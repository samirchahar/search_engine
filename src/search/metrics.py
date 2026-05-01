# src/search/metrics.py
# Tracks performance metrics for indexing and search operations.
# All metrics are stored in memory and can be exported as a summary.
# These numbers are what go on your resume.

import time
from dataclasses import dataclass, field


@dataclass
class IndexMetrics:
    """Metrics captured during a single indexing session."""
    files_indexed: int = 0
    pages_indexed: int = 0
    total_words: int = 0
    index_time_ms: float = 0.0

    @property
    def pages_per_second(self) -> float:
        if self.index_time_ms <= 0:
            return 0.0
        return round(self.pages_indexed / (self.index_time_ms / 1000), 1)

    @property
    def words_per_second(self) -> float:
        if self.index_time_ms <= 0:
            return 0.0
        return round(self.total_words / (self.index_time_ms / 1000), 1)

    def summary(self) -> str:
        return (
            f"Indexed {self.files_indexed} file(s), "
            f"{self.pages_indexed} page(s), "
            f"{self.total_words} words in {self.index_time_ms}ms "
            f"({self.pages_per_second} pages/sec)"
        )


@dataclass
class QueryMetrics:
    """Metrics captured for a single search query."""
    query: str = ""
    mode: str = "keyword"
    results_count: int = 0
    latency_ms: float = 0.0

    def summary(self) -> str:
        return (
            f"Query '{self.query}' [{self.mode}] → "
            f"{self.results_count} result(s) in {self.latency_ms}ms"
        )


class MetricsTracker:
    """
    Central metrics tracker for the whole session.
    Stores all indexing and query events.
    Call summary() at any time to get a full report.
    """

    def __init__(self):
        self.index_sessions: list[IndexMetrics] = []
        self.queries: list[QueryMetrics] = []
        self._index_start: float = 0.0
        self._query_start: float = 0.0

    # ── Indexing ──────────────────────────────────────────────────────────

    def start_indexing(self):
        """Call this just before indexing begins."""
        self._index_start = time.time()

    def finish_indexing(self, files: int, pages: int, words: int) -> IndexMetrics:
        """Call this immediately after indexing completes."""
        elapsed_ms = round((time.time() - self._index_start) * 1000, 2)
        m = IndexMetrics(
            files_indexed=files,
            pages_indexed=pages,
            total_words=words,
            index_time_ms=elapsed_ms
        )
        self.index_sessions.append(m)
        return m

    # ── Queries ───────────────────────────────────────────────────────────

    def start_query(self):
        """Call this just before a search query runs."""
        self._query_start = time.time()

    def finish_query(self, query: str, mode: str,
                     results_count: int) -> QueryMetrics:
        """Call this immediately after a search query completes."""
        elapsed_ms = round((time.time() - self._query_start) * 1000, 2)
        m = QueryMetrics(
            query=query,
            mode=mode,
            results_count=results_count,
            latency_ms=elapsed_ms
        )
        self.queries.append(m)
        return m

    # ── Summary ───────────────────────────────────────────────────────────

    def summary(self) -> str:
        lines = ["=== Performance Metrics ===", ""]

        if self.index_sessions:
            lines.append("-- Indexing --")
            for m in self.index_sessions:
                lines.append(f"  {m.summary()}")
            lines.append("")

        if self.queries:
            lines.append("-- Queries --")
            latencies = [q.latency_ms for q in self.queries]
            avg = round(sum(latencies) / len(latencies), 2)
            min_l = min(latencies)
            max_l = max(latencies)
            lines.append(f"  Total queries: {len(self.queries)}")
            lines.append(f"  Avg latency:   {avg}ms")
            lines.append(f"  Min latency:   {min_l}ms")
            lines.append(f"  Max latency:   {max_l}ms")
            lines.append("")
            lines.append("  Recent queries:")
            for q in self.queries[-5:]:
                lines.append(f"    {q.summary()}")

        return "\n".join(lines)

    def avg_query_latency_ms(self) -> float:
        if not self.queries:
            return 0.0
        return round(
            sum(q.latency_ms for q in self.queries) / len(self.queries), 2)