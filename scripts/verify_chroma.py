
import os
import chromadb
from dotenv import load_dotenv

# Load env manually since we are running as a script
load_dotenv()

def verify_content():
    api_key = os.environ.get('CHROMA_API_KEY')
    tenant = os.environ.get('CHROMA_TENANT', 'default_tenant')
    database = os.environ.get('CHROMA_DATABASE', 'default_database')

    if not api_key:
        print("Error: CHROMA_API_KEY not found in environment.")
        return

    print("Connecting to ChromaDB...")
    try:
        client = chromadb.HttpClient(
            host='https://api.trychroma.com',
            headers={'x-chroma-token': api_key},
            tenant=tenant,
            database=database
        )
        
        collection_name = "tmdb_movies_bert"
        try:
            collection = client.get_collection(name=collection_name)
        except Exception:
            print(f"Collection '{collection_name}' not found.")
            return

        print(f"Peeking at collection '{collection_name}'...")
        # Get first 3 items
        results = collection.peek(limit=3)
        
        if not results['documents']:
            print("Collection is empty.")
            return

        print("\n--- Verified Documents ---")
        for i, doc in enumerate(results['documents']):
            print(f"Document {i+1}:")
            print(f"'{doc}'")
            print("-" * 30)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_content()
