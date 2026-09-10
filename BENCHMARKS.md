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

## Retrieval evaluation: keyword vs. semantic vs. hybrid

To check whether combining keyword and semantic search (hybrid) actually
works better than either one alone, ran the same 50 test questions
against a 200-document legal/medical corpus (3,138 indexed pages) three
separate times — once with only keyword search turned on, once with only
semantic search turned on, and once with both together (hybrid). This is
called an ablation test: turn a piece off, see how much performance
drops, and you learn how much that piece was actually contributing.

Test files: `tests/run_eval.py` (runs the test), `tests/eval_queries.json`
(the 50 questions and their correct answers).

Note: 50 questions is a small sample, so treat these percentages as
"roughly this good," not exact — the true number could reasonably be off
by about 11 points either way.

The 50 questions were a mix of:
- ~22 questions phrased naturally, with no exact words copied from the
  documents (tests whether the system understands meaning, not just
  matching words)
- ~28 questions built from real phrases pulled out of the documents,
  then lightly reworded (tests whether exact-term matching works)

| Mode           | Found correct doc in top 5 | Avg. rank of correct answer* |
|----------------|----------------------------|-------------------------------|
| Keyword only   | 56.0%                      | 0.517                         |
| Semantic only  | 74.0%                      | 0.642                         |
| Hybrid (both)  | 74.0%                      | 0.655                         |

*Higher is better; 1.0 would mean the correct answer was always ranked
#1.

**What this tells us:**
- Semantic search alone is much stronger than keyword search alone on
  this question set. This confirms the semantic (ChromaDB) layer is
  doing real, meaningful work — not just a nice-to-have.
- Hybrid ties semantic search on "found it in the top 5" and is slightly
  better on "how high it ranked." In other words, combining both methods
  never makes results worse than the better individual method, but it
  also isn't a big win yet — the current 60/40 blend of keyword and
  semantic scores may need tuning.
- Keyword search results depend heavily on exact wording: its score rose
  from 40.9% to 56.0% once added questions built from real document
  phrases, since keyword matching is naturally strong when the question
  uses the same words as the document.

**Next step (not done yet):** try different blend ratios between keyword
and semantic scores (currently fixed at 60% keyword / 40% semantic) to
see if hybrid can be made to clearly beat semantic-only, instead of just
tying it.