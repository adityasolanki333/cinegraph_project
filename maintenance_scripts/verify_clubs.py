import os
import django
import json
from django.test import RequestFactory

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
django.setup()

from django.contrib.auth.models import User
from movies.models import Club, ClubMember, ClubThread, ClubPost
from movies.clubs_api import clubs_list, join_club, club_threads, create_post, thread_details

def setup_users():
    print("Setting up test users...")
    user1, _ = User.objects.get_or_create(username='club_owner', email='owner@example.com')
    if not user1.check_password('password'):
        user1.set_password('password')
        user1.save()
        
    user2, _ = User.objects.get_or_create(username='club_member', email='member@example.com')
    if not user2.check_password('password'):
        user2.set_password('password')
        user2.save()
        
    return user1, user2

def verify_clubs():
    owner, member = setup_users()
    factory = RequestFactory()
    
    print("\n--- Testing Club Creation ---")
    data = {
        'title': 'Test Club',
        'description': 'A club for testing',
        'cover_image_url': 'http://example.com/image.jpg'
    }
    request = factory.post('/api/clubs', data=json.dumps(data), content_type='application/json')
    request.user = owner
    
    response = clubs_list(request)
    if response.status_code != 201:
        print(f"FAILED: Club creation failed. Status: {response.status_code}")
        print(response.content)
        return
        
    club_data = json.loads(response.content)
    club_id = club_data['id']
    print(f"SUCCESS: Club created with ID {club_id}")
    
    # Verify owner membership
    club = Club.objects.get(id=club_id)
    if not ClubMember.objects.filter(club=club, user=owner, role='admin').exists():
         print("FAILED: Owner is not a member/admin")
    else:
         print("SUCCESS: Owner is admin member")

    print("\n--- Testing Join Club ---")
    request = factory.post(f'/api/clubs/{club_id}/join')
    request.user = member
    
    response = join_club(request, club_id)
    if response.status_code != 200:
        print(f"FAILED: Join club failed. Status: {response.status_code}")
    else:
        print("SUCCESS: User joined club")
        club.refresh_from_db()
        print(f"Member count: {club.member_count} (Expected: 2)")

    print("\n--- Testing Create Thread ---")
    thread_data = {
        'title': 'Test Thread',
        'content': 'This is the first thread content.'
    }
    request = factory.post(f'/api/clubs/{club_id}/threads', data=json.dumps(thread_data), content_type='application/json')
    request.user = owner
    
    response = club_threads(request, club_id)
    if response.status_code != 201:
        print(f"FAILED: Thread creation failed. Status: {response.status_code}")
        print(response.content)
        return

    thread_res = json.loads(response.content)
    thread_id = thread_res['id']
    print(f"SUCCESS: Thread created with ID {thread_id}")

    print("\n--- Testing Reply to Thread ---")
    post_data = {
        'content': 'This is a reply from the member.'
    }
    request = factory.post(f'/api/clubs/threads/{thread_id}/posts', data=json.dumps(post_data), content_type='application/json')
    request.user = member
    
    response = create_post(request, thread_id)
    if response.status_code != 201:
        print(f"FAILED: Reply creation failed. Status: {response.status_code}")
    else:
        print("SUCCESS: Reply posted")
        
    # Verify Thread Details and Post Count
    print("\n--- Verifying Thread Details ---")
    request = factory.get(f'/api/clubs/threads/{thread_id}')
    request.user = owner
    response = thread_details(request, thread_id)
    details = json.loads(response.content)
    
    post_count = len(details['posts'])
    print(f"Thread Title: {details['title']}")
    print(f"Post Count: {post_count} (Expected: 1)")
    
    if post_count == 1:
        print("SUCCESS: Thread verification passed")
    else:
        print("FAILED: Post count mismatch")

if __name__ == '__main__':
    try:
        verify_clubs()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
