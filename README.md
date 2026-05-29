# Infrastructure Knowledge Bot RAG with PostgreSQL + pgvector

A RAG (Retrieval-Augmented Generation) pipeline that lets you query infrastructure runbooks, architecture docs, and operational knowledge using natural language.

Built by a platform engineer, for platform engineers.

---

## What it does

Instead of searching through folders of runbooks or scrolling through Confluence, ask natural language questions and get answers grounded in your actual infrastructure docs.

**Example queries:**
- *"How do I upgrade an EKS cluster with zero downtime?"*
- *"What is the Karpenter node provisioner configuration?"*
- *"How do we handle a P1 production incident?"*
- *"What are the Trivy scan commands for CI/CD?"*

---

## How it works

```
Infrastructure Docs (JSON)
        ↓
  text-embedding-3-small
        ↓
 PostgreSQL + pgvector          ← Vector similarity search
        ↓
  Top-5 relevant chunks
        ↓
    Claude claude-sonnet-4-20250514            ← Synthesises the answer
        ↓
  Grounded answer with sources
```

The key SQL query:

```sql
SELECT
    id,
    category,
    title,
    content,
    1 - (embedding <=> $1::vector) AS similarity_score
FROM infra_docs
ORDER BY similarity_score DESC
LIMIT 5;
```

`<=>` is the pgvector cosine distance operator. Lower distance = higher similarity.

---

## Tech stack

| Component | Technology |
|---|---|
| Vector store | PostgreSQL 16 + pgvector |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | Anthropic Claude Sonnet |
| API | FastAPI |
| Infrastructure | Docker + docker-compose |

---

## Quick start

**1. Clone the repo**
```bash
git clone https://github.com/ramalakshmi0505/rag-infra-bot
cd rag-infra-bot
```

**2. Copy env file and add your keys**
```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and ANTHROPIC_API_KEY
```

**3. Start PostgreSQL with pgvector**
```bash
docker-compose up postgres -d
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Ingest runbooks into PostgreSQL**
```bash
python src/ingest.py
```

**6. Ask a question from CLI**
```bash
python src/retrieve.py "How do I upgrade EKS with zero downtime?"
```

**7. Start the API server**
```bash
uvicorn src.app:app --reload
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/query` | Ask a question, get a grounded answer |
| GET | `/docs-list` | List all indexed runbook documents |
| GET | `/health` | Health check |

**Example request:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I configure Vault secrets on EKS?", "top_k": 5}'
```

**Example response:**
```json
{
  "query": "How do I configure Vault secrets on EKS?",
  "answer": "To configure Vault secrets on EKS...",
  "chunks": [
    {
      "title": "HashiCorp Vault Secrets Management on EKS",
      "category": "Security",
      "score": 91.3
    }
  ],
  "total_chunks_searched": 14
}
```

---

## Adding your own runbooks

Edit `data/runbooks.json` and add your docs in this format:

```json
{
  "category": "EKS",
  "title": "Your runbook title",
  "tags": ["tag1", "tag2"],
  "content": "Full runbook content here..."
}
```

Then re-run ingestion:
```bash
python src/ingest.py
```

---

## Why PostgreSQL over a dedicated vector DB?

Most teams already run PostgreSQL. Adding pgvector means no new infrastructure just an extension. For production platform teams with existing Postgres, this is the simplest path to production-grade vector search.

---

## Roadmap

- [ ] Slack bot integration — ask questions directly from Slack
- [ ] Auto-ingest from Confluence via API
- [ ] Terraform module to deploy on EKS
- [ ] Conversation memory for multi-turn queries

---

Built with Python, PostgreSQL, pgvector, OpenAI, and Anthropic Claude.
