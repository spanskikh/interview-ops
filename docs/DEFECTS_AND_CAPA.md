# Defects & CAPA Registry

## CAPA-002: Cross-Session Context Drift, Toolchain Mismatch & Language Governance
- **Triggering Incidents:** New release chat sessions guessing unverified Pydantic/MCP schemas, invoking `uv` instead of `.venv/bin/`, pasting `set -e` into interactive shells, and risking Russian text leakage into Git artifacts.
- **Root Cause:** Operational engineering conventions existed only in ephemeral chat history rather than a versioned, machine-checked repository standard.
- **Corrective & Preventive Action (`CR-013`):** Codified `DEVPROCESS.md` across all 4 repositories (`Zero-Orphan Artifact Rule`, `Chat vs. Git Language Split`, `Zero-Guesswork Contract Rule`, and `.venv/bin/` + `./scripts/run_logged.sh` standard), backed by `tests/test_docs_quality.py` (`LANGUAGE_DRIFT_CYRILLIC`).
