import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "movieflix.settings")
django.setup()

from movies.ml.recommendation_engine import content_based_recommender

print("Testing ChromaDB response structure...")

try:
    # Get a sample movie
    results = content_based_recommender.chroma_collection.get(
        ids=["278"],  # The Shawshank Redemption
        include=['embeddings']
    )
    
    print(f"Type of results: {type(results)}")
    print(f"Keys in results: {results.keys() if results else 'None'}")
    
    if 'embeddings' in results:
        print(f"\nType of results['embeddings']: {type(results['embeddings'])}")
        print(f"Value: {results['embeddings']}")
        print(f"Length: {len(results['embeddings']) if hasattr(results['embeddings'], '__len__') else 'N/A'}")
        
        # Try different checks
        print(f"\nChecking with 'if results['embeddings']': ", end="")
        try:
            if results['embeddings']:
                print("TRUE")
            else:
                print("FALSE")
        except Exception as e:
            print(f"ERROR: {e}")
            
        print(f"Checking with 'len() > 0': ", end="")
        try:
            if len(results['embeddings']) > 0:
                print("TRUE")
            else:
                print("FALSE")
        except Exception as e:
            print(f"ERROR: {e}")
            
        print(f"Checking with 'is not None': ", end="")
        try:
            if results['embeddings'] is not None:
                print("TRUE")
            else:
                print("FALSE")
        except Exception as e:
            print(f"ERROR: {e}")
            
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
