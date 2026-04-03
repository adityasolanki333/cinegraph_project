
import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

def reset_chroma():
    api_key = os.environ.get('CHROMA_API_KEY')
    tenant = os.environ.get('CHROMA_TENANT', 'default_tenant')
    database = os.environ.get('CHROMA_DATABASE', 'default_database')

    if not api_key:
        print("Error: CHROMA_API_KEY not found.")
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
            print(f"Deleting collection '{collection_name}'...")
            client.delete_collection(name=collection_name)
            print("Collection deleted successfully.")
        except Exception as e:
            print(f"Collection delete failed (might not exist): {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_chroma()
