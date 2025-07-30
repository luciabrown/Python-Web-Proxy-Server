import socket, threading
from datetime import datetime,timedelta

# URL Blocking Initialisation & Cache
blocked_urls = set()
cache={}
cache_expiry=timedelta(seconds=30)
blocklist_lock = threading.Lock()

# Initialize socket server & bind to local address, listen for up to 10 incoming connections
port = 8888
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('127.0.0.1', port))
server.listen(10)
print(f"Proxy server started on 127.0.0.1:{port}")

# Read data from incoming request & extract target server's host & port
def handle_client_request(client_socket):
    """Handles incoming client requests, forwards them to the target server, and relays the response back."""
    print("Received request from client.")  
    client_socket.settimeout(25.0)  # Set timeout for receiving

    # Kill connection if there's no data found
    request = read_full_request(client_socket)
    if not request:
        print("No request data received. Closing connection.")
        client_socket.close()
        return
    
    # Take the first line to extract the method (check for HTTPS)
    first_line = request.split(b'\n')[0].decode('utf-8', 'ignore')
    method, _, _ = first_line.split()

    # Extract the target server's host and port from the request
    host, port = extract_host_port_from_request(request)

    # Kill connection if there's no host or port found
    if not host or port is None:
        print("[Invalid host/port extracted. Closing connection.")
        client_socket.close()
        return
    
    print(f"Extracted Host: {host}, Port: {port}")

    # Check if the requested URL is blocked
    if url_is_blocked(host):
        print(f"URL {host} is blocked.")
        client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\nBlocked URL.")
        client_socket.close()
        blocklist()
        return
    
    # Check if the connection is HTTPS
    if method == "CONNECT":
        handle_https(client_socket, host, port)
    # Use HTTP instead of HTTPS
    else:
        handle_http(client_socket, host, port, request)

def read_full_request(client_socket):
    """Reads the full HTTP request from the client socket."""
    request = b""
    try:
        while True:
            data = client_socket.recv(1024) # Take in data chunk by chunk
            if not data:
                break  # No more data means request is complete
            request += data # Add the chunks to the full request
            if b'\r\n\r\n' in request: # Stop reading once full HTTP headers are received
                break
    except socket.timeout:
        print("Client socket timed out while reading request (likely incomplete request).")
    except Exception as e:
        print(f"Error while reading request: {e}")
    return request

# HTTP handler
def handle_http(client_socket, host, port, request):

    # If there is an existing cache, attempt to use it
    cache_key = f"{host}:{port}"
    if cache_key in cache:
        cache_timestamp, cached_response = cache[cache_key]
        if datetime.now() - cache_timestamp < cache_expiry: # Ensure that the cache is still witin the appropriate time
            print(f"Serving {cache_key} from cache.")
            try:
                client_socket.sendall(cached_response)  # Ensure full response is sent
                print(f"Sent cached response for {cache_key}")
            except Exception as e:
                print(f"Error sending cached response: {e}")
            client_socket.close()
            return
        else:
            print(f"Cache expired for {cache_key}, fetching fresh data.")   # Get new data if the cache is expired
            del cache[cache_key] # Clear old cache

    # Forward client request & handle response
    try:
        destination_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        destination_socket.connect((host, port))
        print("Connection established with target server.")

        # Forward request to destination server
        request = request.replace(b"Connection: keep-alive", b"Connection: close")
        destination_socket.sendall(request)
        print("Request forwarded to target server.")

        response_data = b'' 
        while True:
            data = destination_socket.recv(1024)    # Handle data in chunks again
            if not data:
                break  # Stop when no more data is available
            print(f"Received chunk from target server:")
            response_data += data # Collect full response
            client_socket.sendall(data)
        if response_data:
            cache[cache_key] = (datetime.now(), response_data)  # Update cache with response data
            print(f"Cached response for {cache_key}")

    except Exception as e:
        print(f"Error forwarding request or receiving response: {e}")
    
    finally:
        close_sockets(client_socket, destination_socket)    # Terminate the connection once all is complete

