import sys
from pypdf import PdfReader
with open("scripts/output_utf8.txt", "w", encoding="utf-8") as f:
    reader = PdfReader(sys.argv[1])
    for page in reader.pages:
        f.write(page.extract_text() + "\n")
