from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import FastMCP

from interview_ops.cegis import run_grounded_cv_cegis
from interview_ops.contracts import ExperienceRecord, TailoredAnswerProposal
from interview_ops.rag_store import PgHybridStore, embed_text
from interview_ops.verifier import verify_against_ssot

mcp = FastMCP("interview-ops-rag-qa")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")


@mcp.tool()
async def hybrid_search_ssot(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Гибридный поиск (pgvector cosine + BM25 RRF) по базе опыта на rhino."""
    store = PgHybridStore()
    async with httpx.AsyncClient() as client:
        q_vec = await embed_text(client, query, ollama_url=OLLAMA_URL)
    hits = store.hybrid_search(query, q_vec, top_k=top_k)
    return [{"rrf_score": score, **rec.model_dump()} for rec, score in hits]


@mcp.tool()
async def generate_verified_cv_claims(
    job_description: str,
    top_k: int = 3,
    max_iters: int = 4,
) -> dict[str, Any]:
    """Извлекает релевантный опыт из pgvector и синтезирует резюме с Z3-проверкой фактов."""
    store = PgHybridStore()
    async with httpx.AsyncClient() as client:
        q_vec = await embed_text(client, job_description, ollama_url=OLLAMA_URL)
    hits = store.hybrid_search(job_description, q_vec, top_k=top_k)
    ssot: list[ExperienceRecord] = [rec for rec, _ in hits]
    res = await run_grounded_cv_cegis(job_description, ssot, max_iters=max_iters)
    return {
        "converged": res.converged,
        "iterations": res.iterations,
        "verdict": res.final_verdict.model_dump() if res.final_verdict else None,
        "proposal": res.final_proposal.model_dump() if res.final_proposal else None,
    }


@mcp.tool()
def audit_cv_proposal(
    proposal_json: dict[str, Any],
    ssot_json: list[dict[str, Any]],
) -> dict[str, Any]:
    """Детерминированный Z3-аудит сгенерированных утверждений резюме против SSOT."""
    prop = TailoredAnswerProposal.model_validate(proposal_json)
    ssot = [ExperienceRecord.model_validate(item) for item in ssot_json]
    return verify_against_ssot(prop, ssot).model_dump()


if __name__ == "__main__":
    mcp.run(transport="stdio")
