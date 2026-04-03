
import chromadb
from dotenv import load_dotenv
import os

# Load env to avoid warnings (even if not used for local)
load_dotenv()

def inspect_db():
    try:
        path = "./datasets/chroma_db_data"
        print(f"📂 Connecting to ChromaDB at: {path}")
        
        client = chromadb.PersistentClient(path=path)
        
        # List collections
        collections = client.list_collections()
        print(f"📊 Found {len(collections)} collections:")
        
        for col in collections:
            print(f"  - Collection: {col.name}")
            collection = client.get_collection(col.name)
            count = collection.count()
            print(f"    - Total Documents: {count}")
            
            if count > 0:
                print("    - 🕵️ Peeking at first 2 items:")
                peek = collection.peek(limit=2)
                for i in range(len(peek['ids'])):
                    print(f"      [{i+1}] ID: {peek['ids'][i]}")
                    print(f"          Metadata: {peek['metadatas'][i]}")
                    print(f"          Document (snippet): {peek['documents'][i][:100]}...")
                    print("-" * 40)
                    
    except Exception as e:
        print(f"❌ Error inspecting DB: {e}")

if __name__ == "__main__":
    inspect_db()
