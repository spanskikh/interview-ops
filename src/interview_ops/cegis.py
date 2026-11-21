from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from interview_ops.contracts import (
    ExperienceRecord,
    FactAuditVerdict,
    TailoredAnswerProposal,
)
from interview_ops.rag_store import PgHybridStore, embed_text
from interview_ops.verifier import verify_against_ssot

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5-coder:7b")


@dataclass(frozen=True)
class RagCegisResult:
    converged: bool
    iterations: int
    final_verdict: FactAuditVerdict | None
    final_proposal: TailoredAnswerProposal | None
    history: list[FactAuditVerdict]


async def _generate_tailored_claims(
    client: httpx.AsyncClient,
    ollama_url: str,
    model: str,
    job_description: str,
    retrieved_ssot: list[ExperienceRecord],
    feedback: list[str],
    seed: int = 42,
) -> TailoredAnswerProposal:
    ssot_dump = json.dumps([r.model_dump() for r in retrieved_ssot], ensure_ascii=False, indent=2)
    system_prompt = (
        "You are a strict technical CV compiler. Return ONLY JSON matching TailoredAnswerProposal. "
        "CRITICAL INVARIANTS: Every claim MUST cite an exact source_record_id from the SSOT below, "
        "use the EXACT company name, start_year, end_year, and ONLY claimed_skills that appear "
        "in that record's skills list. Put missing job skills into missing_required_skills."
    )
    user_prompt = (
        f"Job Description:\n{job_description}\n\n"
        f"Verified SSOT Records:\n{ssot_dump}\n"
    )
    if feedback:
        joined = "\n".join(f"- Iteration {i + 1}: {msg}" for i, msg in enumerate(feedback))
        user_prompt += f"\nZ3 Fact-Checker Counterexamples (fix these hallucinations):\n{joined}\n"

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": TailoredAnswerProposal.model_json_schema(),
        "options": {"temperature": 0.0, "seed": seed, "num_ctx": 4096},
    }
    resp = await client.post(f"{ollama_url}/api/chat", json=payload, timeout=120.0)
    resp.raise_for_status()
    return TailoredAnswerProposal.model_validate_json(resp.json()["message"]["content"])


async def run_grounded_cv_cegis(
    job_description: str,
    ssot_records: list[ExperienceRecord],
    max_iters: int = 4,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_CHAT_MODEL,
    transport: httpx.AsyncBaseTransport | None = None,
) -> RagCegisResult:
    feedback: list[str] = []
    history: list[FactAuditVerdict] = []
    last_proposal: TailoredAnswerProposal | None = None

    async with httpx.AsyncClient(transport=transport) as client:
        for step in range(max_iters):
            try:
                proposal = await _generate_tailored_claims(
                    client=client,
                    ollama_url=ollama_url,
                    model=model,
                    job_description=job_description,
                    retrieved_ssot=ssot_records,
                    feedback=feedback,
                    seed=42 + step,
                )
            except (ValidationError, json.JSONDecodeError, KeyError) as exc:
                feedback.append(f"Schema/JSON error: {exc}")
                continue

            last_proposal = proposal
            verdict = verify_against_ssot(proposal, ssot_records)
            history.append(verdict)

            if verdict.status == "SAT":
                return RagCegisResult(
                    converged=True,
                    iterations=step + 1,
                    final_verdict=verdict,
                    final_proposal=proposal,
                    history=history,
                )

            feedback.append("; ".join(verdict.violations))

    return RagCegisResult(
        converged=False,
        iterations=max_iters,
        final_verdict=history[-1] if history else None,
        final_proposal=last_proposal,
        history=history,
    )


async def _smoke_demo() -> None:
    seed_records = [
        ExperienceRecord(
            record_id="exp_deutsche_bank_2025",
            company="Deutsche Bank (Berlin)",
            role="Lead Data & Backend QA Engineer",
            start_year=2023,
            end_year=2025,
            skills=["Python", "DuckDB", "kdb", "FIX", "Protobuf", "Ollama", "Ragas"],
            summary="Tested FIX/protobuf stock feeds, DuckDB pipelines, and RAG QA.",
        ),
        ExperienceRecord(
            record_id="exp_infineon_2024",
            company="Infineon Technologies (Munich)",
            role="Systems & Automation QA Engineer",
            start_year=2023,
            end_year=2024,
            skills=["Python", "Docker", "Selenium Grid", "PyTest", "Linux"],
            summary="Led post-merger test automation and Docker performance harnesses in Munich.",
        ),
        ExperienceRecord(
            record_id="exp_ser_group_2022",
            company="SER Group (Bonn)",
            role="Senior Test Automation Developer",
            start_year=2017,
            end_year=2022,
            skills=["Python", "Java", "JavaScript", "Tomcat", "DSL"],
            summary="Built multi-language test frameworks and synthetic data generators.",
        ),
    ]

    store = PgHybridStore()
    store.init_schema()

    async with httpx.AsyncClient() as client:
        for rec in seed_records:
            doc = f"{rec.role} at {rec.company}: {rec.summary} {rec.skills}"
            vec = await embed_text(client, doc)
            store.upsert_record(rec, vec)

        job = (
            "Senior AI QA & Data Intelligence Engineer in Munich: requires Python, DuckDB, "
            "RAG evaluation (Ragas), Docker, and Kubernetes."
        )
        q_vec = await embed_text(client, job)

    retrieved = store.hybrid_search(job, q_vec, top_k=2)
    print("Hybrid RRF Top-2 from rhino pgvector:")
    for rec, score in retrieved:
        print(f"  - {rec.record_id} ({rec.company}) RRF={score:.4f}")

    res = await run_grounded_cv_cegis(job, [r for r, _ in retrieved], max_iters=3)
    print(f"CEGIS Converged: {res.converged} in {res.iterations} iter(s)")
    if res.final_proposal:
        print("  Verified Claims:", [c.source_record_id for c in res.final_proposal.claims])
        print("  Honest Skill Gaps:", res.final_proposal.missing_required_skills)


if __name__ == "__main__":
    asyncio.run(_smoke_demo())
