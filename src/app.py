"""
app.py — FastAPI server exposing the RAG infrastructure bot as an API
Usage: uvicorn src.app:app --reload
"""

import os
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from src.retrieve import retrieve_chunks, generate_answer

load_dotenv()

app = FastAPI(
    title="Infrastructure Knowledge Bot",
    description="RAG pipeline using PostgreSQL + pgvector to query infrastructure runbooks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class ChunkResult(BaseModel):
    title: str
    category: str
    content: str
    tags: list[str]
    score: float


class QueryResponse(BaseModel):
    query: str
    answer: str
    chunks: list[ChunkResult]
    total_chunks_searched: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "infra-rag-bot"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM infra_docs;")
            total = cur.fetchone()[0]

        chunks = retrieve_chunks(conn, request.query, k=request.top_k)
        answer = generate_answer(request.query, chunks)

        conn.close()

        return QueryResponse(
            query=request.query,
            answer=answer,
            chunks=[ChunkResult(**c) for c in chunks],
            total_chunks_searched=total
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs-list")
def list_docs():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        with conn.cursor() as cur:
            cur.execute("SELECT id, category, title, tags FROM infra_docs ORDER BY category, title;")
            rows = cur.fetchall()
        conn.close()
        return [{"id": r[0], "category": r[1], "title": r[2], "tags": r[3]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
