# src/search/vector_search.py
# Vector search layer using ChromaDB and sentence-transformers.
# Converts document text to embeddings and enables semantic similarity search.
# Runs fully offline — no internet or cloud required.

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import chromadb
from sentence_transformers import SentenceTransformer
from search.logger import log


# Local model — downloaded once, cached on disk after first run
MODEL_NAME = "all-MiniLM-L6-v2"

# ChromaDB stores its data here
CHROMA_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'chroma_store')


class VectorSearch:
    def __init__(self):
        log.info("Loading sentence-transformer model...")
        self.model = SentenceTransformer(MODEL_NAME)
        log.info(f"Model loaded: {MODEL_NAME}")

        # Persistent ChromaDB client — data survives between sessions
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)

        # One collection holds all document vectors
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}  # cosine similarity
        )

        log.info(f"ChromaDB ready — {self.collection.count()} vectors stored")

    def index_documents(self, extracted_docs: list[dict]):
        """
        Convert document text to vectors and store in ChromaDB.
        Each doc: {"docid": ..., "filepath": ..., "page": ..., "text": ...}
        Skips documents already in the collection.
        """
        if not extracted_docs:
            return

        # Find which docids are not yet indexed
        existing = set()
        try:
            all_ids = self.collection.get()["ids"]
            existing = set(all_ids)
        except Exception:
            pass

        new_docs = [d for d in extracted_docs
                    if d["docid"] not in existing]

        if not new_docs:
            log.info("Vector index: all documents already indexed")
            return

        texts = [d["text"] for d in new_docs]
        ids = [d["docid"] for d in new_docs]
        metadatas = [
            {
                "filepath": d["filepath"],
                "page": str(d["page"]),
                "docid": d["docid"]
            }
            for d in new_docs
        ]

        log.info(f"Generating embeddings for {len(new_docs)} document(s)...")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        embeddings_list = [e.tolist() for e in embeddings]

        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=metadatas
        )

        log.info(f"Vector index: added {len(new_docs)} document(s). "
                 f"Total: {self.collection.count()}")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Search for semantically similar documents.
        Returns top_k results ranked by cosine similarity.
        """
        if self.collection.count() == 0:
            return []

        query_embedding = self.model.encode([query])[0].tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count())
        )

        output = []
        ids = results["ids"][0]
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]

        for i, docid in enumerate(ids):
            # Convert cosine distance to similarity score (0-1)
            similarity = round(1 - distances[i], 4)
            meta = metadatas[i]

            output.append({
                "docid": docid,
                "filepath": meta["filepath"],
                "page": int(meta["page"]),
                "score": similarity,
                "snippet": self._extract_snippet(documents[i])
            })

        return output

    def remove_documents(self, filepaths: list[str]):
        """
        Remove all vectors associated with given filepaths.
        Called when a file is removed from the index.
        """
        try:
            all_data = self.collection.get()
            ids_to_remove = [
                id_ for id_, meta in zip(
                    all_data["ids"], all_data["metadatas"])
                if meta["filepath"] in filepaths
            ]
            if ids_to_remove:
                self.collection.delete(ids=ids_to_remove)
                log.info(f"Vector index: removed {len(ids_to_remove)} "
                         f"vector(s) for {len(filepaths)} file(s)")
        except Exception as e:
            log.error(f"Vector removal error: {e}")

    def reset(self):
        """Wipe the entire vector collection and start fresh."""
        self.client.delete_collection("documents")
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        log.info("Vector index reset")

    def _extract_snippet(self, text: str, max_words: int = 80) -> str:
        """Return first max_words words of text as a snippet."""
        words = text.split()
        snippet = " ".join(words[:max_words])
        return f"...{snippet}..." if len(words) > max_words else snippet