# src/search/stopwords.py
# Common English stopwords to exclude from indexing and search queries.

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "that", "this", "these", "those", "it", "its", "as", "up", "out",
    "about", "into", "through", "during", "before", "after", "above",
    "below", "between", "each", "so", "than", "too", "very", "just",
    "not", "no", "nor", "only", "own", "same", "also", "then", "once"
}


def remove_stopwords(words: list[str]) -> list[str]:
    """Remove stopwords from a list of words."""
    return [w for w in words if w not in STOPWORDS]