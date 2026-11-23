# Changelog

All notable changes and formal Change Requests (CRs) for `interview-ops` are documented in this file.

## [0.9.0] - 2026-11-23 — CR-026: Shared `CycloneDX` PEP 610 `file://` Sanitizer CLI Integration
### Objective & Risk Mitigated
- **Closed Residual Risk:** Replaced local inline PEP 610 `file://` SBOM sanitization in `tests/test_sbom_and_contracts.py` with delegation to the shared `sandbox_init.sbom` sanitizer CLI (`CAPA-007`) while retaining an isolated single-repo CI fallback.
- **Traceability:** Change Request `CR-026` (`tests/test_sbom_and_contracts.py`).

### Added & Changed
- `tests/test_sbom_and_contracts.py` (`CR-026` / `CAPA-007`): Invokes `python -m sandbox_init.sbom --input ... --output ... --verify --format summary` from sibling `sandbox-init/src` during two-run `CycloneDX` SBOM reproducibility and host-path hygiene verification.

### Verification Evidence
- `./scripts/run_logged.sh cr026_ruff -- .venv/bin/ruff check src tests`: `All checks passed!` (`0` errors).
- `./scripts/run_logged.sh cr026_mypy -- .venv/bin/mypy src tests --strict`: `Success: no issues found in 15 source files`.
- `./scripts/run_logged.sh cr026_pytest -- .venv/bin/pytest -v -m "not integration"`: `31 passed, 2 deselected`.

## [0.8.0] - 2026-11-23 — CR-022 & CR-023: Cross-Cluster Z3 Contract, SBOM Gate & Rubric Sign-Off
### Objective & Risk Mitigated
- **Closed Residual Risk:** Enforced cross-cluster Z3 RAM budget invariants (`hippo` 24 GiB / `rhino` 16 GiB), 12-tool FastMCP namespace disjointness, deterministic `CycloneDX` SBOM reproducibility, and grammar-constrained live Ollama documentation rubric evaluation (`>= 4/5`).
- **Traceability:** Change Requests `CR-022` and `CR-023` (`BUG-003` / `CAPA-006`) merged via `--no-ff`; release `v0.8.0`.

### Added & Changed
- `pyproject.toml` & `.github/workflows/ci.yml` (`CR-022`): Bump version to `0.8.0`, add `cyclonedx-bom>=7.2.0`, and verify two-run `CycloneDX` SBOM determinism and path hygiene in CI.
- `tests/test_sbom_and_contracts.py` (`CR-022`): Cross-cluster Z3 SAT/UNSAT budget solver, 12-tool FastMCP namespace disjointness check, and `CycloneDX` SBOM reproducibility gate.
- `tests/test_docs_quality.py` (`CR-023` / `BUG-003` / `CAPA-006`): Upgraded `_judge_doc_with_ollama` to JSON Schema grammar-constrained decoding (`DocRubricScore.model_json_schema()`, `temperature=0.0`, `timeout=180.0`).

### Verification Evidence
- `ruff check src tests` & `mypy src tests --strict`: `0` issues across all source and test modules.
- `pytest -m "not integration"`: `31 passed` (including `CR-022` Z3 cluster and `CycloneDX` SBOM gates).
- `pytest -v -m integration`: `2 passed` against live `hippo` Ollama (`qwen2.5-coder:7b`) and `rhino` PostgreSQL.

## [0.7.0] - 2026-11-23 — CR-017..CR-021: Engineering Profiles, SSoT Governance & Auditor Fix
### Objective & Risk Mitigated
- **Closed Residual Risk:** Eliminated cross-repository inconsistency in how theoretical foundations, library versions, workstation environment, SDLC/QA processes, and empirical benchmark metrics are presented to technical reviewers; enforced structural compliance via automated AST/regex quality gates.
- **Traceability:** Change Request `CR-017` implemented across `interview-ops` (`docs/ENGINEERING_PROFILE.md`, `README.md`, `tests/test_docs_quality.py`, `RELEASES.md`).

### Added
- `docs/ENGINEERING_PROFILE.md`: Standardized 5-section engineering dossier (`1. Concepts and Theories`, `2. Frameworks and Libraries`, `3. Dev Tools and Environment`, `4. Processes and Procedures`, `5. Test Approach, Tools, Environment & Metrics`).
- `README.md`: Added direct navigation link to `docs/ENGINEERING_PROFILE.md`.
- `tests/test_docs_quality.py`: Added mandatory file, 5-heading structural assertions, signal density checks, and `2` new seeded defect counterexamples (`missing_engineering_profile`, `missing_profile_section`).

