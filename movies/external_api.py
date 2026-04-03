import os
import requests

RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')


def rapidapi_request(url, host):
    if not RAPIDAPI_KEY:
        return None, "RapidAPI key not configured"
    try:
        response = requests.get(
            url,
            headers={
                'X-Rapidapi-Key': RAPIDAPI_KEY,
                'X-Rapidapi-Host': host,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json(), None
        return None, f"RapidAPI error: {response.status_code}"
    except Exception as e:
        return None, str(e)
