"""
Upload TMDB data to ChromaDB with embeddings
Limit: 10,000 movies
"""

import os
import sys
import os

# Add project root to sys.path to allow importing project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
import pandas as pd
import numpy as np
import chromadb
from sentence_transformers import SentenceTransformer

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "movieflix.settings")
django.setup()

# Configuration
DATASET_PATH = "datasets/TMDB_all_movies.csv"
LIMIT = 10000
BATCH_SIZE = 100
COLLECTION_NAME = "tmdb_movies_minilm_l6_v2"

# Initialize ChromaDB client
print("Connecting to ChromaDB...")
client = chromadb.HttpClient(
    host="api.trychroma.com",
    port=443,
    ssl=True,
    tenant=os.getenv("CHROMA_TENANT"),
    database=os.getenv("CHROMA_DATABASE"),
    headers={"x-chroma-token": os.getenv("CHROMA_API_KEY")}
)

# Get or create collection
try:
    collection = client.get_collection(COLLECTION_NAME)
    print(f"✓ Found existing collection: {COLLECTION_NAME}")
    
    # Ask user if they want to reset
    response = input("Collection already exists. Do you want to reset it? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        client.delete_collection(COLLECTION_NAME)
        print("✓ Deleted existing collection")
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "TMDB movies with MiniLM-L6-v2 embeddings"}
        )
        print(f"✓ Created new collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"Creating new collection: {COLLECTION_NAME}")
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "TMDB movies with MiniLM-L6-v2 embeddings"}
    )
    print(f"✓ Created collection: {COLLECTION_NAME}")

# Load TMDB dataset
print(f"\nLoading TMDB dataset from {DATASET_PATH}...")
try:
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    print(f"✓ Loaded {len(df)} total movies from dataset")
except Exception as e:
    print(f"✗ Error loading dataset: {e}")
    sys.exit(1)

# Filter and prepare data
print("\nPreparing data...")

# Filter for movies with required fields
df = df.dropna(subset=['id', 'title', 'overview'])
df = df[df['overview'].str.len() > 20]  # Filter out movies with very short overviews

# Sort by popularity or vote_count to get best movies
if 'popularity' in df.columns:
    df = df.sort_values('popularity', ascending=False)
elif 'vote_count' in df.columns:
    df = df.sort_values('vote_count', ascending=False)

# Limit to top N movies
df = df.head(LIMIT)
print(f"✓ Selected {len(df)} movies for embedding")

# Prepare text for embedding
print("\nPreparing text for embedding...")
df['embedding_text'] = df.apply(
    lambda row: f"{row['title']}. {row['overview']}" + 
                (f". Genres: {row['genres']}" if pd.notna(row.get('genres')) else ""),
    axis=1
)

# Initialize embedding model
print("\nLoading embedding model (all-MiniLM-L6-v2)...")
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"✗ Error loading model: {e}")
    sys.exit(1)

# Upload to ChromaDB in batches
print(f"\nUploading {len(df)} movies to ChromaDB in batches of {BATCH_SIZE}...")

uploaded_count = 0
error_count = 0

# Function to process a single batch
def process_batch(batch_data):
    batch_idx, batch_df = batch_data
    try:
        # Prepare batch data
        ids = [str(int(tmdb_id)) for tmdb_id in batch_df['id'].values]
        texts = batch_df['embedding_text'].tolist()
        
        # Generate embeddings
        # Note: SentenceTransformer encoding handles batching efficiently internally,
        # but running multiple encodes in parallel threads might compete for CPU/GPU.
        # However, the network I/O for ChromaDB upload is the likely bottleneck.
        embeddings = model.encode(texts, show_progress_bar=False).tolist()
        
        # Prepare metadata
        metadatas = []
        for _, row in batch_df.iterrows():
            metadata = {
                'title': str(row['title']),
                'overview': str(row['overview'])[:500],  # Limit overview length
            }
            
            # Add optional fields if available
            if pd.notna(row.get('release_date')):
                metadata['release_date'] = str(row['release_date'])
            if pd.notna(row.get('genres')):
                metadata['genres'] = str(row['genres'])
            if pd.notna(row.get('vote_average')):
                metadata['vote_average'] = float(row['vote_average'])
            if pd.notna(row.get('popularity')):
                metadata['popularity'] = float(row['popularity'])
            if pd.notna(row.get('original_language')):
                metadata['original_language'] = str(row['original_language'])
            
            metadatas.append(metadata)
        
        # Upload to ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        return len(ids), 0, None
        
    except Exception as e:
        return 0, len(batch_df), f"Batch {batch_idx + 1}: {str(e)}"

# Prepare batches
batches = []
for i in range(0, len(df), BATCH_SIZE):
    batch_df = df.iloc[i:i+BATCH_SIZE]
    batches.append((i // BATCH_SIZE, batch_df))

# Upload to ChromaDB in parallel
print(f"\nUploading {len(df)} movies to ChromaDB in parallel (max_workers=5)...")

uploaded_count = 0
error_count = 0

import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # Map batches to executor
    futures = [executor.submit(process_batch, batch) for batch in batches]
    
    # Process results as they complete
    for future in tqdm(concurrent.futures.as_completed(futures), total=len(batches), desc="Uploading batches"):
        success, error, error_msg = future.result()
        uploaded_count += success
        error_count += error
        if error_msg:
            print(f"\n✗ {error_msg}")

print(f"\n{'='*60}")
print(f"Upload Complete!")
print(f"{'='*60}")
print(f"✓ Successfully uploaded: {uploaded_count} movies")
if error_count > 0:
    print(f"✗ Errors: {error_count} movies")
print(f"Collection: {COLLECTION_NAME}")
print(f"Embedding model: all-MiniLM-L6-v2")
print(f"Embedding dimension: 384")

# Verify upload
print(f"\n{'='*60}")
print("Verifying upload...")
try:
    count = collection.count()
    print(f"✓ Collection now contains {count} movies")
    
    # Test query
    test_results = collection.get(
        ids=[ids[0]],
        include=['embeddings', 'metadatas', 'documents']
    )
    
    if test_results and test_results['ids']:
        print(f"✓ Test query successful")
        print(f"  Sample movie: {test_results['metadatas'][0].get('title', 'N/A')}")
        print(f"  Embedding dimension: {len(test_results['embeddings'][0])}")
    else:
        print("✗ Test query failed")
        
except Exception as e:
    print(f"✗ Verification error: {e}")

print(f"\n{'='*60}")
print("Done!")
print(f"{'='*60}")
