
import chromadb
from sentence_transformers import SentenceTransformer
import sys

def search_movies(query_text, n_results=5):
    print(f"🔍 Searching for: '{query_text}'")
    
    # 1. Connect to Local DB
    path = "./datasets/chroma_db_data"
    client = chromadb.PersistentClient(path=path)
    
    collection_name = "tmdb_movies_minilm_l6_v2"
    collection = client.get_collection(name=collection_name)
    
    # 2. Encode Query
    print("🧠 Encoding query...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode([query_text]).tolist()
    
    # 3. Query DB
    print("⚡ Querying nearest neighbors...")
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        include=["metadatas", "documents", "distances"]
    )
    
    # 4. Print Results
    print(f"\n🎬 Top {n_results} Recommendations:")
    for i in range(len(results['ids'])): # Results is a dict with lists
        # Chroma returns list of lists (one list per query)
        ids = results['ids'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        documents = results['documents'][0]
        
        for j in range(len(ids)):
            print(f"\n[{j+1}] {metadatas[j]['title']} (Score: {1 - distances[j]:.4f})")
            print(f"    📅 Released: {metadatas[j]['release_date']}")
            print(f"    🎭 Genres: {metadatas[j]['genres']}")
            print(f"    📝 Plot: {documents[j][:150]}...")

if __name__ == "__main__":
    query = "Star Wars"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    
    search_movies(query)