- `DEVPROCESS.md` & `tests/test_docs_quality.py` (`CR-019` / `CAPA-003`): Enforced `<= 1.5 KiB` PTY paste cap and `logs/` summary cap.

- `README.md` & SSoT Migration (`CR-020` / `CAPA-004`): Consolidated shared governance docs (`DEVPROCESS.md`, `RELEASES.md`, `docs/DEFECTS_AND_CAPA.md`, `docs/releases/*`) into `spanskikh/spanskikh` and linked canonical URLs.
- `tests/test_docs_quality.py` (`CR-021` / `BUG-002` / `CAPA-005`): Fixed Markdown auditor to scan all tracked `*.md` files recursively for Cyrillic/placeholders and enforce `CLUSTER_DOC_DUPLICATE`.

### Verification Evidence
- `ruff check .` & `mypy --strict`: `0` issues across all source and test modules.
- `pytest -m "not integration"`: All unit, contract, hygiene, and documentation quality tests green (`+2` new counterexample cases).

## [0.6.0] - 2026-11-22 — CR-014, CR-015 & CR-016: Pre-Public Hygiene Gate, Portfolio Sync & Public CI / CycloneDX Activation
### Objective & Risk Mitigated
- **Closed Residual Risk:** Enforced automated pre-public secret/PII hygiene checks, synchronized `README.md` and `docs/ARCHITECTURE.md` with live hybrid RRF IR metrics (`Recall@3 = 0.9375`, `MRR = 1.0000`, `p95 = 72.217 ms`), and activated GitHub Actions CI + `CycloneDX` SBOM generation.
- **Traceability:** Branches `feat/cr-014-release-hygiene-gate` (`e75e059`), `feat/cr-015-portfolio-landing-sync` (`4d3c433`), and `CR-016` CI promotion merged via `--no-ff`; releases `v0.6.0`.

### Added
- `tests/test_release_hygiene.py`: Pre-public tracked-file secret/PII scanner and CI readiness assertions.
- `docs/ci/ci.yml` -> `.github/workflows/ci.yml` & `scripts/publish_to_github.sh`: Automated CI verification and `CycloneDX` SBOM artifact generation.
- `README.md` & `docs/ARCHITECTURE.md`: Added empirical hybrid RRF retrieval benchmark table.

### Verification Evidence
- `./scripts/run_logged.sh cr015_ruff`: `All checks passed!`
- `./scripts/run_logged.sh cr015_mypy`: `Success: no issues found in 14 source files`
- `./scripts/run_logged.sh cr015_pytest`: `27 passed, 2 deselected`

## [0.6.0] - 2026-11-22 — CR-014, CR-015 & CR-016: Pre-Public Hygiene Gate, Portfolio Sync & Public CI / CycloneDX Activation
### Objective & Risk Mitigated
- **Closed Residual Risk:** Enforced automated pre-public secret/PII hygiene checks, synchronized `README.md` and `docs/ARCHITECTURE.md` with live hybrid RRF IR metrics (`Recall@3 = 0.9375`, `MRR = 1.0000`, `p95 = 72.217 ms`), and activated GitHub Actions CI + `CycloneDX` SBOM generation.
- **Traceability:** Branches `feat/cr-014-release-hygiene-gate` (`e75e059`), `feat/cr-015-portfolio-landing-sync` (`4d3c433`), and `CR-016` CI promotion merged via `--no-ff`; releases `v0.6.0`.

### Added
- `tests/test_release_hygiene.py`: Pre-public tracked-file secret/PII scanner and CI readiness assertions.
- `docs/ci/ci.yml` -> `.github/workflows/ci.yml` & `scripts/publish_to_github.sh`: Automated CI verification and `CycloneDX` SBOM artifact generation.
- `README.md` & `docs/ARCHITECTURE.md`: Added empirical hybrid RRF retrieval benchmark table.

### Verification Evidence
- `./scripts/run_logged.sh cr015_ruff`: `All checks passed!`
- `./scripts/run_logged.sh cr015_mypy`: `Success: no issues found in 14 source files`
- `./scripts/run_logged.sh cr015_pytest`: `27 passed, 2 deselected`

