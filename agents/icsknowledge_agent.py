"""ICS Knowledge Agent: retrieves relevant standards/threat-intel context via RAG."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agents.schemas import AnomalyEvent, KnowledgeContext
from rag.retriever import Retriever

# Note: this agent does NOT index the IEC 61850 standard text itself, since
# it's a paywalled IEC publication. It indexes public NIST/MITRE ATT&CK for
# ICS summary notes (see rag/knowledge_base/). Add your own licensed IEC
# 61850 notes locally if you have access - just drop .txt files into
# rag/knowledge_base/ and rebuild the index.


class ICSKnowledgeAgent:
    def __init__(self, retriever: Retriever | None = None):
        self.retriever = retriever or Retriever()

    def run(self, event: AnomalyEvent, attack_hint: str | None = None) -> KnowledgeContext:
        query_parts = [attack_hint or "", event.mms_service or "", "ICS smart grid attack"]
        query = " ".join(p for p in query_parts if p).strip()
        references = self.retriever.retrieve(query)
        return KnowledgeContext(references=references)
