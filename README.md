 # CapitalMind — AI Investment Research Platform

Production-grade, multi-agent investment intelligence system built on LangGraph,
Ollama (local LLMs), and PostgreSQL. Processes SEC filings, earnings transcripts, and
real-time market data to generate institutional-quality research memos with
full audit trails and human-in-the-loop review gates.

> **Runs 100% locally** — no API keys required. Uses Ollama with llama3.1, llava, and nomic-embed-text.

---

## Architecture

```
User Request
    │
    ▼
FastAPI (api/main.py)
    │  WebSocket (real-time streaming)
    ▼
LangGraph StateGraph (src/graph/investment_graph.py)
    │
    ├── ingest_documents      SEC EDGAR API + yfinance snapshot
    │
    ├── extract_multimodal    PDFs → chunks + tables (Camelot) + charts (GPT-4o vision)
    │
    ├── plan_research         Pinecone retrieval + strategy
    │
    ├── [PARALLEL FAN-OUT via Send API]
    │       ├── financial_analysis    Ollama → metrics, ratios, EPS
    │       ├── sentiment_analysis    Ollama → tone, guidance, hedging signals
    │       ├── risk_assessment       Ollama → categorized risk flags
    │       └── peer_comparison       Ollama → sector benchmarking
    │
    ├── synthesize            Ollama → investment memo with citations
    │
    ├── fact_check            Ollama → verify every claim vs source docs
    │
    ├── hitl_router           LangGraph interrupt() if confidence < 0.80
    │       │
    │       └── [POST /api/research/{id}/review] resumes graph
    │
    └── generate_report       Final memo → S3 + PostgreSQL audit
```

### Infrastructure (AWS)
```
AWS ECS (Fargate)          ← Application containers
AWS RDS (PostgreSQL)       ← LangGraph checkpointer + audit trail
AWS ElastiCache (Redis)    ← Session cache + WebSocket pub/sub
AWS MSK (Kafka)            ← Real-time market data ingestion
AWS S3                     ← Raw documents + final reports
Pinecone (Serverless)      ← Vector embeddings (3072-dim)
```

---

## Key Features

| Feature | Implementation |
|---|---|
| Multi-agent orchestration | LangGraph StateGraph with parallel Send API |
| Multi-modal extraction | Camelot (tables) + GPT-4o vision (charts) |
| Real-time data | yfinance + Kafka MSK stream consumer |
| Human-in-the-loop | LangGraph `interrupt()` + POST `/review` resume |
| Audit trail | Immutable PostgreSQL event log, every agent action |
| Fault tolerance | PostgreSQL checkpointer — resume after any crash |
| Observability | LangSmith tracing + OpenTelemetry + Sentry |
| Fact-checking | Claim extraction + cross-reference against sources |
| Vector search | Pinecone Serverless, 3072-dim, namespace per ticker |
| Hybrid retrieval | Dense (Pinecone) — sparse (BM25) fusion planned |

---

## Quick Start (Local)

