import os
from dotenv import load_dotenv
load_dotenv()
from pinecone import Pinecone
import json

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))

try:
    print('Available indexes:', [i.name for i in pc.list_indexes()])
    if 'cinema-guide' in [i.name for i in pc.list_indexes()]:
        idx = pc.Index('cinema-guide')
        stats = idx.describe_index_stats()
        print('=== INDEX STATS ===')
        print(f"Total vectors : {stats.total_vector_count}")
        print(f"Namespaces    : {dict(stats.namespaces)}")
        
        # We don't know exact IDs, we can just do a dummy query to get 2 random items
        # A dummy query vector of 384 dimensions (all zeros or ones)
        qvec = [0.1] * 384
        res = idx.query(vector=qvec, top_k=2, namespace='movies', include_metadata=True)
        print('=== SAMPLE MOVIES ===')
        for match in res.matches:
            print(f"ID: {match.id}")
            print(f"Metadata keys: {list(match.metadata.keys())}")
            print(f"Title: {match.metadata.get('title')}")
            print(f"Overview snippet: {str(match.metadata.get('overview'))[:150]}...")
            print("---")
except Exception as e:
    print('Error:', e)
