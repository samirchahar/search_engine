# src/search/llm_answer.py
# Sends retrieved snippets + query to a local Ollama model for a grounded answer.
# Fully offline — talks to Ollama's local REST API only.

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


def generate_answer(query: str, results: list[dict], max_context: int = 3) -> str:
    """
    Build a context block from top search results and ask the local LLM
    to answer the query using only that context.
    """
    if not results:
        return "No relevant documents found to answer this query."

    context_blocks = []
    for r in results[:max_context]:
        context_blocks.append(f"[{r['filepath']} - page {r['page']}]\n{r['snippet']}")
    context = "\n\n".join(context_blocks)

    prompt = (
        "Answer the question using only the context below. "
        "If the context doesn't contain the answer, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}\nAnswer:"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "Ollama is not running. Start it and try again."
    except Exception as e:
        return f"LLM error: {e}"