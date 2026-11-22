# Architecture & Formal Verification Design — `interview-ops`

Domain-level architecture for grounded hybrid RAG (`pgvector` + `tsvector` RRF on `rhino`) coupled with symbolic Z3 Single Source of Truth (SSOT) verification on `hippo`. Part of the [`sandbox-init`](https://github.com/spanskikh/sandbox-init) cluster.

## 1. Cross-Node Hybrid Retrieval & Verification Flow
```mermaid
flowchart LR
    JD[Target Job Description] --> EMB[Ollama: nomic-embed-text 768-d]
    EMB -->|SSH Tunnel 15432 -> 5432| PG[(rhino: PostgreSQL + pgvector)]
    PG -->|Reciprocal Rank Fusion k=60| LLM[Ollama: qwen2.5-coder:7b]
    LLM -->|TailoredAnswerProposal| LEX[Lexical Skill & Year Extractor CR-003]
    LEX --> Z3{Z3 SSOT Fact-Checker}
    Z3 -->|SAT: Grounded Claims + Honest Gaps} OUT[Verified Output]
    Z3 -->|UNSAT: Skill/Year/Entity Drift| LLM
```

## 2. Architecture Decision Records (ADR)
- **ADR-INT-001 (Hybrid RRF over Dense-Only Vector Search):** Combines cosine similarity (`pgvector`) with lexical `ts_rank_cd` (`GIN tsvector`) via Reciprocal Rank Fusion (`k=60`) so exact tool names (`Z3`, `DuckDB`, `FastMCP`i) are never lost to semantic smoothing.
- **ADR-INT-002 (Free-Text Lexical Extraction Guard — CR-003):** Deterministic boundary-aware extraction scans `bullet_text` for unverified skills and 4-digit years, feeding them directly into Z3 SSOT subset constraints to block skill sneak-in hallucinations.
- **ADR-INT-003 (Explicit Skill-Gap Separation):** Missing job requirements must be emitted in `missing_required_skills` rather than fabricated inside experience bullets.

## 3. Trade-offs & Risk Control Matrix
- **PII & Career History Privacy:** 100% local inference on `hippo` and loopback-bound PostgreSQL on `rhino` over encrypted SSH tunnel (`pg-tunnel-rhino`); GDPR/BDSG compliant.
- **Free-Text Paraphrase Drift:** Deterministic lexical skill/year extractor closes exact token sneak-in (`CR-003`); expand canonical skill alias dictionary as SSOT grows.
