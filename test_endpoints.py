import requests
import json

base_url = "http://127.0.0.1:8000"
endpoints = [
    "/api/community/leaderboards",
    "/api/community/trending",
    "/api/tmdb/search/multi?query=batman",
    "/api/recommendations/semantic-search?query=batman",
]

for ep in endpoints:
    url = base_url + ep
    try:
        resp = requests.get(url, timeout=5)
        print(f"{ep}: {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2)[:200] + "...")
        except:
            print(resp.text[:200])
    except Exception as e:
        print(f"{ep}: Error - {e}")
    print("-" * 40)
