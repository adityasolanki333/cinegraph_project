import os
import chromadb

# Path based on settings in chroma_service.py
# persist_path = os.path.join(base_dir, "datasets", "chroma_db_data")
# Adjusted for scripts/ directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
persist_path = os.path.join(base_dir, "datasets", "chroma_db_data")

print(f"Connecting to ChromaDB at {persist_path}...")

try:
    client = chromadb.PersistentClient(path=persist_path)
    collection = client.get_collection(name="tmdb_movies_minilm_l6_v2")
    count = collection.count()
    print(f"SUCCESS: Total movies in ChromaDB: {count}")
    
    # Also print a sample document to verify structure
    if count > 0:
        results = collection.peek(limit=1)
        print("\nSample Document Content:")
        print(results['documents'][0])
except Exception as e:
    print(f"ERROR: {e}")