# HTTPS handler
def handle_https(client_socket, host, port):
    try:
        # Establish the HTTPS connection
        print(f"Setting up tunnel for {host}:{port}...")

        # Connect to target server
        destination_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        destination_socket.connect((host, port))

        # Respond to client indicating tunnel is established
        client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        print("200 OK response sent to client.")

        # Use threading to allow bidirectional communication
        client_to_server = threading.Thread(target=forward_data, args=(client_socket, destination_socket, "Client to Server Direction"))
        server_to_client = threading.Thread(target=forward_data, args=(destination_socket, client_socket, "Server to Client Direction"))
        client_to_server.start()
        server_to_client.start()
        client_to_server.join(timeout=25)
        server_to_client.join(timeout=25)

        # Kill connection if still alive after the timeout
        if client_to_server.is_alive() or server_to_client.is_alive():
            print("Forcing socket closure due to prolonged connection.")
            close_sockets(client_socket, destination_socket)

    except Exception as e:
        print(f"Error in HTTPS: {e}")

    finally:
        close_sockets(client_socket, destination_socket)    # Terminate the connection once all is complete

def forward_data(source, destination, direction):
    """Forwards data between two sockets and logs activity"""
    source.settimeout(10)
    try:
        while True:
            try:
                data = source.recv(4096)
                if not data:
                   # print(f"[{direction}] Connection closed.")
                    break
                #print(f"[{direction}] Forwarding {len(data)} bytes")
                destination.sendall(data)
            except socket.timeout:
               # print(f"[{direction}] Socket timeout reached, closing connection.")
                break
    except Exception as e:
        print(f"Error forwarding data: {e}")

# Close the connections/sockets
def close_sockets(client_socket, destination_socket):
    """Safely closes client and destination sockets."""
    print("Closing connections...")

    # If there is a destinaton socket, attempt to close it
    if destination_socket:  
        try:
            destination_socket.close() 
        except Exception as e:
            print(f"Error closing destination socket: {e}")
    
    # If there is a client socket, attempt to close it
    if client_socket:
        try:
            client_socket.close()
        except Exception as e:
            print(f"Error closing client socket: {e}")
    print("Connection closed.")
    blocklist()

# Checks for URL blockage
def url_is_blocked(host):
    """Checks if the requested host is in the blocklist."""
    for blocked in blocked_urls:
        if host in blocked or host.endswith("." + blocked):
            return True
    return False

# Allow for dynamic URL blocking
def blocklist():
    """Manage blocked URLs."""
    while True:
        print("1. Add URL to blocklist")
        print("2. Remove URL from blocklist")
        print("3. Show blocked URLs")
        print("4. Exit")
        choice = input("---- Enter your choice: ----")

        with blocklist_lock:
            if choice == '1':
                url = input("Enter URL to block: ")
                if url in blocked_urls:
                    print(f"{url} is already in the blocklist.")
                else:
                    blocked_urls.add(url)
                    print(f"{url} Added to blocklist.")
                continue
            elif choice == '2':
                url = input("Enter URL to unblock: ")
                if url not in blocked_urls:
                    print(f"{url} is not in the blocklist.")
                else:
                    blocked_urls.discard(url)
                    print(f"{url} Removed from blocklist.")
                continue
            elif choice == '3':
                print("\n---- Blocked URLs: ----")
                if blocked_urls:
                    for url in blocked_urls:
                        print(f"  - {url}\n")
                else:
                    print("No URLs are blocked.\n")
                continue
            elif choice == '4':
                print("Resuming...")
                break
            else:
                print("Invalid choice, please try again.")
                continue

# Get the host and port names
def extract_host_port_from_request(request):
    """Extracts the host and port from the HTTP request."""
    try:
        host_string_start = request.find(b'Host: ') + len(b'Host: ')
        host_string_end = request.find(b'\r\n', host_string_start)
        host_string = request[host_string_start:host_string_end].decode('utf-8')

        if ":" in host_string:
            host, port = host_string.split(":", 1)
            port = int(port)
        else:
            host = host_string
            port = 443 if b'CONNECT' in request.split(b'\n')[0] else 80  # HTTPS default to 443, HTTP to 80
        return host, port
    except Exception as e:
        print(f"Failed to extract host/port: {e}")
        return None, None
    
blocklist_thread = threading.Thread(target=blocklist)
blocklist_thread.start()

# Always listen for incoming requests & create a new thread to handle each client request
if __name__ == "__main__":
    while True:
        client_socket, addr = server.accept()
        print(f"Accepted Connection from {addr[0]}:{addr[1]}")

        # Create a new thread to handle the client's request
        client_handler = threading.Thread(target=handle_client_request, args=(client_socket,))
        client_handler.start()
