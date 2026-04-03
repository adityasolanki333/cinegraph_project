
import requests
import sys

# TMDB ID from the user report
TMDB_ID = 1242898
URL = f"http://127.0.0.1:8000/api/ml/similar/chroma/{TMDB_ID}"

try:
    print(f"Testing GET {URL}...")
    response = requests.get(URL)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    
    if response.status_code == 200:
        print("SUCCESS: Endpoint is reachable.")
        sys.exit(0)
    elif response.status_code == 404:
        print("ERROR: Endpoint still returning 404 Not Found.")
        sys.exit(1)
    else:
        print(f"ERROR: Unexpected status code {response.status_code}")
        sys.exit(1)
        
except Exception as e:
    print(f"EXCEPTION: {e}")
    sys.exit(1)
