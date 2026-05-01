# main.py
# Entry point for the local search engine (CLI mode).
# Usage: python main.py <folder_path>

import sys
import os

sys.path.insert(0, 'src')

from extractor.extractor import extract_file
from search.search_engine import SearchEngine


def load_folder(folder_path: str, engine: SearchEngine):
    """
    Scan a folder for PDF and TXT files.
    Extract text and index all documents.
    """
    supported = ('.pdf', '.txt', '.docx', '.pptx')
    files = [f for f in os.listdir(folder_path)
             if f.lower().endswith(supported)]

    if not files:
        print(f"No PDF or TXT files found in: {folder_path}")
        return

    print(f"Found {len(files)} file(s). Indexing...")

    all_docs = []
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        pages = extract_file(filepath)
        for page_data in pages:
            docid = f"{filename}::page{page_data['page']}"
            all_docs.append({
                "docid": docid,
                "filepath": filepath,
                "page": page_data["page"],
                "text": page_data["text"]
            })

    engine.index_documents(all_docs)
    print(f"Indexed {len(all_docs)} page(s) across {len(files)} file(s).")
    print()


def run_search_loop(engine: SearchEngine):
    """
    Interactive search loop.
    Prefix query with 'phrase:' for exact phrase search.
    Example: phrase:artificial intelligence
    """
    print("Search engine ready. Type a query and press Enter.")
    print("Tip: prefix with 'phrase:' for exact phrase search.")
    print("Type 'quit' to exit.")
    print()

    while True:
        query = input("Search> ").strip()
        if not query:
            continue
        if query.lower() == 'quit':
            print("Goodbye.")
            break

        if query.lower().startswith("phrase:"):
            actual_query = query[7:].strip()
            results = engine.phrase_search(actual_query)
            search_type = "phrase"
        else:
            results = engine.search(query)
            search_type = "keyword"

        if not results:
            print(f"No results found.\n")
            continue

        print(f"\nFound {len(results)} result(s) [{search_type}]:\n")
        for i, r in enumerate(results, start=1):
            filename = os.path.basename(r['filepath'])
            print(f"  [{i}] {filename} — Page {r['page']} — Score: {r['score']}")
            print(f"      {r['snippet']}")
            print()
            

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a valid folder.")
        sys.exit(1)

    engine = SearchEngine()
    load_folder(folder_path, engine)
    run_search_loop(engine)