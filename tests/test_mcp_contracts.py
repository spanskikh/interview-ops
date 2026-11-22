from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, TextContent

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TOOLS: dict[str, set[str]] = {
    "hybrid_search_ssot": {"query"},
    "generate_verified_cv_claims": {"job_description"},
    "audit_cv_proposal": {"proposal_json", "ssot_json"},
}

HARNESS_ENTRYPOINT = textwrap.dedent(
    """
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch
    from interview_ops import server
    from interview_ops.contracts import (
        ExperienceRecord,
        FactAuditVerdict,
        ResumeClaim,
        TailoredAnswerProposal,
    )

    _SSOT_REC = ExperienceRecord(
        record_id="exp_infineon_2023",
        company="Infineon Technologies",
        role="Systems & Automation QA Engineer",
        start_year=2023,
        end_year=2024,
        skills=["Python", "Docker", "PyTest", "Z3"],
        summary="Engineered post-merger test harnesses and schema validation pipelines.",
    )

    class _StubPgStore:
        def hybrid_search(
            self,
            query: str,
            q_vec: list[float],
            top_k: int = 3,
        ) -> list[tuple[ExperienceRecord, float]]:
            return [(_SSOT_REC, 0.91)]

    async def _fake_embed(client: object, text: str, ollama_url: str = "") -> list[float]:
        return [0.1, 0.2, 0.3]

    async def _fake_cv_cegis(
        job_description: str,
        ssot: list[ExperienceRecord],
        max_iters: int = 4,
    ) -> SimpleNamespace:
        claim = ResumeClaim(
            source_record_id="exp_infineon_2023",
            company="Infineon Technologies",
            start_year=2023,
            end_year=2024,
            claimed_skills=["Python", "PyTest"],
            bullet_text=(
                "Built Python and PyTest schema validation harnesses "
                "at Infineon Technologies (2023-2024)."
            ),
        )
        proposal = TailoredAnswerProposal(
            target_role="AI QA Architect",
            claims=[claim],
            missing_required_skills=[],
        )
        verdict = FactAuditVerdict(status="SAT", verified_claims=1, violations=[])
        return SimpleNamespace(
            converged=True,
            iterations=1,
            final_verdict=verdict,
            final_proposal=proposal,
        )

    with (
        patch.object(server, "PgHybridStore", _StubPgStore),
        patch.object(server, "embed_text", new=AsyncMock(side_effect=_fake_embed)),
        patch.object(server, "run_grounded_cv_cegis", new=AsyncMock(side_effect=_fake_cv_cegis)),
    ):
        server.mcp.run(transport="stdio")
    """
).strip()


def _extract_dict(result: CallToolResult) -> dict[str, Any]:
    assert not result.is_error, f"Unexpected MCP tool error: {result.content}"
    if isinstance(result.structured_content, dict):
        return result.structured_content
    first = result.content[0]
    assert isinstance(first, TextContent)
    parsed = json.loads(first.text)
    assert isinstance(parsed, dict)
    return parsed


def _extract_list(result: CallToolResult) -> list[dict[str, Any]]:
    assert not result.is_error, f"Unexpected MCP tool error: {result.content}"
    if isinstance(result.structured_content, dict) and "result" in result.structured_content:
        val = result.structured_content["result"]
        assert isinstance(val, list)
        return val
    items: list[dict[str, Any]] = []
    for block in result.content:
        assert isinstance(block, TextContent)
        parsed = json.loads(block.text)
        if isinstance(parsed, list):
            items.extend(parsed)
        elif isinstance(parsed, dict):
            items.append(parsed)
    return items


def _server_params() -> StdioServerParameters:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return StdioServerParameters(
        command=sys.executable,
        args=["-c", HARNESS_ENTRYPOINT],
        env=env,
    )


@pytest.mark.asyncio
async def test_stdio_tool_discovery_and_schemas() -> None:
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()

    tools_by_name = {tool.name: tool for tool in listed.tools}
    assert set(tools_by_name) == set(EXPECTED_TOOLS)

    for name, expected_required in EXPECTED_TOOLS.items():
        schema = tools_by_name[name].input_schema
        assert schema.get("type") == "object"
        required = set(schema.get("required", []))
        assert expected_required.issubset(required)


@pytest.mark.asyncio
async def test_stdio_z3_sat_and_unsat_cv_audits() -> None:
    ssot_json = [
        {
            "record_id": "exp_infineon_2023",
            "company": "Infineon Technologies",
            "role": "Systems & Automation QA Engineer",
            "start_year": 2023,
            "end_year": 2024,
            "skills": ["Python", "Docker", "PyTest"],
            "summary": "Engineered post-merger test harnesses and schema validation pipelines.",
        }
    ]

    sat_proposal = {
        "target_role": "AI QA Architect",
        "claims": [
            {
                "source_record_id": "exp_infineon_2023",
                "company": "Infineon Technologies",
                "start_year": 2023,
                "end_year": 2024,
                "claimed_skills": ["Python", "PyTest"],
                "bullet_text": (
                    "Built Python and PyTest automation harnesses "
                    "at Infineon Technologies."
                ),
            }
        ],
        "missing_required_skills": [],
    }

    unsat_hallucinated_proposal = {
        "target_role": "AI QA Architect",
        "claims": [
            {
                "source_record_id": "exp_infineon_2023",
                "company": "Infineon Technologies",
                "start_year": 2020,
                "end_year": 2024,
                "claimed_skills": ["Kubernetes", "Rust"],
                "bullet_text": (
                    "Led Rust and Kubernetes migration at Infineon Technologies "
                    "from 2020 to 2024."
                ),
            }
        ],
        "missing_required_skills": [],
    }

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            sat_res = await session.call_tool(
                "audit_cv_proposal",
                {"proposal_json": sat_proposal, "ssot_json": ssot_json},
            )
            sat_data = _extract_dict(sat_res)
            assert sat_data["status"] == "SAT"
            assert sat_data["verified_claims"] == 1
            assert sat_data["violations"] == []

            unsat_res = await session.call_tool(
                "audit_cv_proposal",
                {"proposal_json": unsat_hallucinated_proposal, "ssot_json": ssot_json},
            )
            unsat_data = _extract_dict(unsat_res)
            assert unsat_data["status"] == "UNSAT"
            assert len(unsat_data["violations"]) >= 1

            search_res = await session.call_tool(
                "hybrid_search_ssot",
                {"query": "Python PyTest schema validation", "top_k": 1},
            )
            hits = _extract_list(search_res)
            assert len(hits) == 1
            assert hits[0]["record_id"] == "exp_infineon_2023"

            gen_res = await session.call_tool(
                "generate_verified_cv_claims",
                {"job_description": "Senior AI QA Engineer", "top_k": 1, "max_iters": 2},
            )
            gen_data = _extract_dict(gen_res)
            assert gen_data["converged"] is True
            assert gen_data["verdict"]["status"] == "SAT"


@pytest.mark.asyncio
async def test_stdio_pydantic_validation_rejection() -> None:
    malformed_proposal = {
        "target_role": "AI QA Architect",
        "claims": [
            {
                "source_record_id": "exp_infineon_2023",
                "company": "Infineon Technologies",
                "start_year": 1750,
                "end_year": 2024,
                "claimed_skills": ["Python"],
                "bullet_text": "Invalid year below ge=1980 constraint.",
            }
        ],
    }

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            bad_year = await session.call_tool(
                "audit_cv_proposal",
                {"proposal_json": malformed_proposal, "ssot_json": []},
            )
            assert bad_year.is_error is True

            missing_args = await session.call_tool("audit_cv_proposal", {})
            assert missing_args.is_error is True
