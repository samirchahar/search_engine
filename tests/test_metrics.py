# tests/test_metrics.py
import sys
sys.path.insert(0, 'src')
from search.metrics import MetricsTracker
import time

tracker = MetricsTracker()

tracker.start_indexing()
time.sleep(0.05)
tracker.finish_indexing(files=3, pages=90, words=45000)

tracker.start_query()
time.sleep(0.008)
tracker.finish_query("artificial intelligence", "keyword", 4)

tracker.start_query()
time.sleep(0.012)
tracker.finish_query("parsing", "keyword", 20)

print(tracker.summary())