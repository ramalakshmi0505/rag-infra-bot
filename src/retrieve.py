"""
retrieve.py — Query infrastructure docs using pgvector similarity search
Usage: python src/retrieve.py "How do I upgrade EKS cluster?"
"""

import os
import sys
import psycopg2
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
DB_URL = os.getenv("DATABASE_URL")


def get_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def retrieve_chunks(conn, query: str, k: int = 5) -> list[dict]:
    """
    Retrieve top-k most similar infrastructure docs using pgvector cosine distance.
    """
    query_embedding = get_embedding(query)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                id,
                category,
                title,
                content,
                tags,
                1 - (embedding <=> %s::vector) AS similarity_score
            FROM infra_docs
            ORDER BY similarity_score DESC
            LIMIT %s;
        """, (query_embedding, k))

        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "category": row[1],
            "title": row[2],
            "content": row[3],
            "tags": row[4],
            "score": round(float(row[5]) * 100, 1)
        }
        for row in rows
    ]


def generate_answer(query: str, chunks: list[dict]) -> str:
    """
    Use Claude to synthesise an answer from retrieved infrastructure docs.
    """
    context = "\n\n".join([
        f"[{i+1}] {c['title']} ({c['category']}, score: {c['score']}%)\n{c['content']}"
        for i, c in enumerate(chunks)
    ])

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"""You are an infrastructure knowledge assistant.
Answer the question using only the provided runbook context.
Be concise, practical, and specific. Include commands where relevant.

CONTEXT:
{context}

QUESTION:
{query}

Answer:"""
            }
        ]
    )

    return response.content[0].text


def ask(query: str) -> dict:
    conn = psycopg2.connect(DB_URL)

    print(f"\nQuery: {query}")
    print("Retrieving relevant docs...")

    chunks = retrieve_chunks(conn, query)

    print(f"Retrieved {len(chunks)} chunks:")
    for c in chunks:
        print(f"  [{c['score']}%] {c['title']}")

    print("\nGenerating answer with Claude...")
    answer = generate_answer(query, chunks)

    conn.close()

    return {
        "query": query,
        "answer": answer,
        "sources": [{"title": c["title"], "score": c["score"]} for c in chunks]
    }


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "How do I upgrade an EKS cluster with zero downtime?"
    result = ask(query)

    print("\n" + "="*60)
    print("ANSWER:")
    print("="*60)
    print(result["answer"])
    print("\nSOURCES:")
    for s in result["sources"]:
        print(f"  {s['score']}% — {s['title']}")
