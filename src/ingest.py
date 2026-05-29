"""
ingest.py — Load infrastructure docs into PostgreSQL with pgvector embeddings
Usage: python src/ingest.py
"""

import os
import json
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DB_URL = os.getenv("DATABASE_URL")


def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def setup_db(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS infra_docs (
                id        SERIAL PRIMARY KEY,
                category  TEXT NOT NULL,
                title     TEXT NOT NULL,
                content   TEXT NOT NULL,
                tags      TEXT[],
                embedding vector(1536)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS infra_docs_embedding_idx
            ON infra_docs
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10);
        """)
        conn.commit()
    print("Database setup complete.")


def ingest_docs(conn, docs_path: str = "data/runbooks.json"):
    with open(docs_path) as f:
        docs = json.load(f)

    with conn.cursor() as cur:
        cur.execute("DELETE FROM infra_docs;")
        conn.commit()

    inserted = 0
    with conn.cursor() as cur:
        for doc in docs:
            print(f"Embedding: {doc['title']}...")
            embedding = get_embedding(doc["content"])
            cur.execute("""
                INSERT INTO infra_docs (category, title, content, tags, embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                doc["category"],
                doc["title"],
                doc["content"],
                doc.get("tags", []),
                embedding
            ))
            inserted += 1

    conn.commit()
    print(f"Ingested {inserted} documents successfully.")


if __name__ == "__main__":
    conn = psycopg2.connect(DB_URL)
    setup_db(conn)
    ingest_docs(conn)
    conn.close()
    print("Done.")
