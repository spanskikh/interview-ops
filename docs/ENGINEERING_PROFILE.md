# Engineering Profile — `interview-ops`

> **Architectural Role:** Grounded Hybrid RAG & `Z3` Factuality Guard (`C1` Maturity Tier)

## 1. Concepts and Theories
- **Hybrid Lexical & Semantic Information Retrieval:** Combines sparse exact-term scoring (`BM25` / lexical overlap) with dense semantic embeddings fused via **Reciprocal Rank Fusion (`RRF`)** (`score = sum(1 / (k + rank_i))`) to eliminate single-retriever blind spots.
- **Neuro-Symbolic Factuality & Temporal Gating:** Extracts structured claims (entities, roles, organizations, employment/project date intervals) from candidate RAG answers and verifies them in `Z3` against grounded corpus facts—blocking anachronisms, hallucinated employers, and unsupported claims.
- **CEGIS Answer Repair Loop:** When `Z3` flags an `UNSAT` claim (e.g., year mismatch or ungrounded entity), the counterexample feeds back into constrained regeneration until all assertions hold or the system fails closed.
- **Deterministic IR Evaluation:** Benchmarks retrieval quality using standard Information Retrieval metrics (`Recall@k`, `MRR`, tail latency `p95`) over a curated Golden Dataset.

## 2. Frameworks and Libraries
| Layer | Technology | Version / Spec | Role in `interview-ops` |
| :--- | :--- | :--- | :--- |
| **Hybrid Retrieval & Store** | `duckdb` | `>=1.1.0` | Stores chunked corpus, lexical/vector indices, and executes deterministic `RRF` ranking queries. |
| **Formal Factuality Guard** | `z3-solver` | `>=4.13.0` | Proves entity membership and temporal interval consistency (`start_year <= end_year`, corpus grounding). |
| **Relational Persistence** | `psycopg[binary]` | `>=3.2.0` | PostgreSQL v3 driver for multi-node shared session/audit persistence across cluster nodes. |
| **Contracts & Protocol** | `pydantic`, `fastmcp` | `>=2.9.0`, `>=2.0.0` | Structured claim extraction models and `FastMCP` `stdio` tools (`search_evidence`, `verify_claim`). |
| **HTTP & QA Tooling** | `httpx`, `pytest`, `hypothesis`, `mypy` | Python `>=3.12` | Local `Ollama` embedding/generation transport, Golden IR benchmark suite, `--strict` typing (`14` files). |

## 3. Dev Tools and Environment
- **Distributed Local Cluster:** Calculate Linux Desktop (KDE, Kernel `6.18+`) across two Intel Core i5-9500 workstation nodes (`24 GiB` primary compute/storage node + `16 GiB` secondary node) connected via Gigabit Ethernet.
- **Local Embedding & Inference:** Offline `Ollama` (`127.0.0.1:11434`) serving local embedding and generative models with deterministic `seed=42` and `temperature=0.0`.
- **CI/CD & Artifact Verification:** GitHub Actions executing `ruff`, `mypy --strict`, offline `pytest` IR/Z3 regression suites, and `CycloneDX` SBOM generation.

## 4. Processes and Procedures
- **Golden Dataset IR Regression Gate:** Every change to chunking, `RRF` weighting, or `Z3` claim constraints is benchmarked against deterministic query-relevance pairs before merge.
- **Strict Grounding & Anti-Hallucination Policy:** Generated career/technical assertions cannot bypass `Z3` entity/temporal verification; ungrounded claims trigger `UNSAT` rejection rather than silent fallback.
- **Hygiene & Release Traceability:** Automated PII/secret scanning (`tests/test_release_hygiene.py`), `CR-XXX` changelog linking, and retrospective documentation (`docs/releases/`).

## 5. Test Approach, Tools, Environment & Metrics
- **Verification Pyramid:**
  1. *Retrieval Quality Benchmarks:* Automated `Recall@3` and Mean Reciprocal Rank (`MRR`) assertions over the Golden Dataset + `p95` query latency profiling.
  2. *Symbolic Fact-Checker Tests:* Adversarial claim injection (swapped dates, fabricated organizations, boundary years) verified against `Z3` `UNSAT` counterexamples + `Hypothesis` fuzzing.
  3. *MCP `stdio` & Hygiene Gates:* JSON-RPC contract tests for all exposed tools + documentation quality auditor.
- **Empirical Baseline Metrics (`v0.6.0` -> `v0.7.0`):**
  - **Retrieval Precision:** `Recall@3 = 0.9375`, `MRR = 1.0000` on the Golden evaluation benchmark.
  - **Tail Latency:** `p95 = 72.217 ms` end-to-end hybrid `RRF` retrieval + `Z3` claim verification on local CPU.
  - **Offline Fast Suite:** `27 passed`, `0` `mypy --strict` errors across `14` source files.
