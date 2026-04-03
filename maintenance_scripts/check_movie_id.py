
import os
import chromadb
from django.conf import settings
import sys

# Setup Django standalone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
import django
django.setup()

def check_movie(movie_id):
    persist_path = os.path.join(settings.BASE_DIR, "datasets", "chroma_db_data")
    if not os.path.exists(persist_path):
        print("ChromaDB path does not exist.")
        return
    
    client = chromadb.PersistentClient(path=persist_path)
    collection_name = "tmdb_movies_minilm_l6_v2"
    try:
        collection = client.get_collection(name=collection_name)
        result = collection.get(ids=[str(movie_id)])
        
        if result and result['ids'] and len(result['ids']) > 0:
            print(f"Movie {movie_id} FOUND in ChromaDB.")
            print("Metadata:", result['metadatas'][0])
        else:
            print(f"Movie {movie_id} NOT FOUND in ChromaDB.")
            
    except Exception as e:
        print(f"Error checking movie: {e}")

if __name__ == "__main__":
    check_movie(1306368)
