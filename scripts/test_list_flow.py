import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"
USER_ID = "2"  # Using existing user ID from logs
HEADERS = {
    "Content-Type": "application/json",
    "x-user-id": USER_ID
}

def test_list_flow():
    print("--- Starting List Flow Test ---")

    # 1. Create List
    print("\n1. Creating 'Test List API'...")
    create_payload = {
        "userId": int(USER_ID),
        "name": "Test List API",
        "description": "Created via test script",
        "isPublic": True
    }
    try:
        response = requests.post(f"{BASE_URL}/community/lists", json=create_payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        if response.status_code != 201:
            print(f"FAILED: {response.text}")
            return
        
        list_data = response.json()
        list_id = list_data['id']
        print(f"SUCCESS: Created List ID {list_id}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return

    # 2. Add Item to List
    print(f"\n2. Adding 'Inception' to List {list_id}...")
    add_item_payload = {
        "tmdbId": 27205,
        "mediaType": "movie",
        "title": "Inception",
        "posterPath": "/test_poster.jpg",
        "note": "Great movie"
    }
    try:
        response = requests.post(f"{BASE_URL}/community/lists/{list_id}/items", json=add_item_payload, headers=HEADERS)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code not in [200, 201]:
            print("FAILED to add item")
    except Exception as e:
        print(f"EXCEPTION: {e}")

    # 3. Verify Item Count (via User Lists)
    print(f"\n3. Verifying List Count...")
    try:
        response = requests.get(f"{BASE_URL}/community/users/{USER_ID}/lists", headers=HEADERS)
        lists = response.json()
        my_list = next((l for l in lists if l['id'] == list_id), None)
        if my_list:
            item_count = my_list.get('itemCount', 'N/A')
            print(f"List Found. Item Count: {item_count}")
            
            # Verify items array is present
            items = my_list.get('items', [])
            print(f"Items in list: {len(items)}")
            
            if items:
                item_id = items[0]['id']
                print(f"Found item {items[0]['title'] if 'title' in items[0] else 'ID:'+str(item_id)}")
                
                # 4. Remove Item from List
                print(f"\n4. Removing Item {item_id} from List {list_id}...")
                try:
                    remove_resp = requests.delete(f"{BASE_URL}/community/lists/{list_id}/items/{item_id}", headers=HEADERS)
                    print(f"Status: {remove_resp.status_code}")
                    if remove_resp.status_code == 204:
                         print("SUCCESS: Item removed")
                    else:
                         print(f"FAILED: {remove_resp.text}")
                except Exception as e:
                    print(f"EXCEPTION removing item: {e}")
        else:
            print("List NOT found in user lists!")
    except Exception as e:
        print(f"EXCEPTION: {e}")

    # 5. Delete List
    print(f"\n5. Deleting List {list_id}...")
    try:
        response = requests.delete(f"{BASE_URL}/community/lists/{list_id}", headers=HEADERS)
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 204]:
            print("SUCCESS: List deleted")
        else:
            print(f"FAILED: {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_list_flow()
