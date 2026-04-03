
import os
import time
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import concurrent.futures

# Load environment variables
load_dotenv()

def main():
    # Configuration
    CSV_PATH = 'datasets/TMDB_all_movies.csv'
    CHROMA_PATH = './datasets/chroma_db_data'
    COLLECTION_NAME = "tmdb_movies_minilm_l6_v2"
    BATCH_SIZE = 2500
    CHUNK_SIZE = 2000 # Optimized for parallelism
    WORKERS = 4
    LIMIT = 0 # 0 for all

    print(f"🚀 Starting Standalone Fast Ingestion")
    print(f"📂 CSV: {CSV_PATH}")
    print(f"💾 Database: {CHROMA_PATH}")
    
    # 1. Setup ChromaDB
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 2. Setup Model (Multi-Process Safe)
    print("Loading Sentence-BERT model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Start the multi-process pool on all available CPUs
    print("🔥 Starting Multi-Process Encoding Pool...")
    try:
        pool = model.start_multi_process_pool()
    except Exception as e:
        print(f"Warning: Could not start multiprocess pool: {e}")
        pool = None

    # 3. Process CSV
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: CSV not found at {CSV_PATH}")
        return

    # Estimate rows
    print("Counting rows...")
    # total_rows = sum(1 for _ in open(CSV_PATH, 'r', encoding='utf-8')) - 1
    total_rows = 1000000 # Skip count for speed
    
    reader = pd.read_csv(
        CSV_PATH, 
        chunksize=CHUNK_SIZE, 
        usecols=['id', 'title', 'overview', 'genres', 'tagline', 'director', 'cast', 'vote_average', 'release_date'],
        dtype={'id': str, 'title': str, 'overview': str, 'genres': str}
    )

    # Thread pool for uploads (I/O)
    upload_executor = concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS)
    upload_futures = []

    processed_count = 0
    start_time = time.time()

    print(f"⚡ Processing started...")

    try:
        for chunk in reader:
            if LIMIT > 0 and processed_count >= LIMIT:
                break
            
            # Clean data
            chunk = chunk.dropna(subset=['overview', 'title', 'id'])
            if chunk.empty:
                continue

            documents = []
            ids = []
            metadatas = []

            for _, row in chunk.iterrows():
                # Construct rich context
                title = str(row.get('title', ''))
                overview = str(row.get('overview', ''))
                genres = str(row.get('genres', ''))
                cast = str(row.get('cast', ''))[:100] # Limit length
                
                text = f"{title}. {overview} Genres: {genres}. Cast: {cast}."
                documents.append(text)
                ids.append(str(row['id']))
                metadatas.append({
                    "title": title,
                    "genres": genres,
                    "release_date": str(row.get('release_date', '')),
                    "vote_average": float(row.get('vote_average', 0))
                })

            if not documents:
                continue

            # Parallel Encoding
            # print(f"  - Encoding {len(documents)} items...")
            if pool:
                embeddings = model.encode_multi_process(documents, pool)
            else:
                embeddings = model.encode(documents, convert_to_numpy=True)

            # Upload in batches
            for i in range(0, len(ids), BATCH_SIZE):
                b_ids = ids[i:i+BATCH_SIZE]
                b_emb = embeddings[i:i+BATCH_SIZE].tolist()
                b_meta = metadatas[i:i+BATCH_SIZE]
                b_doc = documents[i:i+BATCH_SIZE]
                
                future = upload_executor.submit(collection.upsert, ids=b_ids, embeddings=b_emb, metadatas=b_meta, documents=b_doc)
                upload_futures.append(future)

            processed_count += len(ids)
            elapsed = time.time() - start_time
            rate = processed_count / elapsed
            print(f"✅ Processed {processed_count} movies ({rate:.1f} movies/s) | Active Uploads: {len(upload_futures)}")

            # Memory cleanup
            # Clean up completed futures to avoid memory leak
            done, not_done = concurrent.futures.wait(upload_futures, timeout=0)
            upload_futures = list(not_done)

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
    finally:
        print("Finishing pending uploads...")
        concurrent.futures.wait(upload_futures)
        upload_executor.shutdown()
        if pool:
            print("Stopping encoding pool...")
            model.stop_multi_process_pool(pool)

    print(f"🎉 Done! Total: {processed_count} movies in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    main()
