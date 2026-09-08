# main.py
# Entry point for the local search engine (CLI mode).
# Usage: python main.py <folder_path>

import sys
import os

sys.path.insert(0, 'src')

from extractor.extractor import extract_file
from search.search_engine import SearchEngine
from search.vector_search import VectorSearch
from search.llm_answer import generate_answer
from search.metrics import MetricsTracker


def load_folder(folder_path: str, engine: SearchEngine, metrics: MetricsTracker):
    """
    Scan a folder for PDF and TXT files.
    Extract text and index all documents.
    """
    supported = ('.pdf', '.txt', '.docx', '.pptx')
    files = [f for f in os.listdir(folder_path)
        if f.lower().endswith(supported) and not f.startswith('~$')]

    if not files:
        print(f"No PDF or TXT files found in: {folder_path}")
        return

    print(f"Found {len(files)} file(s). Indexing...")
    metrics.start_indexing()

    all_docs = []
    total_words = 0
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        pages = extract_file(filepath)
        for page_data in pages:
            docid = f"{filename}::page{page_data['page']}"
            total_words += len(page_data["text"].split())
            all_docs.append({
                "docid": docid,
                "filepath": filepath,
                "page": page_data["page"],
                "text": page_data["text"]
            })

    engine.index_documents(all_docs)
    m = metrics.finish_indexing(files=len(files), pages=len(all_docs), words=total_words)
    print(f"Indexed {len(all_docs)} page(s) across {len(files)} file(s).")
    print(f"  {m.summary()}")
    print()

def run_search_loop(engine: SearchEngine, metrics: MetricsTracker):
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
            print(metrics.summary())
            print("Goodbye.")
            break

        metrics.start_query()
        if query.lower().startswith("phrase:"):
            actual_query = query[7:].strip()
            results = engine.phrase_search(actual_query)
            search_type = "phrase"
        else:
            results = engine.search(query)
            search_type = "keyword"
        qm = metrics.finish_query(query, search_type, len(results))

        if not results:
            print(f"No results found. ({qm.latency_ms}ms)\n")
            continue

        print(f"\nFound {len(results)} result(s) [{search_type}] in {qm.latency_ms}ms:\n")
        for i, r in enumerate(results, start=1):
            filename = os.path.basename(r['filepath'])
            print(f"  [{i}] {filename} — Page {r['page']} — Score: {r['score']}")
            print(f"      {r['snippet']}")
            print()

        answer = generate_answer(query, results)
        print(f"AI Answer: {answer}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a valid folder.")
        sys.exit(1)

    metrics = MetricsTracker()
    engine = SearchEngine()
    print("Loading semantic search model...")
    vs = VectorSearch()
    engine.enable_vector_search(vs)
    load_folder(folder_path, engine, metrics)
    run_search_loop(engine, metrics)