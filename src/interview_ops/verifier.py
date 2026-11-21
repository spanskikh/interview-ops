from __future__ import annotations

import z3

from interview_ops.contracts import (
    ExperienceRecord,
    FactAuditVerdict,
    TailoredAnswerProposal,
)


def _norm(val: str) -> str:
    return val.strip().lower()


def verify_against_ssot(
    proposal: TailoredAnswerProposal,
    ssot: list[ExperienceRecord],
) -> FactAuditVerdict:
    """Формальная проверка фактов (компании, годы, стек навыков <= SSOT) в Z3."""
    by_id: dict[str, ExperienceRecord] = {r.record_id: r for r in ssot}
    violations: list[str] = []

    for idx, claim in enumerate(proposal.claims):
        rec = by_id.get(claim.source_record_id)
        if rec is None:
            violations.append(
                f"Claim[{idx}]: unknown source_record_id '{claim.source_record_id}' (not in SSOT)"
            )
            continue

        solver = z3.Solver()
        c_start, c_end = z3.Ints("c_start c_end")
        s_start, s_end = z3.Ints("s_start s_end")
        company_match = z3.Bool("company_match")

        solver.add(
            c_start == claim.start_year,
            c_end == claim.end_year,
            s_start == rec.start_year,
            s_end == rec.end_year,
            company_match == z3.BoolVal(_norm(claim.company) == _norm(rec.company)),
        )

        solver.add(
            company_match,
            c_start <= c_end,
            c_start == s_start,
            c_end == s_end,
        )

        allowed_skills = {_norm(s) for s in rec.skills}
        for s_idx, raw_skill in enumerate(claim.claimed_skills):
            v = z3.Bool(f"skill_in_ssot_{s_idx}")
            in_set = _norm(raw_skill) in allowed_skills
            solver.add(v == z3.BoolVal(in_set))
            solver.add(v)

        if solver.check() != z3.sat:
            if _norm(claim.company) != _norm(rec.company):
                violations.append(
                    f"Claim[{idx}] ({rec.record_id}): company mismatch "
                    f"'{claim.company}' != '{rec.company}'"
                )
            if (claim.start_year, claim.end_year) != (rec.start_year, rec.end_year):
                violations.append(
                    f"Claim[{idx}] ({rec.record_id}): year mismatch "
                    f"{claim.start_year}-{claim.end_year} != {rec.start_year}-{rec.end_year}"
                )
            hallucinated = [s for s in claim.claimed_skills if _norm(s) not in allowed_skills]
            if hallucinated:
                violations.append(
                    f"Claim[{idx}] ({rec.record_id}): hallucinated skills {hallucinated} "
                    f"not in SSOT {rec.skills}"
                )

    if violations:
        return FactAuditVerdict(
            status="UNSAT",
            verified_claims=len(proposal.claims),
            violations=violations,
        )

    return FactAuditVerdict(
        status="SAT",
        verified_claims=len(proposal.claims),
    )
