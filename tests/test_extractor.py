# tests/test_extractor.py
import sys
sys.path.insert(0, 'src')

from extractor.extractor import extract_file

# Replace with your scanned PDF filename
results = extract_file('data/myfile.pdf')
print(f"Total pages/chunks extracted: {len(results)}")
for r in results:
    print(f"\n--- Page {r['page']} ---")
    print(r['text'][:500])
