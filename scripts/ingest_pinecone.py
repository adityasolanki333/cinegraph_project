"""
Pinecone Movie Data Ingestion Script
=====================================
Reads datasets/TMDB_all_movies.csv, generates all-MiniLM-L6-v2 embeddings,
and upserts them to a Pinecone index named 'cinema-guide'.

Usage:
    python scripts/ingest_pinecone.py
    python scripts/ingest_pinecone.py --limit 5000   # ingest first N rows only
    python scripts/ingest_pinecone.py --batch 200    # custom upsert batch size

Requirements:
    pip install pinecone sentence-transformers pandas python-dotenv tqdm

Environment variables (.env):
    PINECONE_API_KEY=<your_key>
"""

import os
import sys
import time
import argparse
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# ─── Config ──────────────────────────────────────────────────────────────────
CSV_PATH      = "datasets/TMDB_all_movies.csv"
INDEX_NAME    = "cinema-guide"
DIMENSION     = 384          # all-MiniLM-L6-v2 output dimension
METRIC        = "cosine"
MODEL_NAME    = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 2000         # rows read per CSV chunk
DEFAULT_BATCH = 150          # vectors per Pinecone upsert call (stay under 4 MB)
NAMESPACE     = "movies"

# Read API key — supports both common naming conventions
PINECONE_API_KEY = (
    os.environ.get("PINECONE_API_KEY") or
    os.environ.get("PINE_CONE_API_KEY") or
    os.environ.get("PINECONE_KEY") or
    ""
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from movies.ml.embedding_text import build_enriched_text
except ImportError:
    def build_enriched_text(movie_data):
        title = str(movie_data.get("title", "") or "")
        overview = str(movie_data.get("overview", "") or "")
        genres = str(movie_data.get("genres", "") or "")
        director = str(movie_data.get("director", "") or "")
        cast = str(movie_data.get("cast", "") or "")[:120]
        keywords = str(movie_data.get("keywords", "") or "")
        tagline = str(movie_data.get("tagline", "") or "")
        release_date = str(movie_data.get("release_date", "") or "")
        release_year = str(movie_data.get("release_year", "") or "")
        if not release_year and release_date and len(release_date) >= 4:
            release_year = release_date[:4]
        themes_parts = [t for t in [keywords, tagline] if t]
        themes = ", ".join(themes_parts)
        parts = [f"Title: {title}."]
        if release_year:
            parts.append(f"Year: {release_year}.")
        if overview:
            parts.append(f"Overview: {overview}")
        if genres:
            parts.append(f"Genres: {genres}.")
        if themes:
            parts.append(f"Themes: {themes}.")
        if director:
            parts.append(f"Director: {director}.")
        if cast:
            parts.append(f"Cast: {cast}.")
        return " ".join(parts).strip()


def build_text_soup(row) -> str:
    return build_enriched_text(row)


def safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_str(val, default="") -> str:
    if pd.isna(val):
        return default
    return str(val).strip()


def build_metadata(row) -> dict:
    """
    Build Pinecone metadata dict.
    Stores: title, overview (plot), genres, release_date, original_language,
            director, tagline, imdb_rating.
    Omits:  poster_path, vote_count, vote_average, runtime, popularity.
    Pinecone only accepts str/float/bool — no None/NaN.
    """
    meta = {}

    # String fields — only add if non-empty
    str_fields = {
        "title":             "title",
        "overview":          "overview",    # ← plot detail
        "genres":            "genres",
        "release_date":      "release_date",
        "original_language": "original_language",
        "director":          "director",
        "tagline":           "tagline",
    }
    for key, col in str_fields.items():
        val = safe_str(row.get(col))
        if val:
            # Pinecone metadata string limit is 40 KB; cap overview just in case
            meta[key] = val[:1000] if key == "overview" else val

    release_date = safe_str(row.get("release_date"))
    if release_date and len(release_date) >= 4:
        meta["release_year"] = release_date[:4]

    val = safe_float(row.get("imdb_rating"))
    if val and val == val:
        meta["imdb_rating"] = val

    pop_val = safe_float(row.get("popularity"))
    if pop_val and pop_val == pop_val:
        meta["popularity"] = pop_val

    vote_val = safe_float(row.get("vote_average"))
    if vote_val and vote_val == vote_val:
        meta["vote_average"] = vote_val

    poster = safe_str(row.get("poster_path"))
    if poster:
        meta["poster_path"] = poster

    return meta


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest TMDB movies into Pinecone")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to ingest (0 = all)")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH, help="Upsert batch size")
    parser.add_argument("--dry-run", action="store_true", help="Parse CSV only, no upload")
    args = parser.parse_args()

    # ── 1. Validate API key ──────────────────────────────────────────────────
    if not PINECONE_API_KEY:
        print("❌  No Pinecone API key found.")
        print("    Add one of these to your .env:")
        print("      PINECONE_API_KEY=pc-xxxxxxxxxxxx")
        sys.exit(1)

    print("✅  Pinecone API key loaded.")

    # ── 2. Connect to Pinecone & ensure index exists ─────────────────────────
    if not args.dry_run:
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=PINECONE_API_KEY)

        existing = [idx.name for idx in pc.list_indexes()]
        if INDEX_NAME not in existing:
            print(f"📦  Creating index '{INDEX_NAME}' (dim={DIMENSION}, metric={METRIC})...")
            pc.create_index(
                name=INDEX_NAME,
                dimension=DIMENSION,
                metric=METRIC,
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            # Wait for index to be ready
            print("⏳  Waiting for index to be ready...")
            while not pc.describe_index(INDEX_NAME).status["ready"]:
                time.sleep(2)
            print("✅  Index ready.")
        else:
            print(f"✅  Index '{INDEX_NAME}' already exists.")

        index = pc.Index(INDEX_NAME)
        stats = index.describe_index_stats()
        already_indexed = stats.total_vector_count
        print(f"📊  Vectors already in index: {already_indexed:,}")
    else:
        index = None
        print("🔍  Dry-run mode — no Pinecone uploads.")

    # ── 3. Load embedding model ───────────────────────────────────────────────
    print(f"\n🤖  Loading model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    print("✅  Model loaded.")

    # ── 4. Validate CSV ───────────────────────────────────────────────────────
    if not os.path.exists(CSV_PATH):
        print(f"❌  CSV not found: {CSV_PATH}")
        sys.exit(1)

    # ── 5. Process CSV in chunks ──────────────────────────────────────────────
    USE_COLS = [
        "id", "title", "overview", "genres", "tagline", "director", "cast",
        "vote_average", "vote_count", "popularity", "release_date",
        "original_language", "poster_path", "runtime", "imdb_rating",
    ]

    reader = pd.read_csv(
        CSV_PATH,
        chunksize=CHUNK_SIZE,
        usecols=[c for c in USE_COLS],   # only load needed columns
        dtype={"id": str, "title": str, "overview": str, "genres": str},
        low_memory=False,
    )

    total_processed = 0
    total_upserted  = 0
    start_time      = time.time()

    print(f"\n⚡  Starting ingestion  (batch={args.batch}, limit={args.limit or 'ALL'})\n")

    try:
        for chunk_idx, chunk in enumerate(reader):
            if args.limit > 0 and total_processed >= args.limit:
                break

            # Drop rows missing essential fields
            chunk = chunk.dropna(subset=["id", "title", "overview"])
            chunk = chunk[chunk["overview"].str.strip().str.len() > 10]
            if chunk.empty:
                continue

            if args.limit > 0:
                remaining = args.limit - total_processed
                chunk = chunk.head(remaining)

            # Build text soups
            soups = [build_text_soup(row) for _, row in chunk.iterrows()]
            ids   = chunk["id"].astype(str).tolist()

            # Embed
            embeddings = model.encode(
                soups,
                batch_size=64,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Build Pinecone vectors: list of (id, embedding, metadata)
            vectors = []
            for i, (_, row) in enumerate(chunk.iterrows()):
                vectors.append({
                    "id":       ids[i],
                    "values":   embeddings[i].tolist(),
                    "metadata": build_metadata(row),
                })

            # Upsert in batches
            if not args.dry_run and index:
                for i in range(0, len(vectors), args.batch):
                    batch_vecs = vectors[i : i + args.batch]
                    index.upsert(vectors=batch_vecs, namespace=NAMESPACE)
                    total_upserted += len(batch_vecs)

            total_processed += len(chunk)

            elapsed = time.time() - start_time
            rate    = total_processed / elapsed
            print(
                f"  chunk {chunk_idx+1:>4} | "
                f"processed {total_processed:>7,} | "
                f"upserted {total_upserted:>7,} | "
                f"{rate:>7.1f} movies/s"
            )

    except KeyboardInterrupt:
        print("\n🛑  Interrupted by user.")

    # ── 6. Final stats ────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    print(f"\n🎉  Done!")
    print(f"    Processed : {total_processed:,} movies")
    print(f"    Upserted  : {total_upserted:,} vectors")
    print(f"    Time      : {elapsed:.1f}s  ({total_processed/elapsed:.0f} movies/s avg)")

    if not args.dry_run and index:
        final_stats = index.describe_index_stats()
        print(f"    Index now : {final_stats.total_vector_count:,} total vectors")


if __name__ == "__main__":
    main()
