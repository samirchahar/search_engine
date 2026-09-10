# tests/run_eval.py
# Ablation benchmark: compares keyword-only, semantic-only, and hybrid
# retrieval against a labeled query set (tests/eval_queries.json).
# Metrics: Hit Rate@5 and Mean Reciprocal Rank (MRR).

import sys
import os
import json

sys.path.insert(0, 'src')

from extractor.extractor import extract_file
from search.search_engine import SearchEngine
from search.vector_search import VectorSearch

CORPUS_FOLDER = "data/legal_medical"
EVAL_FILE = "tests/eval_queries.json"
TOP_K = 5


def index_corpus(folder):
    supported = ('.pdf', '.txt', '.docx', '.pptx')
    files = [f for f in os.listdir(folder)
             if f.lower().endswith(supported) and not f.startswith('~$')]

    print(f"Indexing {len(files)} file(s) from {folder}...")
    all_docs = []
    for filename in files:
        filepath = os.path.join(folder, filename)
        pages = extract_file(filepath)
        for p in pages:
            all_docs.append({
                "docid": f"{filename}::page{p['page']}",
                "filepath": filepath,
                "page": p["page"],
                "text": p["text"]
            })

    vs = VectorSearch()
    engine = SearchEngine()
    engine.enable_vector_search(vs)
    engine.index_documents(all_docs)
    print(f"Indexed {len(all_docs)} page(s).\n")
    return engine, vs


def rank_of_expected(results, expected_file, top_k):
    for i, r in enumerate(results[:top_k], start=1):
        if os.path.basename(r["filepath"]) == expected_file:
            return i
    return None


def evaluate_mode(name, results_fn, queries):
    hits = 0
    reciprocal_ranks = []
    for q in queries:
        results = results_fn(q["query"])
        rank = rank_of_expected(results, q["expected_file"], TOP_K)
        if rank:
            hits += 1
            reciprocal_ranks.append(1 / rank)
        else:
            reciprocal_ranks.append(0)

    hit_rate = round(hits / len(queries) * 100, 1)
    mrr = round(sum(reciprocal_ranks) / len(queries), 3)
    print(f"{name:15s} Hit Rate@{TOP_K}: {hit_rate}%   MRR: {mrr}")
    return hit_rate, mrr


def main():
    with open(EVAL_FILE) as f:
        queries = json.load(f)

    engine, vs = index_corpus(CORPUS_FOLDER)

    def keyword_only(query):
        words = engine._tokenize(query)
        return engine._keyword_search(words) if words else []

    def semantic_only(query):
        return vs.search(query, top_k=TOP_K)

    def hybrid(query):
        return engine.search(query)

    print(f"Evaluating {len(queries)} queries across 3 retrieval modes:\n")
    evaluate_mode("Keyword-only", keyword_only, queries)
    evaluate_mode("Semantic-only", semantic_only, queries)
    evaluate_mode("Hybrid", hybrid, queries)


if __name__ == "__main__":
    main()