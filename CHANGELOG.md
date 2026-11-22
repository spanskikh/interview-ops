# Changelog

All notable changes and formal Change Requests (CRs) for `interview-ops` are documented in this file.

## [0.3.0-cr006] - 2026-11-22 — CR-006: Offline GitHub Actions CI & CycloneDX SBOM Blueprints
### Objective & Risk Mitigated
- **Closed Residual Risk:** Standardized pre-release verification (`ruff`, `mypy --strict`, `pytest -m "not integration"`) and supply-chain `CycloneDX` SBOM generation across `interview-ops` without triggering premature CI runs while the repository remains private.
- **Traceability:** Branch `feat/cr-006-ci-blueprints` merged via `--no-ff`.

### Added
- `docs/ci/ci.yml`: Staged GitHub Actions workflow (`uv`, `ruff`, `mypy --strict`, `pytest`, `cyclonedx-py` SBOM artifact upload).
- `scripts/publish_to_github.sh`: Deterministic pre-flight and promotion script (`git mv docs/ci/ci.yml .github/workflows/ci.yml` + `gh repo edit --visibility public`).

### Verification Evidence
- `docs/ci/ci.yml` YAML indentation validated and staged cleanly; `.github/workflows/` kept absent until public release.

## [0.2.0] - 2026-11-21 — CR-003: Free-Text Bullet Entity & Year Guard
### Objective & Risk Mitigated
* **Closed Residual Risk:** Closed the "skill sneak-in" hallucination vector where an LLM omits an unverified skill from structured `claimed_skills` but embeds it (or an out-of-range calendar year) inside free-text `bullet_text`.
* **Traceability:** Branch `feat/cr-003-bullet-entity-guard` merged via `--no-ff` (`240fa9a`).

### Added
* `src/interview_ops/verifier.py`: Deterministic boundary-aware lexical skill extractor (`extract_mentioned_skills`) and 4-digit year extractor (`extract_mentioned_years`) wired directly into Z3 SSOT subset and `[start_year, end_year]` constraints.
* `tests/test_bullet_entity_guard.py`: Regression tests blocking unverified skills and out-of-range years inside `bullet_text`.

### Verification Evidence
* `ruff check src tests`: `All checks passed!`
* `mypy src tests` (`--strict`): `0` issues across `8` source files.
* `pytest -v`: `4 passed`.

## [0.1.0] - 2026-11-21 — Grounded Hybrid RAG & Z3 Fact-Checker Baseline
* Initial `pgvector` + `tsvector` Reciprocal Rank Fusion (RRF) retrieval on `rhino`, Z3 SSOT fact-checker on `hippo`, and CEGIS self-correction loop.
