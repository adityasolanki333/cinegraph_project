import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "movieflix.settings")
django.setup()

from django.contrib.auth.models import User
from movies.models import UserReview, TmdbTrainingData

# Check if user has ratings
print("=== Checking User Data ===")
users = User.objects.all()
print(f"Total users: {users.count()}")

for user in users:
    reviews = UserReview.objects.filter(user=user)
    print(f"\nUser: {user.username} (ID: {user.id})")
    print(f"  Total reviews: {reviews.count()}")
    high_rated = reviews.filter(rating__gte=4)
    print(f"  High-rated (>=4): {high_rated.count()}")
    
    if high_rated.exists():
        print(f"  Sample high-rated movies:")
        for review in high_rated[:3]:
            print(f"    - {review.title} (ID: {review.tmdb_id}, Rating: {review.rating})")

# Check if training data exists
print("\n=== Checking Training Data ===")
training_count = TmdbTrainingData.objects.count()
print(f"Total movies in TmdbTrainingData: {training_count}")

if training_count > 0:
    sample = TmdbTrainingData.objects.first()
    print(f"Sample movie: {sample.title} (ID: {sample.tmdb_id})")

# Test the recommendation engine
print("\n=== Testing Recommendation Engine ===")
if users.exists():
    test_user = users.first()
    print(f"Testing for user: {test_user.username} (ID: {test_user.id})")
    
    try:
        from movies.ml.recommendation_engine import hybrid_recommender, recommendation_engine
        
        # Build the user-item matrix
        print("Building user-item matrix...")
        recommendation_engine.build_user_item_matrix(None)
        print(f"Matrix shape: {recommendation_engine.user_item_matrix.shape if recommendation_engine.user_item_matrix is not None else 'None'}")
        
        # Get recommendations
        print(f"Getting hybrid recommendations for user {test_user.id}...")
        recommendations = hybrid_recommender.get_recommendations(test_user.id, n_recommendations=5)
        
        print(f"Recommendations returned: {len(recommendations)}")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"{i}. TMDB ID: {rec.get('tmdb_id')}, Score: {rec.get('score'):.3f}, Type: {rec.get('type')}")
            if 'reason' in rec:
                print(f"   Reason: {rec['reason']}")
                
    except Exception as e:
        import traceback
        print(f"ERROR: {e}")
        traceback.print_exc()
else:
    print("No users found in database")

print("\n=== Check Complete ===")
