from __future__ import annotations

import re

import z3

from interview_ops.contracts import (
    ExperienceRecord,
    FactAuditVerdict,
    TailoredAnswerProposal,
)

_YEAR_RE = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")


def _norm(val: str) -> str:
    return val.strip().lower()


def extract_mentioned_skills(text: str, vocabulary: set[str]) -> set[str]:
    """Deterministically extract known skill tokens mentioned in free-text bullet."""
    found: set[str] = set()
    lowered = text.lower()
    for skill in vocabulary:
        if not skill:
            continue
        pattern = rf"(?<![a-z0-9_+#.-]){re.escape(skill)}(?![a-z0-9_+#.-])"
        if re.search(pattern, lowered):
            found.add(skill)
    return found


def extract_mentioned_years(text: str) -> list[int]:
    """Extract 4-digit calendar years mentioned in bullet text."""
    return [int(m.group(1)) for m in _YEAR_RE.finditer(text)]


def verify_against_ssot(
    proposal: TailoredAnswerProposal,
    ssot: list[ExperienceRecord],
) -> FactAuditVerdict:
    """Formal Z3 verification of companies, dates, skills, and free-text bullet entities."""
    by_id: dict[str, ExperienceRecord] = {r.record_id: r for r in ssot}
    global_vocab: set[str] = {_norm(s) for r in ssot for s in r.skills} | {
        _norm(s) for s in proposal.missing_required_skills
    }
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
            company_match,
            c_start <= c_end,
            c_start == s_start,
            c_end == s_end,
        )

        allowed_skills = {_norm(s) for s in rec.skills}
        text_skills = extract_mentioned_skills(claim.bullet_text, global_vocab)
        effective_skills = sorted({_norm(s) for s in claim.claimed_skills} | text_skills)

        for s_idx, norm_skill in enumerate(effective_skills):
            v = z3.Bool(f"skill_in_ssot_{s_idx}")
            solver.add(v == z3.BoolVal(norm_skill in allowed_skills), v)

        text_years = extract_mentioned_years(claim.bullet_text)
        for y_idx, yr in enumerate(text_years):
            y_var = z3.Int(f"bullet_year_{y_idx}")
            solver.add(y_var == yr, y_var >= s_start, y_var <= s_end)

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
            hallucinated_struct = [
                s for s in claim.claimed_skills if _norm(s) not in allowed_skills
            ]
            if hallucinated_struct:
                violations.append(
                    f"Claim[{idx}] ({rec.record_id}): hallucinated skills {hallucinated_struct} "
                    f"not in SSOT {rec.skills}"
                )
            sneaked_skills = sorted(s for s in text_skills if s not in allowed_skills)
            if sneaked_skills:
                violations.append(
                    f"Claim[{idx}] ({rec.record_id}): unverified skill(s) {sneaked_skills} "
                    f"sneaked into bullet_text (allowed: {rec.skills})"
                )
            out_of_range_years = [
                y for y in text_years if y < rec.start_year or y > rec.end_year
            ]
            if out_of_range_years:
                violations.append(
                    f"Claim[{idx}] ({rec.record_id}): bullet_text mentions out-of-range "
                    f"year(s) {out_of_range_years} outside {rec.start_year}-{rec.end_year}"
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
