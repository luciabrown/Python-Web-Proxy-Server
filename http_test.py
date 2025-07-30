import requests,time,concurrent.futures, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Disable terminal warnings about security

# Proxy settings
proxies = {
    "http": "http://127.0.0.1:8888",  
    "https": "http://127.0.0.1:8888",
}

# Test sending a basic HTTP request through the server
def send_request(url):
    print("---- TEST 1 - BASIC HTTP CONNECTION ----")
    try:
        print(f"Sending request to {url} through the proxy...")
        response = requests.get(url, proxies=proxies,verify=False)
        print("Response status code:", response.status_code)  # Print HTTP status code
        print("Response headers:", response.headers) 
       # print("Response body (first 200 chars):", response.text[:200])  # Print first 200 chars of body
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

# Test the caching functionality by sending the same requests through the server before and after the cache has expired
# Includes timing data to prove that the cached result is faster than the non-cached result
def caching_test(response1):
    print("\n---- TEST 2 - CACHING CONNECTIONS ----\n")
    time.sleep(2)
    start_time_1 = time.time()
    response2 = send_request(url)
    end_time_1 = time.time()
    elapsed_time_1 = end_time_1 - start_time_1
    print(f"Time taken for cached request: {elapsed_time_1:.2f} seconds")

    # Compare results
    if response1 and response2:
        if response1.status_code == response2.status_code:
            print("Both requests returned the same status code.")
        if response1.text[:200] == response2.text[:200]:
            print("Responses have identical content (cache hit likely).")
        else:
            print("Responses have different content (cache miss or different resource).")
    else:
        print("Issue with one of the requests.")

    time.sleep(40)  # Allow the cache to expire
    start_time_2 = time.time()
    send_request(url)
    end_time_2 = time.time()
    elapsed_time_2 = end_time_2 - start_time_2
    print(f"Time taken for non-cached request: {elapsed_time_2:.2f} seconds")

    difference = elapsed_time_2 - elapsed_time_1
    print(f"THE TIME DIFFERENCE BETWEEN THE CACHED AND NON-CACHED REQUEST WAS: {difference:.5f} seconds")
    print("---- END TEST 2 ----")

# Test for concurrent requests
def concurrent_test():
    print("---- TEST 3 - CONCURRENT CONNECTIONS ----")
    print("\nSending concurrent requests...\n")
    urls = [url] * 3  # Simulate multiple users requesting the same URL
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(send_request, urls))

    # Time the concurrent requests
    elapsed_time = time.time() - start_time
    print(f"\nAll concurrent requests completed in {elapsed_time:.6f} seconds")

    # Check if all responses are the same (cache verification)
    successful_responses = [resp for resp in results if resp and resp.status_code == 200]
    if len(successful_responses) == len(urls):
        print("All concurrent requests returned successful responses")
        if all(resp.text[:200] == successful_responses[0].text[:200] for resp in successful_responses):
            print("All concurrent responses are identical")
        else:
            print("Concurrent responses differ")
    else:
        print("Some concurrent requests failed")
    print("---- END TEST 3 ----")

url = "http://example.com"
response1 = send_request(url)
caching_test(response1)
concurrent_test()
