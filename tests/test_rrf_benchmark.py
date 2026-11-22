from __future__ import annotations

import os
from pathlib import Path

import duckdb
import httpx
import pytest

from interview_ops.benchmark import (
    GOLDEN_QUERIES,
    GOLDEN_SSOT_CORPUS,
    InMemoryHybridEngine,
    evaluate_retrieval_mode,
    persist_benchmark_report,
)
from interview_ops.rag_store import PgHybridStore, embed_text


def test_offline_hybrid_rrf_meets_recall_mrr_and_latency_gates(tmp_path: Path) -> None:
    engine = InMemoryHybridEngine(GOLDEN_SSOT_CORPUS)
    db_file = tmp_path / "rag_telemetry.duckdb"

    dense_report = evaluate_retrieval_mode(
        engine.dense_search,
        GOLDEN_QUERIES,
        mode="dense",
        suite_name="cr011_offline_golden",
    )
    lexical_report = evaluate_retrieval_mode(
        engine.lexical_search,
        GOLDEN_QUERIES,
        mode="lexical",
        suite_name="cr011_offline_golden",
    )
    hybrid_report = evaluate_retrieval_mode(
        engine.hybrid_search,
        GOLDEN_QUERIES,
        mode="hybrid_rrf",
        suite_name="cr011_offline_golden",
    )

    for rep in (dense_report, lexical_report, hybrid_report):
        persist_benchmark_report(db_file, rep)

    assert hybrid_report.recall_at_k >= 0.90
    assert hybrid_report.mrr >= 0.85
    assert hybrid_report.p95_latency_ms < 150.0
    assert hybrid_report.passed_gate is True

    # Hybrid RRF (k=60) must outperform or match standalone dense and lexical modes
    assert hybrid_report.recall_at_k >= dense_report.recall_at_k
    assert hybrid_report.recall_at_k >= lexical_report.recall_at_k
    assert hybrid_report.mrr >= dense_report.mrr
    assert hybrid_report.mrr >= lexical_report.mrr

    conn = duckdb.connect(str(db_file))
    try:
        rows = conn.execute(
            "SELECT mode, passed_gate FROM rag_benchmarks ORDER BY mode"
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 3
    by_mode = {str(mode): bool(passed) for mode, passed in rows}
    assert by_mode["hybrid_rrf"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_pgvector_hybrid_rrf_benchmark(tmp_path: Path) -> None:
    dsn = os.getenv(
        "POSTGRES_DSN", "postgresql://dev:dev@host.docker.internal:15432/interview_ops"
    )
    ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
    telemetry_db = Path(
        os.getenv("AUDIT_DB_PATH", str(tmp_path / "live_rag_telemetry.duckdb"))
    )

    store = PgHybridStore(dsn=dsn)
    store.init_schema()

    query_vecs: dict[str, list[float]] = {}
    async with httpx.AsyncClient() as client:
        for rec in GOLDEN_SSOT_CORPUS:
            doc_text = f"{rec.role} at {rec.company}: {', '.join(rec.skills)}. {rec.summary}"
            vec = await embed_text(client, doc_text, ollama_url=ollama_url)
            store.upsert_record(rec, vec)

        for q in GOLDEN_QUERIES:
            query_vecs[q.query_id] = await embed_text(
                client, q.query_text, ollama_url=ollama_url
            )

    q_by_text = {q.query_text: q.query_id for q in GOLDEN_QUERIES}

    hybrid_report = evaluate_retrieval_mode(
        lambda text, k: store.hybrid_search(text, query_vecs[q_by_text[text]], top_k=k),
        GOLDEN_QUERIES,
        mode="hybrid_rrf",
        suite_name="cr011_live_rhino_pgvector",
    )
    persist_benchmark_report(telemetry_db, hybrid_report)

    assert hybrid_report.recall_at_k >= 0.90
    assert hybrid_report.mrr >= 0.85
    assert hybrid_report.p95_latency_ms < 150.0
    assert hybrid_report.passed_gate is True
