
import requests
import json
import os

# Ensure we use the right port
URL = "http://127.0.0.1:8000/api/recommendations/semantic-search"

def test_search():
    print(f"Testing {URL}...")
    try:
        # Simple query payload
        payload = {"query": "adventure movies"}
        
        response = requests.post(URL, json=payload)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Source: {data.get('source')}")
            print(f"Count: {data.get('count')}")
        else:
            print(f"Failed: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
