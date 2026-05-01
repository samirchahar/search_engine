# src/search/search_engine.py
# Connects Python to the C++ indexer via subprocess.
# The C++ process stays alive for the whole session — index persists in memory.
# TF-IDF ranking applied on top of raw frequency scores from C++.

import subprocess
import os
import re
import math
from search.stopwords import remove_stopwords


INDEXER_PATH = os.path.join(os.path.dirname(__file__), '..', 'indexer', 'indexer.exe')


class SearchEngine:
    def __init__(self):
        # { docid: {"filepath": ..., "page": ..., "text": ...} }
        self.documents = {}

        # Track how many documents each word appears in (for IDF)
        # { word: set of docids }
        self.doc_frequency = {}

        # Total number of documents indexed
        self.total_docs = 0

        # Start the C++ indexer as a persistent process
        self.process = subprocess.Popen(
            [INDEXER_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def _send(self, line: str):
        """Send a single line to the C++ indexer."""
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()

    def _read_line(self) -> str:
        """Read a single line of output from the C++ indexer."""
        return self.process.stdout.readline().strip()

    def index_documents(self, extracted_docs: list[dict]):
        """
        Index a list of extracted documents.
        Also builds doc_frequency table for TF-IDF.
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

                # Track which words appear in this document (for IDF)
                unique_words = set(words)
                for word in unique_words:
                    if word not in self.doc_frequency:
                        self.doc_frequency[word] = set()
                    self.doc_frequency[word].add(docid)

        self.total_docs = len(self.documents)

    def _compute_tfidf(self, docid: str, query_words: list[str], raw_score: int) -> float:
        """
        Compute a TF-IDF influenced score for a document.
        TF = raw frequency score from C++ (total query word occurrences)
        IDF = log(total_docs / docs_containing_word) per query word
        Final score = TF * sum of IDF weights
        """
        if self.total_docs == 0:
            return float(raw_score)

        idf_sum = 0.0
        for word in query_words:
            df = len(self.doc_frequency.get(word, set()))
            if df > 0:
                idf = math.log(self.total_docs / df)
                idf_sum += idf

        return raw_score * idf_sum if idf_sum > 0 else float(raw_score)

    def search(self, query: str) -> list[dict]:
        """
        Keyword search with TF-IDF ranking.
        Returns ranked results with snippets.
        """
        query_words = self._tokenize(query)
        if not query_words:
            return []

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
                "score": round(tfidf_score, 4),
                "snippet": snippet
            })

        # Re-sort by TF-IDF score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def phrase_search(self, query: str) -> list[dict]:
        """
        Exact phrase search — words must appear consecutively.
        Returns ranked results with snippets.
        """
        query_words = self._tokenize(query)
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
            snippet = self._extract_snippet(doc.get("text", ""), query_words)

            results.append({
                "docid": docid,
                "filepath": doc.get("filepath", ""),
                "page": doc.get("page", 1),
                "score": score,
                "snippet": snippet
            })

        return results

    def _tokenize(self, text: str, remove_stops: bool = True) -> list[str]:
        """
        Split text into lowercase words, removing punctuation.
        Optionally removes stopwords (default: True).
        """
        words = re.findall(r'[a-zA-Z0-9]+', text.lower())
        if remove_stops:
            words = remove_stopwords(words)
        return words


    def _extract_snippet(self, text: str, query_words: list[str], context_words: int = 10) -> str:
        """
        Find the first occurrence of any query word in the text.
        Return surrounding context as a snippet.
        """
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
        """Shut down the C++ indexer process cleanly."""
        self._send("END")
        self.process.stdin.close()
        self.process.wait()