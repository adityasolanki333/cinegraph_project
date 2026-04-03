import zipfile
import os

zip_path = 'datasets/archive (1).zip'
extract_path = 'datasets'

print(f"Extracting {zip_path} to {extract_path}...")
try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_path)
    print("Extraction complete.")
except Exception as e:
    print(f"Error extracting: {e}")
