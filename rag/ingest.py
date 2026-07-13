"""
Ingests plain-text documents from rag/knowledge_base/ into chunks ready
for embedding + indexing by vectorstore.py.

Only public-domain / summary material lives in knowledge_base/ - see
README for why the actual IEC 61850 standard text is not bundled here.
"""
from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import settings

KB_DIR = Path(__file__).resolve().parent / "knowledge_base"


@dataclass
class Chunk:
    text: str
    source: str


def load_documents(kb_dir: Path = KB_DIR) -> list[tuple[str, str]]:
    """Returns list of (source_filename, full_text)."""
    docs = []
    for path in sorted(kb_dir.glob("*.txt")):
        docs.append((path.name, path.read_text()))
    return docs


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.cfg["rag"]["chunk_size"]
    overlap = overlap or settings.cfg["rag"]["chunk_overlap"]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start <= 0:
            break
    return [c.strip() for c in chunks if c.strip()]


def build_chunks(kb_dir: Path = KB_DIR) -> list[Chunk]:
    all_chunks = []
    for source, text in load_documents(kb_dir):
        for chunk in chunk_text(text):
            all_chunks.append(Chunk(text=chunk, source=source))
    return all_chunks


if __name__ == "__main__":
    chunks = build_chunks()
    print(f"Loaded {len(chunks)} chunks from {KB_DIR}")
    for c in chunks[:2]:
        print(f"--- {c.source} ---\n{c.text[:200]}...\n")
