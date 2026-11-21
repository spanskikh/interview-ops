from __future__ import annotations

from interview_ops.contracts import ExperienceRecord, ResumeClaim, TailoredAnswerProposal
from interview_ops.verifier import verify_against_ssot


def _sample_ssot() -> list[ExperienceRecord]:
    return [
        ExperienceRecord(
            record_id="exp_db_2025",
            company="Deutsche Bank",
            role="Lead Data QA Engineer",
            start_year=2024,
            end_year=2025,
            skills=["Python", "DuckDB", "PyTest"],
            summary="Built deterministic FIX and DuckDB QA pipelines.",
        ),
        ExperienceRecord(
            record_id="exp_inf_2024",
            company="Infineon",
            role="Systems QA Engineer",
            start_year=2023,
            end_year=2024,
            skills=["Docker", "Selenium"],
            summary="Led post-merger test automation.",
        ),
    ]


def test_blocks_skill_sneaked_into_bullet_text() -> None:
    proposal = TailoredAnswerProposal(
        target_role="AI QA Architect",
        claims=[
            ResumeClaim(
                source_record_id="exp_db_2025",
                company="Deutsche Bank",
                start_year=2024,
                end_year=2025,
                claimed_skills=["Python", "DuckDB"],
                bullet_text="Automated DuckDB and Selenium pipelines in 2025.",
            )
        ],
        missing_required_skills=["Kubernetes"],
    )
    verdict = verify_against_ssot(proposal, _sample_ssot())
    assert verdict.status == "UNSAT"
    assert any("sneaked into bullet_text" in v and "selenium" in v for v in verdict.violations)


def test_blocks_out_of_range_year_in_bullet_text() -> None:
    proposal = TailoredAnswerProposal(
        target_role="AI QA Architect",
        claims=[
            ResumeClaim(
                source_record_id="exp_db_2025",
                company="Deutsche Bank",
                start_year=2024,
                end_year=2025,
                claimed_skills=["Python"],
                bullet_text="Migrated legacy Python pipelines originally built in 2021.",
            )
        ],
    )
    verdict = verify_against_ssot(proposal, _sample_ssot())
    assert verdict.status == "UNSAT"
    assert any("out-of-range year(s) [2021]" in v for v in verdict.violations)
