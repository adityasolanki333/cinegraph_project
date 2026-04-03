import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("PINECONE_API_KEY")

pc = Pinecone(api_key=api_key)

print("=== PINE CONE DB INDEXES ===\n")
for idx_name in pc.list_indexes():
    print(f"Index: {idx_name.name}")
    idx = pc.Index(idx_name.name)
    stats = idx.describe_index_stats()
    print(f"  Dimension: {stats.dimension}")
    print(f"  Total Vectors: {stats.total_vector_count}")
    print(f"  Namespaces: {list(stats.namespaces.keys())}")
    
    # Query a single sample
    for ns in stats.namespaces.keys():
        if stats.namespaces[ns].vector_count > 0:
            print(f"\n  [Sample vector from '{idx_name.name}', namespace: '{ns}']")
            try:
                # Dummy vector 
                res = idx.query(vector=[0.1]*stats.dimension, top_k=1, namespace=ns, include_metadata=True)
                if res.matches:
                    m = res.matches[0]
                    print(f"  ID: {m.id} | Score based on dummy vec: {m.score:.4f}")
                    for k, v in m.metadata.items():
                        # Truncate long texts
                        val_str = str(v)
                        if len(val_str) > 100: val_str = val_str[:100] + "..."
                        print(f"    - {k}: {val_str}")
            except Exception as e:
                print(f"  Failed to query sample: {e}")
    print("\n" + "-"*40 + "\n")
