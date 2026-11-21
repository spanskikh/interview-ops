from __future__ import annotations

import json

import httpx

from interview_ops.cegis import run_grounded_cv_cegis
from interview_ops.contracts import ExperienceRecord, ResumeClaim, TailoredAnswerProposal
from interview_ops.verifier import verify_against_ssot

SSOT_SAMPLE = [
    ExperienceRecord(
        record_id="exp_db",
        company="Deutsche Bank",
        role="Lead Data QA",
        start_year=2023,
        end_year=2025,
        skills=["Python", "DuckDB", "Ragas"],
        summary="Financial data QA.",
    )
]


def test_z3_blocks_hallucinated_skill_and_year_drift() -> None:
    bad = TailoredAnswerProposal(
        target_role="AI QA",
        claims=[
            ResumeClaim(
                source_record_id="exp_db",
                company="Deutsche Bank",
                start_year=2022,
                end_year=2025,
                claimed_skills=["Python", "Kubernetes"],
                bullet_text="Built pipelines.",
            )
        ],
    )
    verdict = verify_against_ssot(bad, SSOT_SAMPLE)
    assert verdict.status == "UNSAT"
    assert any("year mismatch" in v for v in verdict.violations)
    assert any("Kubernetes" in v for v in verdict.violations)


async def test_cegis_strips_hallucinated_skill_after_z3_feedback() -> None:
    step = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal step
        step += 1
        if step == 1:
            bad = {
                "target_role": "AI QA",
                "claims": [
                    {
                        "source_record_id": "exp_db",
                        "company": "Deutsche Bank",
                        "start_year": 2023,
                        "end_year": 2025,
                        "claimed_skills": ["Python", "Kubernetes"],
                        "bullet_text": "Tested RAG.",
                    }
                ],
                "missing_required_skills": [],
            }
            return httpx.Response(200, json={"message": {"content": json.dumps(bad)}})

        body = json.loads(request.content.decode())
        assert "Kubernetes" in body["messages"][-1]["content"]
        fixed = {
            "target_role": "AI QA",
            "claims": [
                {
                    "source_record_id": "exp_db",
                    "company": "Deutsche Bank",
                    "start_year": 2023,
                    "end_year": 2025,
                    "claimed_skills": ["Python", "Ragas"],
                    "bullet_text": "Tested RAG with Python and Ragas.",
                }
            ],
            "missing_required_skills": ["Kubernetes"],
        }
        return httpx.Response(200, json={"message": {"content": json.dumps(fixed)}})

    res = await run_grounded_cv_cegis(
        job_description="Need Python, Ragas, Kubernetes",
        ssot_records=SSOT_SAMPLE,
        max_iters=3,
        transport=httpx.MockTransport(handler),
    )
    assert res.converged is True
    assert res.iterations == 2
    assert res.final_proposal is not None
    assert res.final_proposal.missing_required_skills == ["Kubernetes"]