## [0.6.0] - 2026-11-22 — CR-014, CR-015 & CR-016: Pre-Public Hygiene Gate, Portfolio Sync & Public CI / CycloneDX Activation
### Objective & Risk Mitigated
- **Closed Residual Risk:** Enforced automated pre-public secret/PII hygiene checks, synchronized `README.md` and `docs/ARCHITECTURE.md` with live hybrid RRF IR metrics (`Recall@3 = 0.9375`, `MRR = 1.0000`, `p95 = 72.217 ms`), and activated GitHub Actions CI + `CycloneDX` SBOM generation.
- **Traceability:** Branches `feat/cr-014-release-hygiene-gate` (`e75e059`), `feat/cr-015-portfolio-landing-sync` (`4d3c433`), and `CR-016` CI promotion merged via `--no-ff`; releases `v0.6.0`.

### Added
- `tests/test_release_hygiene.py`: Pre-public tracked-file secret/PII scanner and CI readiness assertions.
- `docs/ci/ci.yml` -> `.github/workflows/ci.yml` & `scripts/publish_to_github.sh`: Automated CI verification and `CycloneDX` SBOM artifact generation.
- `README.md` & `docs/ARCHITECTURE.md`: Added empirical hybrid RRF retrieval benchmark table.

### Verification Evidence
- `./scripts/run_logged.sh cr015_ruff`: `All checks passed!`
- `./scripts/run_logged.sh cr015_mypy`: `Success: no issues found in 14 source files`
- `./scripts/run_logged.sh cr015_pytest`: `27 passed, 2 deselected`

## [0.6.0] - 2026-11-22 — CR-014, CR-015 & CR-016: Pre-Public Hygiene Gate, Portfolio Sync & Public CI / CycloneDX Activation
### Objective & Risk Mitigated
- **Closed Residual Risk:** Enforced automated pre-public secret/PII hygiene checks, synchronized `README.md` and `docs/ARCHITECTURE.md` with live hybrid RRF IR metrics (`Recall@3 = 0.9375`, `MRR = 1.0000`, `p95 = 72.217 ms`), and activated GitHub Actions CI + `CycloneDX` SBOM generation.
- **Traceability:** Branches `feat/cr-014-release-hygiene-gate` (`e75e059`), `feat/cr-015-portfolio-landing-sync` (`4d3c433`), and `CR-016` CI promotion merged via `--no-ff`; releases `v0.6.0`.

### Added
- `tests/test_release_hygiene.py`: Pre-public tracked-file secret/PII scanner and CI readiness assertions.
- `docs/ci/ci.yml` -> `.github/workflows/ci.yml` & `scripts/publish_to_github.sh`: Automated CI verification and `CycloneDX` SBOM artifact generation.
- `README.md` & `docs/ARCHITECTURE.md`: Added empirical hybrid RRF retrieval benchmark table.

### Verification Evidence
- `./scripts/run_logged.sh cr015_ruff`: `All checks passed!`
- `./scripts/run_logged.sh cr015_mypy`: `Success: no issues found in 14 source files`
- `./scripts/run_logged.sh cr015_pytest`: `27 passed, 2 deselected`

## [0.5.0] - 2026-11-22 — CR-010, CR-011 & CR-013: FastMCP `stdio` Contract Harness & Hybrid RRF Recall@3 / MRR Benchmark Gate
### Objective & Risk Mitigated
- **Closed Residual Risk:** Quantified hybrid retrieval precision (`pgvector` cosine + `tsvector` BM25 fused via `RRF k=60`) against a curated 16-query Golden Dataset over live `hippo <-> rhino` infrastructure, preventing silent context degradation prior to Z3-grounded CV synthesis.
- **Traceability:** Branches `feat/cr-010-mcp-stdio-contracts` and `feat/cr-011-hybrid-rrf-benchmark` (`4cc9675`) merged via `--no-ff`; releases `v0.5.0`.

### Added
- `tests/test_mcp_contracts.py`: Real `mcp.client.stdio` discovery, JSON schema checks, `SAT`/`UNSAT` Z3 CV claim auditing, and Pydantic validation error rejection across `hybrid_search_ssot`, `generate_verified_cv_claims`, and `audit_cv_proposal`.
- `src/interview_ops/rag_store.py`, `src/interview_ops/benchmark.py` & `tests/test_rrf_benchmark.py`: Added `dense_search()` and `lexical_search()` baselines alongside `hybrid_search()`, 12-record SSOT Golden Corpus, 16 curated Golden Queries, `Recall@3`/`MRR`/`p95` evaluator, and `DuckDB` `rag_benchmarks` persistence.
- `DEVPROCESS.md` & `docs/DEFECTS_AND_CAPA.md` (`CAPA-002`): Codified normative SDLC and English-only Git governance.

