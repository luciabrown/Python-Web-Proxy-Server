import requests, time, concurrent.futures,urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)# Disable terminal warnings about security


# Proxy settings (For HTTPS requests)
proxies = {
    "http": "http://127.0.0.1:8888",  # Proxy server running locally
    "https": "http://127.0.0.1:8888",  
}

# Send a basic HTTPS request through the proxy
def send_https_request(url):
    print("---- TEST 1 - BASIC HTTPS CONNECTION ----")
    try:
        print(f"Sending HTTPS request to {url} through the proxy...")
        response = requests.get(url, proxies=proxies, verify=False)  # Disable verification for testing
        print("Response status code:", response.status_code)
        print("Response headers:", str(response.headers)[:20])
      #  print("Response body (first 200 chars):", response.text[:200])
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

# Test caching functionality for HTTPS connections
# Includes timing data to prove cached request is faster than non-cached request
def caching_test_https(url):
    print("\n---- TEST 2 - CACHING HTTPS CONNECTIONS ----\n")
    response1 = send_https_request(url) #Inital request to ensure there is something in the cache

    time.sleep(2)
    start_time_cache = time.time()
    response2 = send_https_request(url)    #This request should be pulled from the cache
    end_time_cache = time.time()
    elapsed_time_cache = end_time_cache - start_time_cache
    print(f"Time taken for cached request: {elapsed_time_cache:.5f} seconds")

    # Compare results
    if response1 and response2:
        if response1.status_code == response2.status_code:
            print("Both HTTPS requests returned the same status code.")
        if response1.text[:200] == response2.text[:200]:
            print("HTTPS responses have identical content (cache hit likely).")
        else:
            print("HTTPS responses have different content (cache miss or different resource).")
    else:
        print("Issue with one of the HTTPS requests.") 
    
    time.sleep(40)  # Allow the cache to expire
    start_time_nocache = time.time()
    send_https_request(url)    # This request should be fresh and take longer
    end_time_nocache = time.time()
    elapsed_time_nocache = end_time_nocache - start_time_nocache
    print(f"Time taken for non-cached request: {elapsed_time_nocache:.5f} seconds")

    difference = elapsed_time_nocache - elapsed_time_cache
    print(f"THE TIME DIFFERENCE BETWEEN THE CACHED AND NON-CACHED REQUEST WAS: {difference:.5f} seconds")
     
    print("\n---- END TEST 2 ----\n")

# Test for concurrent HTTPS requests
def concurrent_https_test(url):
    print("---- TEST 3 - CONCURRENT HTTPS CONNECTIONS ----")
    print("\nSending concurrent HTTPS requests...\n")
    urls = [url] * 3  # Simulate multiple users requesting the same HTTPS URL
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(send_https_request, urls))

    # Time the concurrent requests
    elapsed_time = time.time() - start_time
    print(f"\nAll concurrent HTTPS requests completed in {elapsed_time:.6f} seconds")

    # Check if all responses are the same
    successful_responses = [resp for resp in results if resp and resp.status_code == 200]
    if len(successful_responses) == len(urls):
        print("All concurrent HTTPS requests returned successful responses")
        if all(resp.text[:200] == successful_responses[0].text[:200] for resp in successful_responses):
            print("All concurrent HTTPS responses are identical")
        else:
            print("Concurrent HTTPS responses differ")
    else:
        print("Some concurrent HTTPS requests failed")
    print("---- END TEST 3 ----")

# Test the HTTPS functionality
google = "https://google.com"  
youtube = "https://youtube.com"
github = "https://github.com"

send_https_request(youtube)
#caching_test_https(google)
#concurrent_https_test(github)
