# tests/test_vector_search.py
import sys
sys.path.insert(0, 'src')

from search.vector_search import VectorSearch

vs = VectorSearch()

# Index some test documents
docs = [
    {
        "docid": "test1::page1",
        "filepath": "test1.pdf",
        "page": 1,
        "text": "Artificial intelligence and machine learning are transforming computer science."
    },
    {
        "docid": "test2::page1",
        "filepath": "test2.pdf",
        "page": 1,
        "text": "The quick brown fox jumps over the lazy dog."
    },
    {
        "docid": "test3::page1",
        "filepath": "test3.pdf",
        "page": 1,
        "text": "Neural networks and deep learning models require large datasets."
    }
]

vs.index_documents(docs)
print("Indexed 3 documents\n")

# Search semantically
results = vs.search("AI and neural networks", top_k=3)
print("Query: 'AI and neural networks'")
for r in results:
    print(f"  [{r['score']}] {r['filepath']} — {r['snippet']}")