### 1. Prerequisites
- Python 3.12+
- Docker + Docker Compose
- Node.js 20+
- [Ollama](https://ollama.ai) installed and running

### 1b. Pull Ollama Models
```bash
ollama pull llama3.1:8b          # Primary reasoning LLM
ollama pull llava:13b            # Vision / chart interpretation
ollama pull nomic-embed-text     # Local embeddings (768-dim)
```

### 2. Infrastructure
```bash
cd infrastructure
docker-compose up -d postgres redis kafka zookeeper
```

### 3. Python Setup
```bash
python -m venv venv
source venv/bin/activate          # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env              # Fill in your API keys
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

### 5. API Server
```bash
uvicorn api.main:app --reload --port 8000
```

### 6. Full Production Build
```bash
docker build -t capitalmind:latest .
docker-compose -f infrastructure/docker-compose.yml up
```

---

## API Reference

### Start Research Run
```http
POST /api/research
Content-Type: application/json

{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "research_type": "earnings_analysis",
  "requested_by": "analyst@firm.com"
}
```

**Research types:** `earnings_analysis` | `full_deep_dive` | `risk_assessment` | `peer_comparison` | `quick_summary`

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "ticker": "AAPL",
  "message": "Research started. Connect to /ws/550e8400-... for live updates."
}
```

### WebSocket (Real-time Updates)
```js
const ws = new WebSocket(`ws://localhost:8000/ws/${run_id}`);
ws.onmessage = ({ data }) => {
  const event = JSON.parse(data);
  // event.type: "agent_start" | "agent_complete" | "hitl_required" | "complete" | "error"
};
```

### Get Result
```http
GET /api/research/{run_id}
```

### Submit HITL Review
```http
POST /api/research/{run_id}/review
Content-Type: application/json

{
  "decision": "approved",
  "reviewer_id": "analyst@firm.com",
  "notes": "Revenue figures verified against Bloomberg. Approved.",
  "revised_sections": null
}
```

**Decisions:** `approved` | `rejected` | `revised`

### Get Audit Trail
```http
GET /api/audit/{run_id}
```

---

## LangGraph HITL Mechanism

The HITL gate uses LangGraph's native `interrupt()` primitive:

1. `hitl_router_node` calls `interrupt(payload)` → graph **serializes state** to PostgreSQL and pauses
2. Frontend receives `hitl_required` WebSocket event with the review packet
3. Reviewer submits decision to `POST /api/research/{id}/review`
4. API calls `graph.ainvoke(Command(resume=decision), config)` → graph **resumes from checkpoint**
5. Final report is generated with reviewer's annotations in the audit trail

This means HITL works across HTTP requests, server restarts, and even different server instances — because state is fully persisted in PostgreSQL.

---

## Configuration

All configuration in `src/utils/settings.py` via environment variables or `.env`.

Key thresholds:
- `HITL_CONFIDENCE_THRESHOLD=0.80` — Below this score triggers human review
- `QUALITY_THRESHOLD=0.75` — Minimum synthesis quality before fact-check
- `AGENT_MAX_ITERATIONS=5` — Maximum retries per agent step
- `RETRIEVAL_TOP_K=8` — Pinecone results per query

---

## Running Tests

```bash
pytest tests/ -v --asyncio-mode=auto
```

Test coverage includes:
- Agent JSON parsing (financial, sentiment, risk, fact-checker)
- Chunking strategy edge cases
- Audit event structure and UUID validation
- API schema validation (Pydantic)
- Graph state enum values
- Settings defaults

---

## Production Deployment (AWS ECS)

See `infrastructure/` for:
- `docker-compose.yml` — Full local stack
- `Dockerfile` — Multi-stage production build
- `nginx.conf` — Reverse proxy config

For AWS production:
1. Push image to ECR: `aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL`
2. Create ECS Task Definition with the ECR image
3. Set secrets via AWS Secrets Manager (reference in task definition)
4. RDS PostgreSQL with `pgvector` extension enabled
5. ElastiCache Redis cluster (cluster mode disabled for pub/sub)
6. MSK Kafka cluster for market data streaming
7. S3 bucket with server-side encryption for reports
8. CloudFront distribution for frontend CDN

---

## Project Structure

```
capitalmind/
├── src/
│   ├── graph/
│   │   ├── investment_graph.py   ← LangGraph StateGraph (main orchestration)
│   │   └── state.py              ← Shared TypedDict state schema
│   ├── agents/
│   │   ├── financial_analyst.py  ← Metrics + ratio extraction
│   │   ├── sentiment_analyst.py  ← Tone + guidance analysis
│   │   ├── risk_assessor.py      ← Risk flag identification
│   │   ├── fact_checker.py       ← Claim verification + PeerComparatorAgent
│   │   ├── multimodal_analyst.py ← PDF tables + vision chart interpretation
│   │   └── synthesizer.py        ← Investment memo generation
│   ├── ingestion/
│   │   ├── sec_edgar.py          ← SEC EDGAR async client
│   │   └── market_data.py        ← yfinance + Kafka consumer
│   ├── retrieval/
│   │   └── pinecone_store.py     ← Vector upsert + similarity search
│   ├── audit/
│   │   └── trail.py              ← PostgreSQL audit persistence
│   └── utils/
│       ├── settings.py           ← Pydantic settings (env-driven)
│       └── s3.py                 ← S3 upload utility
├── api/
│   └── main.py                   ← FastAPI app + WebSocket + HITL routes
├── frontend/
│   └── src/App.jsx               ← Bloomberg Terminal-style React dashboard
├── tests/
│   └── test_capitalmind.py       ← Full test suite
├── infrastructure/
│   └── docker-compose.yml        ← Local dev stack (pg, redis, kafka)
├── Dockerfile                    ← Multi-stage production build
├── requirements.txt              ← Python dependencies
└── .env.example                  ← Environment template
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | LangGraph 0.2.28 |
| Primary LLM | Ollama — llama3.1:8b (local) |
| Vision LLM | Ollama — llava:13b (local) |
| Embeddings | Ollama — nomic-embed-text (768-dim, local) |
| Vector store | Pinecone Serverless |
| Framework | FastAPI + Uvicorn + Gunicorn |
| Database | PostgreSQL 16 (async via asyncpg) |
| Checkpointing | LangGraph AsyncPostgresSaver |
| Cache | Redis 7 |
| Streaming | Apache Kafka (AWS MSK) |
| Real-time UI | WebSocket (native FastAPI) |
| Market data | yfinance + Alpha Vantage |
| SEC filings | EDGAR REST API |
| PDF tables | Camelot + pdfplumber |
| Observability | LangSmith + OpenTelemetry + Sentry |
| Containerization | Docker multi-stage + ECS Fargate |
| Frontend | React 18 + Vite |

---

## License

MIT
