import requests
import json

print("Testing Hybrid Recommendation API...")
print("=" * 50)

try:
    response = requests.get("http://localhost:8000/api/recommendations/hybrid/1?limit=5", timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse Data:")
        print(json.dumps(data, indent=2))
        
        if 'recommendations' in data:
            print(f"\n✅ Got {len(data['recommendations'])} recommendations")
            for i, rec in enumerate(data['recommendations'][:3], 1):
                print(f"{i}. {rec.get('title', 'Unknown')} - Score: {rec.get('score', 'N/A')}")
        else:
            print("\n⚠️ No 'recommendations' key in response")
    else:
        print(f"\n❌ Error: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ Request timed out after 30 seconds")
except requests.exceptions.ConnectionError:
    print("❌ Could not connect to server - is it running?")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
