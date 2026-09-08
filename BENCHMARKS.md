# Argus Benchmarks

Performance and relevance testing on two corpora: a general mixed-topic
document set, and a domain-specific legal/medical corpus matching Argus's
intended use case (offline search over sensitive documents).

## Test 1: General corpus

- 22 files, 1,643 pages, 574,517 words (mix of PDF, DOCX, PPTX, TXT,
  including a scanned page processed via OCR)
- Indexing: 57.8s total, 28.2 pages/sec
- 8 test queries (keyword, phrase, and conceptual/semantic)
- Query latency: avg 22.0ms, min 0.39ms, max 77.38ms

## Test 2: Legal and medical corpus

- 55 real public documents (court filings and medical research papers),
  500 pages, 194,748 words
- Indexing: 18.3s total, 27.3 pages/sec
- 8 test queries (keyword, phrase, and conceptual/semantic) across both
  legal and medical topics
- Query latency: avg 18.16ms, min 0.24ms, max 31.58ms

## Combined benchmark

Weighted across both test runs (2,143 pages, 769,265 words, 16 queries
total):

- Indexing throughput: 28.0 pages/sec
- Query latency: avg 20.08ms, min 0.24ms, max 77.38ms

This spans general mixed-topic documents and a domain-specific
legal/medical corpus, so it reflects performance across different
document types and query patterns rather than a single best case.

## Relevance checks

Conceptual queries with no literal keyword overlap with the target
document still returned the correct source in the top result, confirming
the semantic (ChromaDB) layer contributes real retrieval value beyond
keyword matching. Examples:

- "what happens when two parties disagree over land ownership" correctly
  surfaced a land ownership dispute case.
- "how does a computer detect malicious traffic" correctly surfaced the
  intrusion detection systems section of a networking textbook.

## Methodology

Both tests used a cold cache (chroma_store cleared before indexing) to
measure true from-scratch indexing time. Query latency is measured
server-side via MetricsTracker, covering the C++ inverted index lookup,
TF-IDF scoring, ChromaDB semantic search, and hybrid result merging (does
not include LLM answer generation time, which is separate and depends on
Ollama/hardware).