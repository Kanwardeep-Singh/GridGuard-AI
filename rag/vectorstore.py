"""
Vector store for the ICS knowledge base.

Design choice: this uses TF-IDF vectors (scikit-learn) indexed with FAISS,
rather than calling an external embedding API. That keeps retrieval fully
functional and testable with zero API keys and zero network calls - a
deliberate tradeoff for a security tool that should be auditable and
runnable air-gapped. If higher retrieval quality is needed later, swap
`_vectorize` to call a real embedding model without changing the rest of
the pipeline (FAISS index + search interface stay the same).
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from rag.ingest import build_chunks, Chunk
from config.settings import settings


class VectorStore:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=4096)
        self.index: faiss.Index | None = None
        self.chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk] | None = None) -> "VectorStore":
        self.chunks = chunks or build_chunks()
        if not self.chunks:
            raise ValueError("No knowledge base documents found to index.")

        texts = [c.text for c in self.chunks]
        tfidf = self.vectorizer.fit_transform(texts).toarray().astype("float32")
        faiss.normalize_L2(tfidf)

        self.index = faiss.IndexFlatIP(tfidf.shape[1])
        self.index.add(tfidf)
        return self

    def search(self, query: str, top_k: int | None = None) -> list[tuple[Chunk, float]]:
        if self.index is None:
            raise RuntimeError("Call .build() (or .load()) before .search()")
        top_k = top_k or settings.cfg["rag"]["top_k"]

        q_vec = self.vectorizer.transform([query]).toarray().astype("float32")
        faiss.normalize_L2(q_vec)
        scores, indices = self.index.search(q_vec, min(top_k, len(self.chunks)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    def save(self, index_dir: Path | None = None) -> None:
        index_dir = index_dir or settings.vectorstore_dir
        index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_dir / "index.faiss"))
        with open(index_dir / "meta.pkl", "wb") as f:
            pickle.dump({"chunks": self.chunks, "vectorizer": self.vectorizer}, f)

    @classmethod
    def load(cls, index_dir: Path | None = None) -> "VectorStore":
        index_dir = index_dir or settings.vectorstore_dir
        store = cls()
        store.index = faiss.read_index(str(index_dir / "index.faiss"))
        with open(index_dir / "meta.pkl", "rb") as f:
            data = pickle.load(f)
        store.chunks = data["chunks"]
        store.vectorizer = data["vectorizer"]
        return store


if __name__ == "__main__":
    store = VectorStore().build()
    store.save()
    for chunk, score in store.search("denial of service against RTU", top_k=3):
        print(f"[{score:.3f}] {chunk.source}: {chunk.text[:120]}...")
