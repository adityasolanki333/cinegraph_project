
import os
import django
import sys
import unittest

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
django.setup()

from django.contrib.auth.models import User
from movies.models import UserReview, UserList, UserActivityStats, UserBadge, UserFollow

class TestGamification(unittest.TestCase):
    def setUp(self):
        # Clean up previous tests
        User.objects.filter(username__startswith='testgamer').delete()
        
        # Create users
        self.user1 = User.objects.create_user(username='testgamer1', email='gamer1@test.com', password='password123')
        self.user2 = User.objects.create_user(username='testgamer2', email='gamer2@test.com', password='password123')
        
    def test_review_badges(self):
        print("\nTesting Review Badges...")
        # Create 1 review -> First Review Badge
        UserReview.objects.create(
            user=self.user1,
            tmdb_id=100,
            media_type='movie',
            rating=5,
            review_text='Great movie!'
        )
        
        stats = UserActivityStats.objects.get(user=self.user1)
        print(f"Stats after 1 review: {stats.total_reviews} reviews")
        self.assertEqual(stats.total_reviews, 1)
        self.assertTrue(UserBadge.objects.filter(user=self.user1, badge_type='first_review').exists(), "Should have 'first_review' badge")
        
        # Create 9 more reviews -> Review Master Badge
        for i in range(9):
            UserReview.objects.create(
                user=self.user1,
                tmdb_id=101+i,
                media_type='movie',
                rating=4,
                review_text='Another review'
            )
            
        stats.refresh_from_db()
        print(f"Stats after 10 reviews: {stats.total_reviews} reviews")
        self.assertEqual(stats.total_reviews, 10)
        self.assertTrue(UserBadge.objects.filter(user=self.user1, badge_type='review_master').exists(), "Should have 'review_master' badge")
        print("Review Badges Verified!")

    def test_list_badges(self):
        print("\nTesting List Badges...")
        # Create 5 lists -> List Creator Badge
        for i in range(5):
            UserList.objects.create(
                user=self.user2,
                title=f'List {i}',
                description='Test list',
                is_public=True
            )
            
        stats = UserActivityStats.objects.get(user=self.user2)
        print(f"Stats after 5 lists: {stats.total_lists} lists")
        self.assertEqual(stats.total_lists, 5)
        self.assertTrue(UserBadge.objects.filter(user=self.user2, badge_type='list_creator').exists(), "Should have 'list_creator' badge")
        print("List Badges Verified!")

    def test_social_badges(self):
        print("\nTesting Social Badges...")
        # User 1 follows User 2
        UserFollow.objects.create(follower=self.user1, following=self.user2)
        
        stats1 = UserActivityStats.objects.get(user=self.user1) # Follower
        stats2 = UserActivityStats.objects.get(user=self.user2) # Following
        
        print(f"User 1 (Follower) following count: {stats1.total_following}")
        print(f"User 2 (Following) follower count: {stats2.total_followers}")
        
        self.assertEqual(stats1.total_following, 1)
        self.assertEqual(stats2.total_followers, 1)
        
        # Verify stats decrement on unfollow
        UserFollow.objects.filter(follower=self.user1, following=self.user2).delete()
        stats1.refresh_from_db()
        stats2.refresh_from_db()
        
        print(f"User 1 after unfollow: {stats1.total_following}")
        self.assertEqual(stats1.total_following, 0)
        print("Social Stats update Verified!")

if __name__ == '__main__':
    unittest.main()