### Verification Evidence
- `./scripts/run_logged.sh cr011_ruff` (`logs/20261122-155239_cr011_ruff.log`): `All checks passed!`
- `./scripts/run_logged.sh cr011_mypy` (`logs/20261122-155239_cr011_mypy.log`): `Success: no issues found in 13 source files`
- `./scripts/run_logged.sh cr011_pytest` (`logs/20261122-155240_cr011_pytest.log`): `19 passed, 2 deselected`
- `./scripts/run_logged.sh cr011_live_rrf` (`logs/20261122-155817_cr011_live_rrf.log`): `1 passed` against live `rhino` `PostgreSQL + pgvector` + `Ollama` (`nomic-embed-text`) — `Recall@3 = 0.9375` (`>= 0.90`), `MRR = 1.0000` (`>= 0.85`), `p95 = 72.217 ms` (`< 150 ms`).

## [0.4.0] - 2026-11-22 — CR-009: Dev-Process Auditability, Execution Logging & Release Retrospectives
### Objective & Risk Mitigated
- **Closed Residual Risk:** Eliminated loss of iterative engineering history, unlogged local execution runs, and missing post-release retrospectives across `interview-ops` by introducing deterministic `.stdout`/`.stderr`/`.log` capture, versioned `docs/dev-log/` artifacts, and mandatory release retrospectives enforced by automated mutation tests.
- **Traceability:** Branch `feat/cr-009-dev-process-auditability` merged via `--no-ff`; releases `v0.4.0`.

### Added
- `scripts/run_logged.sh` & `tests/test_run_logged.py`: POSIX execution wrapper capturing ISO-8601 start/end timestamps, duration, exit codes, and split `.stdout`, `.stderr`, and `.log` artifacts in gitignored `logs/`.
- `docs/dev-log/`: Versioned raw patch/script artifact history (`20261122-130500_cr-009_install-run-logged.sh`, `20261122-130800_cr-009_enforce-release-retrospectives.py`).
- `docs/releases/v0.3.0-retrospective.md` & `tests/test_docs_quality.py`: Post-release retrospective capturing Lessons Learned, Rejected Ideas, Unlucky Probe-Runs, and Release Chat Digest, enforced by an 8th seeded mutation counterexample (`missing_retrospective_section`).

### Verification Evidence
- `./scripts/run_logged.sh cr009_final_gate`: `ruff check src tests` (`All checks passed!`), `mypy src tests --strict` (`Success: no issues found`), `pytest -v -m "not integration"` (`14 passed, 1 deselected`).

## [0.3.0] - 2026-11-22 — CR-008: Documentation Quality Gates, Mutation Counterexamples & Live Rubric Evaluation
### Objective & Risk Mitigated
- **Closed Residual Risk:** Eliminated documentation drift, broken relative links, unclosed Mermaid diagrams, unresolved placeholders, and hollow marketing claims across `interview-ops` through deterministic structural/style/market-value checks, 7 seeded negative mutation counterexamples, and live `Ollama` rubric grading.
- **Traceability:** Branch `feat/cr-008-docs-quality-tests` merged via `--no-ff`; releases `v0.3.0`.

### Added
- `docs/ARCHITECTURE.md`: Added Level-2 domain architecture with Mermaid topology, ADRs, and trade-off/risk control matrix.
- `tests/test_docs_quality.py`: `DocQualityAuditor` (`Pydantic v2`), 7 parametrized negative mutation counterexamples (`MISSING_REQUIRED_FILE`, `LANGUAGE_DRIFT_CYRILLIC`, `MISSING_REQUIRED_SECTION`, `PLACEHOLDER_LEAK`, `BROKEN_MERMAID_BLOCK`, `BROKEN_RELATIVE_LINK`, `LOW_MARKET_SIGNAL_OR_HYPE`), and `@pytest.mark.integration` live `Ollama` rubric test (`num_ctx=2048`, `num_predict=160`, `timeout=180.0` tuned for CPU inference on `hippo`).
- `pyproject.toml`: Standardized version `0.3.0`, `[project.optional-dependencies] dev`, `pythonpath = ["src"]`, and `@pytest.mark.integration` marker.

### Verification Evidence
- `ruff check src tests`: `All checks passed!`
- `mypy src tests --strict`: `Success: no issues found`
- `pytest -v -m "not integration"`: `12 passed, 1 deselected` (including all 7 seeded mutation counterexamples)
- `pytest -v -m "integration"`: `1 passed, 12 deselected` (live `Ollama` rubric >= 4/5 on real docs and <= 2/5 on weak counterexample)

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
