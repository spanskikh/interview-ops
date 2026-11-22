from __future__ import annotations

import json
import os
from typing import Any

import httpx
import psycopg
from pgvector.psycopg import register_vector

from interview_ops.contracts import ExperienceRecord

DEFAULT_DSN = os.getenv(
    "POSTGRES_DSN", "postgresql://dev:dev@host.docker.internal:15432/interview_ops"
)
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")


async def embed_text(
    client: httpx.AsyncClient,
    text: str,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_EMBED_MODEL,
) -> list[float]:
    resp = await client.post(
        f"{ollama_url}/api/embed",
        json={"model": model, "input": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return [float(x) for x in data["embeddings"][0]]


def _row_to_record(row: tuple[Any, ...]) -> tuple[ExperienceRecord, float]:
    skills_raw: Any = row[5]
    skills = json.loads(skills_raw) if isinstance(skills_raw, str) else list(skills_raw)
    rec = ExperienceRecord(
        record_id=str(row[0]),
        company=str(row[1]),
        role=str(row[2]),
        start_year=int(row[3]),
        end_year=int(row[4]),
        skills=skills,
        summary=str(row[6]),
    )
    return rec, float(row[7])


class PgHybridStore:
    """SSOT store in pgvector (rhino) with hybrid RRF search (Vector + BM25/tsvector)."""

    def __init__(self, dsn: str = DEFAULT_DSN) -> None:
        self._dsn = dsn

    def init_schema(self) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            register_vector(conn)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ssot_records (
                    record_id VARCHAR(64) PRIMARY KEY,
                    company VARCHAR(128) NOT NULL,
                    role VARCHAR(128) NOT NULL,
                    start_year INTEGER NOT NULL,
                    end_year INTEGER NOT NULL,
                    skills_json JSONB NOT NULL,
                    summary TEXT NOT NULL,
                    fts tsvector GENERATED ALWAYS AS (
                        to_tsvector('english', coalesce(role, '') || ' ' || coalesce(summary, ''))
                    ) STORED,
                    embedding VECTOR(768) NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ssot_fts ON ssot_records USING GIN (fts);"
            )

    def upsert_record(self, rec: ExperienceRecord, embedding: list[float]) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            register_vector(conn)
            conn.execute(
                """
                INSERT INTO ssot_records (
                    record_id, company, role, start_year, end_year, skills_json, summary, embedding
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (record_id) DO UPDATE SET
                    company = EXCLUDED.company,
                    role = EXCLUDED.role,
                    start_year = EXCLUDED.start_year,
                    end_year = EXCLUDED.end_year,
                    skills_json = EXCLUDED.skills_json,
                    summary = EXCLUDED.summary,
                    embedding = EXCLUDED.embedding;
                """,
                (
                    rec.record_id,
                    rec.company,
                    rec.role,
                    rec.start_year,
                    rec.end_year,
                    json.dumps(rec.skills),
                    rec.summary,
                    embedding,
                ),
            )

    def dense_search(
        self, query_embedding: list[float], top_k: int = 3
    ) -> list[tuple[ExperienceRecord, float]]:
        """Pure dense cosine similarity retrieval over pgvector."""
        sql = """
        SELECT record_id, company, role, start_year, end_year,
               skills_json, summary, 1.0 - (embedding <=> %s::vector) AS cosine_sim
        FROM ssot_records
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """
        with psycopg.connect(self._dsn) as conn:
            register_vector(conn)
            rows = conn.execute(sql, (query_embedding, query_embedding, top_k)).fetchall()
            return [_row_to_record(row) for row in rows]

    def lexical_search(
        self, query_text: str, top_k: int = 3
    ) -> list[tuple[ExperienceRecord, float]]:
        """Pure lexical full-text retrieval using PostgreSQL tsvector/ts_rank_cd."""
        sql = """
        SELECT record_id, company, role, start_year, end_year,
               skills_json, summary,
               ts_rank_cd(fts, plainto_tsquery('english', %s)) AS fts_score
        FROM ssot_records
        WHERE fts @@ plainto_tsquery('english', %s)
        ORDER BY fts_score DESC
        LIMIT %s;
        """
        with psycopg.connect(self._dsn) as conn:
            rows = conn.execute(sql, (query_text, query_text, top_k)).fetchall()
            return [_row_to_record(row) for row in rows]

    def hybrid_search(
        self, query_text: str, query_embedding: list[float], top_k: int = 3
    ) -> list[tuple[ExperienceRecord, float]]:
        """Reciprocal Rank Fusion (RRF, k=60) over cosine distance and ts_rank_cd."""
        sql = """
        WITH vec_ranked AS (
            SELECT record_id,
                   ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector) AS r_vec
            FROM ssot_records
            LIMIT 20
        ),
        fts_ranked AS (
            SELECT record_id,
                   ROW_NUMBER() OVER (
                       ORDER BY ts_rank_cd(fts, plainto_tsquery('english', %s)) DESC
                   ) AS r_fts
            FROM ssot_records
            WHERE fts @@ plainto_tsquery('english', %s)
            LIMIT 20
        ),
        fused AS (
            SELECT COALESCE(v.record_id, f.record_id) AS record_id,
                   COALESCE(1.0 / (60.0 + v.r_vec), 0.0)
                   + COALESCE(1.0 / (60.0 + f.r_fts), 0.0) AS rrf_score
            FROM vec_ranked v
            FULL OUTER JOIN fts_ranked f ON v.record_id = f.record_id
        )
        SELECT s.record_id, s.company, s.role, s.start_year, s.end_year,
               s.skills_json, s.summary, f.rrf_score
        FROM fused f
        JOIN ssot_records s ON s.record_id = f.record_id
        ORDER BY f.rrf_score DESC
        LIMIT %s;
        """
        with psycopg.connect(self._dsn) as conn:
            register_vector(conn)
            rows = conn.execute(sql, (query_embedding, query_text, query_text, top_k)).fetchall()
            return [_row_to_record(row) for row in rows]
