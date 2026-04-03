
import os
import chromadb
from django.conf import settings
import sys

# Setup Django standalone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
import django
django.setup()

def check_count():
    persist_path = os.path.join(settings.BASE_DIR, "datasets", "chroma_db_data")
    print(f"Checking path: {persist_path}")
    if not os.path.exists(persist_path):
        print("ChromaDB path does not exist.")
        return 0
    
    client = chromadb.PersistentClient(path=persist_path)
    collection_name = "tmdb_movies_minilm_l6_v2"
    try:
        collection = client.get_collection(name=collection_name)
        count = collection.count()
        print(f"Collection '{collection_name}' has {count} items.")
        return count
    except Exception as e:
        print(f"Collection '{collection_name}' not found or error: {e}")
        return 0

if __name__ == "__main__":
    check_count()
