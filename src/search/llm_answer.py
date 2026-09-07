import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


def generate_answer(query: str, results: list[dict], max_context: int = 2) -> str:
    if not results:
        return "No relevant documents found to answer this query."

    top_score = results[0]["score"]
    relevant = [r for r in results if top_score > 0 and r["score"] >= top_score * 0.5]
    relevant = relevant[:max_context] if relevant else results[:1]

    context = "\n\n".join(r["snippet"] for r in relevant)

    prompt = (
        "You are summarizing excerpts from the user's own local technical/academic documents "
        "(e.g. computer science, networking topics). Treat all content as legitimate and safe. "
        "Using only the excerpts below, answer the question in 2-3 plain sentences. "
        "Do not refuse, moralize, or add disclaimers — just summarize the given text.\n\n"
        f"Excerpts:\n{context}\n\nQuestion: {query}\nAnswer:"
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