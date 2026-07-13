# GridGuard AI

**A multi-agent smart-grid security copilot: ML anomaly detection + LLM agent investigation for IEC 61850/MMS industrial control systems.**

This project is an engineering extension of my Master's Thesis at
Friedrich-Alexander-Universität Erlangen-Nürnberg, *"AI-based anomaly detection in
smart grids with ICS protocols integration."* The thesis built a machine-learning
anomaly detector for MMS traffic in a simulated smart-grid testbed. This repo takes
that detector and wraps it with a multi-agent LLM layer that investigates each flagged
anomaly, retrieves relevant ICS security context, assesses risk, and recommends a
response, turning a raw anomaly score into an incident report a SOC analyst can act on.

> **Status:** working end-to-end prototype. Detection, feature engineering, the
> multi-agent pipeline, RAG knowledge retrieval, the API, and the test suite are all
> implemented and passing. See [What's implemented vs. conceptual](#whats-implemented-vs-conceptual)
> below for an honest breakdown, some pieces from the original design (real ICS
> captures, Power Automate/Teams delivery, cloud deployment) need infrastructure this
> repo can describe but not fully exercise on its own.

## Architecture

```
                 ┌─────────────────────┐
 MMS Traffic ──▶ │ Feature Engineering  │
 (real or        └──────────┬───────────┘
  synthetic)                ▼
                 ┌─────────────────────┐
                 │ Anomaly Detection    │   Isolation Forest + Local Outlier
                 │ (ensemble)           │   Factor, ensemble union/threshold
                 └──────────┬───────────┘
                             ▼ (flagged event)
                 ┌─────────────────────────────────────────────┐
                 │           Agent Orchestrator (LangGraph)      │
                 │                                               │
                 │  Detection ─▶ ICS Knowledge (RAG) ─▶          │
                 │  Root Cause ─▶ Risk Assessment ─▶ Response     │
                 └──────────────────────┬────────────────────────┘
                                         ▼
                              Incident Report (JSON)
                                         ▼
                      Power Automate webhook ─▶ Teams / Email
```

## What's implemented vs. conceptual

| Component | Status | Notes |
|---|---|---|
| Feature engineering (temporal + network features) | ✅ Implemented | `detection/feature_engineering.py` |
| Isolation Forest + LOF ensemble detector | ✅ Implemented, tested | `detection/` |
| Synthetic MMS traffic generator (DoS/MITM/FDI/Replay) | ✅ Implemented | `data/generate_synthetic_data.py` — Python replacement for the MATLAB/Simulink path, see below |
| Multi-agent pipeline (5 agents + orchestrator) | ✅ Implemented, tested | `agents/`, built on LangGraph |
| Provider-agnostic LLM client (Anthropic / OpenAI / mock) | ✅ Implemented | `agents/llm_client.py` — mock provider needs no API key |
| RAG knowledge retrieval (NIST + MITRE ATT&CK for ICS) | ✅ Implemented | TF-IDF + FAISS, see caveat below |
| FastAPI service (`/detect`, `/incidents/investigate`) | ✅ Implemented, tested | `api/` |
| Power Automate → Teams/email webhook | ✅ Code implemented, **not live-tested** | Needs your own Power Automate tenant + flow URL |
| Docker / docker-compose | ✅ Written, **not build-tested in this environment** (no Docker daemon available here) | Standard slim-Python image; should build cleanly locally |
| CI (GitHub Actions) | ✅ Implemented | Runs pytest + Docker build on push/PR |
| MATLAB/Simulink data generation | 📝 From original thesis, not reproduced here | See caveat below |
| Azure cloud deployment | 📝 Not implemented | Described as a next step, not present in this repo |
| Digital twin, autonomous remediation, Sentinel integration | 📝 Future work | Intentionally out of scope for this prototype |

### Caveats worth knowing about

- **MATLAB/Simulink → Python synthetic data.** The thesis used a Simulink-modeled
  substation testbed to generate labeled training data. That requires a MATLAB
  license and a validated grid model, which isn't practical to bundle in an
  open-source repo. `data/generate_synthetic_data.py` is a from-scratch Python
  generator that produces statistically distinct feature distributions for normal
  traffic and four attack classes (DoS, MITM, FDI, Replay), so the rest of the
  pipeline is runnable and testable by anyone who clones this repo. It is **not**
  a validated substitute for real grid simulation data — treat it as a development
  and demo aid, and swap in real captures via `load_real_traffic()` in the same
  file when you have them.
- **RAG knowledge base.** The ICS Knowledge Agent retrieves from public NIST
  SP 800-82 and MITRE ATT&CK for ICS *summary notes* (original text, written for
  this repo — not reproductions of the source documents). The actual IEC 61850
  standard is a paywalled IEC publication and isn't indexed here for that reason.
  If you have licensed access, drop your own `.txt` notes into
  `rag/knowledge_base/` and rebuild the index (`python -m rag.vectorstore`).
- **Retrieval uses TF-IDF, not a hosted embedding model.** This was a deliberate
  choice so the whole pipeline — including RAG — runs with zero API keys and zero
  external calls. Swap `rag/vectorstore.py` for a real embedding model if you want
  higher-quality retrieval once you're running with a live LLM provider.
- **Mock LLM provider.** By default (`LLM_PROVIDER=mock`), agents use a
  deterministic rule-based stand-in instead of a real LLM call, so the whole
  system — including CI — runs and is tested without any API key. It does small
  keyword/threshold heuristics on the input features (e.g. high `request_rate` →
  DoS) to produce a coherent demo report; it is not doing real reasoning. Set
  `LLM_PROVIDER=anthropic` or `openai` with a real key in `.env` for actual LLM-driven
  investigation.
- **Power Automate delivery** can't be exercised without your own Microsoft 365
  tenant and a configured flow. The webhook code is real and will POST the incident
  report JSON to whatever URL you configure; wiring the Teams/email fan-out on the
  Power Automate side is on you.

## Repo structure

```
GridGuard-AI/
├── agents/              # Detection, Root Cause, ICS Knowledge, Risk, Response agents + orchestrator
├── api/                 # FastAPI app and routes
├── automation/           # Power Automate webhook integration
├── config/               # config.yaml + settings loader
├── data/                 # synthetic MMS traffic generator
├── detection/             # feature engineering + Isolation Forest / LOF ensemble
├── rag/                   # knowledge base ingestion, TF-IDF/FAISS vector store, retriever
├── scripts/               # end-to-end demo script
├── tests/                 # pytest suite (14 tests, all passing)
├── Dockerfile / docker-compose.yml
└── .github/workflows/ci.yml
```

## Getting started

```bash
git clone https://github.com/Kanwardeep-Singh/GridGuard-AI.git
cd GridGuard-AI
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # defaults to LLM_PROVIDER=mock, no key needed
```

Run the end-to-end demo (synthetic data → detection → agent investigation):
```bash
python scripts/run_pipeline.py
```

Run the test suite:
```bash
pytest tests/ -v
```

Run the API:
```bash
uvicorn api.app:app --reload --port 8000
# interactive docs at http://localhost:8000/docs
```

Or with Docker:
```bash
docker compose up --build
```

To use a real LLM instead of the mock provider, set in `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## Sample incident report

Illustrative output from `scripts/run_pipeline.py` against synthetic traffic
(mock LLM provider) — not a benchmarked production result:

```json
{
  "attack_type": "Denial of Service",
  "protocol": "MMS",
  "target": "NAN-Gateway",
  "severity": "High",
  "confidence": 0.8,
  "impact": "Communication disruption / potential loss of protective function",
  "recommended_actions": [
    "Isolate affected asset from the control network segment",
    "Enable enhanced monitoring on related IEDs",
    "Notify on-call ICS security engineer"
  ],
  "root_cause": "Traffic pattern consistent with a Denial of Service attempt: elevated request rate with reduced packet size.",
  "knowledge_references": ["..."]
}
```

## Thesis lineage

This repo extends the anomaly-detection core of my thesis work:

- Feature engineering on MMS protocol communication data for temporal and
  network-level anomaly signals.
- ML-based detection of DoS, MITM, False Data Injection, and Replay attacks.
- Evaluation via precision/recall/F1/detection-latency style metrics (see `tests/`
  for the sanity-bound checks used here; full benchmark numbers belong to the
  thesis document itself, not this repo).

What's new in this extension is the agent layer on top: instead of stopping at an
anomaly score, GridGuard AI investigates *why* something was flagged, pulls in
ICS security context, scores risk, and proposes a response — closer to what a
SOC analyst workflow actually needs.

## License

MIT — see `LICENSE`.
