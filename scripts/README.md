
# Utility Scripts

This directory contains various utility and testing scripts for the Cinema Guide project.

## How to Run

Most scripts assume they are run from the **project root directory** to correctly resolve file paths and Django settings.

**Example:**
```bash
# Correct way (from project root)
python scripts/check_count.py

# Incorrect way (cd into scripts)
cd scripts
python check_count.py  # May fail due to path issues
```

## Script Descriptions

*   `check_count.py`: Verifies the number of embeddings in ChromaDB.
*   `test_api.py`: Tests basic API connectivity.
*   `test_chroma_endpoint.py`: Validates the Semantic Search API endpoint.
*   `test_list_flow.py`: Tests the User Lists functionality (Create, Add, Remove, Delete).
*   `ingest_standalone.py`: A standalone version of the ingestion logic (legacy).
*   `reset_chroma.py`: **CAUTION** - Deletes and recreates the ChromaDB collection.
