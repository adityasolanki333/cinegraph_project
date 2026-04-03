import os
import numpy as np
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ['DJANGO_SETTINGS_MODULE'] = 'movieflix.settings'

import django
django.setup()

import chromadb
from chromadb.config import Settings

# Connect to ChromaDB
client = chromadb.HttpClient(
    host="api.trychroma.com",
    port=443,
    ssl=True,
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE"),
    headers={"x-chroma-token": os.getenv("CHROMA_API_KEY")}
)

collection_name = "tmdb_movies_bert"
print(f"Connecting to collection: {collection_name}")
collection = client.get_collection(collection_name)

target_id = "2"
print(f"Fetching embeddings for movie ID {target_id}...")
results = collection.get(ids=[target_id], include=['embeddings', 'documents', 'metadatas'])

if results and results['ids']:
    print(f"✅ Found movie ID {target_id}")
    doc = results['documents'][0]
    print(f"Document soup: {doc[:200]}...") # Print first 200 chars
    print(f"Metadata: {results['metadatas'][0]}")
    
    emb = results['embeddings']
    has_embeddings = False
    
    if isinstance(emb, list):
         if len(emb) > 0: has_embeddings = True
    elif isinstance(emb, np.ndarray):
         if emb.size > 0: has_embeddings = True
         
    if has_embeddings:
        print(f"✅ Embeddings present")
    else:
        print("❌ Embeddings missing")
    
    # Verify Content Soup Format
    expected_substrings = ["Overview:", "Genres:", "Tagline:", "Director:", "Cast:"]
    missing = [s for s in expected_substrings if s not in doc]
    if not missing:
        print("✅ Content Soup format appears correct!")
    else:
        print(f"❌ Content Soup missing sections: {missing}")

else:
    print(f"❌ Movie ID {target_id} not found")
