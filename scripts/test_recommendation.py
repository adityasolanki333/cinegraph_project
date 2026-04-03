import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment so we can import internal modules if needed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
import django
django.setup()

from movies.ml.pinecone_service import pinecone_service

def test_recommendation():
    print("Testing Pinecone search (finding a movie to use as anchor)...")
    
    # 1. Search for a popular movie to get a valid ID that is currently in the DB
    results = pinecone_service.search("science fiction space travel", k=1)
    
    if not results:
        print("No movies found in Pinecone. The ingestion might still be at the very beginning.")
        return
        
    target_movie = results[0]
    movie_id = target_movie['id']
    movie_title = target_movie['title']
    
    print(f"\nFound anchor movie: {movie_title} (ID: {movie_id})")
    print(f"Plot snippet: {target_movie.get('overview', '')[:100]}...")
    
    print("\n--------------------------------------------------------------")
    print(f"Testing Recommendation: get_nearest_neighbors for '{movie_title}'")
    print("--------------------------------------------------------------\n")
    
    # 2. Get nearest neighbors (Recommendations)
    recommendations = pinecone_service.get_nearest_neighbors(movie_id, k=5)
    
    if not recommendations:
        print("No recommendations found!")
        return
        
    for i, rec in enumerate(recommendations, 1):
        score = rec.get('similarity', 0)
        percentage = int(score * 100)
        title = rec.get('title', 'Unknown')
        genres = rec.get('genres', 'N/A')
        print(f"{i}. {title} ({percentage}% Match)")
        print(f"   Genres: {genres}")
        
if __name__ == "__main__":
    if pinecone_service.is_initialized():
        test_recommendation()
    else:
        print("Pinecone service failed to initialize.")
