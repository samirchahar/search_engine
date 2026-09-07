# src/search/search_engine.py
# Main search engine — connects Python to the C++ indexer via subprocess.
# Also coordinates with VectorSearch for hybrid retrieval.
# Hybrid search = keyword (C++ TF-IDF) + semantic (ChromaDB vectors) combined.

import subprocess
import os
import re
import math
from search.stopwords import remove_stopwords
from search.logger import log


INDEXER_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'indexer', 'indexer.exe')


class SearchEngine:
    def __init__(self):
        # { docid: {"filepath": ..., "page": ..., "text": ...} }
        self.documents = {}

        # { word: set of docids } — for TF-IDF IDF calculation
        self.doc_frequency = {}

        self.total_docs = 0

        # Vector search — imported here to avoid circular imports
        self.vector_search = None

        # Start C++ indexer as persistent process
        self.process = subprocess.Popen(
            [INDEXER_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def enable_vector_search(self, vector_search):
        """
        Attach a VectorSearch instance to enable hybrid retrieval.
        Called from the UI after VectorSearch is initialized.
        """
        self.vector_search = vector_search
        log.info("Hybrid search enabled")

    def _send(self, line: str):
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def _read_line(self) -> str:
        return self.process.stdout.readline().strip()

    def index_documents(self, extracted_docs: list[dict]):
        """
        Index documents in both C++ inverted index and vector store.
        """
        for doc in extracted_docs:
            docid = doc["docid"]
            self.documents[docid] = {
                "filepath": doc["filepath"],
                "page": doc["page"],
                "text": doc["text"]
            }
            words = self._tokenize(doc["text"])
            if words:
                self._send(f"ADD {docid} {' '.join(words)}")
                unique_words = set(words)
                for word in unique_words:
                    if word not in self.doc_frequency:
                        self.doc_frequency[word] = set()
                    self.doc_frequency[word].add(docid)

        self.total_docs = len(self.documents)

        # Also index in vector store if enabled
        if self.vector_search:
            self.vector_search.index_documents(extracted_docs)

        log.info(f"Indexed {len(extracted_docs)} document(s)")

    def search(self, query: str) -> list[dict]:
        """
        Hybrid search: keyword + vector results merged and re-ranked.
        Falls back to keyword-only if vector search is not enabled.
        """
        query_words = self._tokenize(query)
        if not query_words:
            return []

        # Always run keyword search
        keyword_results = self._keyword_search(query_words)

        # Run vector search if available
        if self.vector_search:
            vector_results = self.vector_search.search(query, top_k=10)
            return self._merge_results(keyword_results, vector_results)

        return keyword_results

    def _keyword_search(self, query_words: list[str]) -> list[dict]:
        """Run keyword search via C++ indexer with TF-IDF ranking."""
        self._send(f"SEARCH {' '.join(query_words)}")
        first_line = self._read_line()
        if not first_line.startswith("RESULTS"):
            return []

        count = int(first_line.split()[1])
        results = []

        for _ in range(count):
            line = self._read_line()
            parts = line.split()
            docid = parts[0]
            raw_score = int(parts[1])

            doc = self.documents.get(docid, {})
            tfidf_score = self._compute_tfidf(docid, query_words, raw_score)
            snippet = self._extract_snippet(doc.get("text", ""), query_words)

            results.append({
                "docid": docid,
                "filepath": doc.get("filepath", ""),
                "page": doc.get("page", 1),
                "score": tfidf_score,
                "snippet": snippet,
                "match_type": "keyword"
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def _merge_results(self, keyword_results: list[dict],
                       vector_results: list[dict]) -> list[dict]:
        """
        Merge keyword and vector results into a single ranked list.
        Strategy:
          - Normalize both score ranges to 0-1
          - Combined score = 0.6 * keyword + 0.4 * vector
          - Documents in both lists get a 0.1 bonus
          - Sort by combined score descending
        """
        # Build lookup maps
        keyword_map = {r["docid"]: r for r in keyword_results}
        vector_map = {r["docid"]: r for r in vector_results}

        # Normalize keyword scores to 0-1
        kw_scores = [r["score"] for r in keyword_results]
        kw_max = max(kw_scores) if kw_scores else 1
        kw_min = min(kw_scores) if kw_scores else 0
        kw_range = kw_max - kw_min if kw_max != kw_min else 1

        # Normalize vector scores (already 0-1 cosine similarity)
        vec_scores = [r["score"] for r in vector_results]
        vec_max = max(vec_scores) if vec_scores else 1
        vec_min = min(vec_scores) if vec_scores else 0
        vec_range = vec_max - vec_min if vec_max != vec_min else 1

        # Collect all unique docids
        all_docids = set(keyword_map.keys()) | set(vector_map.keys())

        merged = []
        for docid in all_docids:
            kw_result = keyword_map.get(docid)
            vec_result = vector_map.get(docid)

            # Normalized scores
            kw_norm = ((kw_result["score"] - kw_min) / kw_range
                       if kw_result else 0.0)
            vec_norm = ((vec_result["score"] - vec_min) / vec_range
                        if vec_result else 0.0)

            # Bonus for appearing in both
            overlap_bonus = 0.1 if (kw_result and vec_result) else 0.0

            combined = round(
                0.6 * kw_norm + 0.4 * vec_norm + overlap_bonus, 4)

            # Use keyword result as base if available, else vector result
            base = kw_result if kw_result else vec_result
            doc = self.documents.get(docid, {})

            # Determine match type label
            if kw_result and vec_result:
                match_type = "hybrid"
            elif kw_result:
                match_type = "keyword"
            else:
                match_type = "semantic"

            merged.append({
                "docid": docid,
                "filepath": base.get("filepath",
                                     doc.get("filepath", "")),
                "page": base.get("page", doc.get("page", 1)),
                "score": combined,
                "snippet": base.get("snippet", ""),
                "match_type": match_type
            })

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged

    def phrase_search(self, query: str) -> list[dict]:
        """Exact phrase search — words must appear consecutively."""
        query_words = self._tokenize(query, remove_stops=False)
        if not query_words:
            return []

        self._send(f"PHRASE {' '.join(query_words)}")
        first_line = self._read_line()
        if not first_line.startswith("RESULTS"):
            return []

        count = int(first_line.split()[1])
        results = []

        for _ in range(count):
            line = self._read_line()
            parts = line.split()
            docid = parts[0]
            score = int(parts[1])
            doc = self.documents.get(docid, {})
            snippet = self._extract_snippet(
                doc.get("text", ""), query_words)

            results.append({
                "docid": docid,
                "filepath": doc.get("filepath", ""),
                "page": doc.get("page", 1),
                "score": score,
                "snippet": snippet,
                "match_type": "phrase"
            })

        return results

    def _compute_tfidf(self, docid: str,
                       query_words: list[str],
                       raw_score: int) -> float:
        if self.total_docs == 0:
            return float(raw_score)
        idf_sum = 0.0
        for word in query_words:
            df = len(self.doc_frequency.get(word, set()))
            if df > 0:
                idf_sum += math.log(self.total_docs / df)
        return round(raw_score * idf_sum, 4) if idf_sum > 0 else float(raw_score)

    def _tokenize(self, text: str,
                  remove_stops: bool = True) -> list[str]:
        words = re.findall(r'[a-zA-Z0-9]+', text.lower())
        if remove_stops:
            words = remove_stopwords(words)
        return words

    def _extract_snippet(self, text: str,
                         query_words: list[str],
                         context_words: int = 45) -> str:
        words = text.split()
        text_lower = text.lower()
        for qword in query_words:
            idx = text_lower.find(qword)
            if idx != -1:
                before = text[:idx].split()
                word_pos = len(before)
                start = max(0, word_pos - context_words)
                end = min(len(words), word_pos + context_words + 1)
                snippet = " ".join(words[start:end])
                return f"...{snippet}..."
        return text[:200]

    def close(self):
        self._send("END")
        self.process.stdin.close()
        self.process.wait()