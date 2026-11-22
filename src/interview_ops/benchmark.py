from __future__ import annotations

import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb

from interview_ops.contracts import ExperienceRecord

RetrievalMode = Literal["dense", "lexical", "hybrid_rrf"]


@dataclass(frozen=True)
class GoldenQuery:
    """Curated IR benchmark query with ground-truth SSOT record IDs."""

    query_id: str
    query_text: str
    relevant_ids: tuple[str, ...]
    category: Literal["semantic", "exact_token", "hybrid"]


@dataclass(frozen=True)
class BenchmarkReport:
    """Aggregated IR quality and latency metrics for a retrieval mode."""

    suite_name: str
    mode: RetrievalMode
    query_count: int
    recall_at_k: float
    mrr: float
    p95_latency_ms: float
    passed_gate: bool


GOLDEN_SSOT_CORPUS: list[ExperienceRecord] = [
    ExperienceRecord(
        record_id="exp_infineon_2023",
        company="Infineon Technologies",
        role="Systems and Automation QA Engineer",
        start_year=2023,
        end_year=2024,
        skills=["Python", "Docker", "Selenium Grid", "JMeter", "Locust"],
        summary=(
            "Led post-merger test management in semiconductor manufacturing; built Docker, "
            "Selenium Grid, JMeter, and Locust schema and load validation harnesses."
        ),
    ),
    ExperienceRecord(
        record_id="exp_prounix_2022",
        company="PROUNIX",
        role="Test Manager and Automation Architect",
        start_year=2022,
        end_year=2023,
        skills=["Python", "Robot Framework", "Selenium", "Docker", "Django", "REST"],
        summary=(
            "Defined risk-based E2E and UAT test strategies using Python, Robot Framework, "
            "and Docker BDD suites across Django REST and SQL microservices."
        ),
    ),
    ExperienceRecord(
        record_id="exp_ser_2017",
        company="SER Group",
        role="Senior Test Automation Developer and System Analyst",
        start_year=2017,
        end_year=2022,
        skills=["Python", "Java", "JavaScript", "Selenium", "REST", "BPMN", "RBAC"],
        summary=(
            "Engineered enterprise ECM and BPMN workflow automation frameworks, custom "
            "Tomcat JAR test extensions, RBAC security checks, and synthetic data generators."
        ),
    ),
    ExperienceRecord(
        record_id="exp_hl7_2016",
        company="Bonn Healthcare Telemetry Lab",
        role="Freelance Data Engineer and SDET",
        start_year=2016,
        end_year=2017,
        skills=["Python", "PostgreSQL", "JSONB", "HL7", "RDF", "SPARQL"],
        summary=(
            "Built fault-tolerant Python daemons, soft real-time HL7 clinical telemetry ETL "
            "pipelines into PostgreSQL JSONB, message-queue simulators, and RDF/SPARQL ontologies."
        ),
    ),
    ExperienceRecord(
        record_id="exp_dhl_2013",
        company="Deutsche Post DHL",
        role="Senior IT Security Architect and Compliance Engineer",
        start_year=2013,
        end_year=2016,
        skills=["DevSecOps", "GDPR", "BDSG", "ISO/IEC 27001", "Palamida", "EDI"],
        summary=(
            "Architected DevSecOps security gates, GDPR and BDSG compliance controls, "
            "ISO/IEC 27001 readiness, open-source license auditing, and EDI/UN/CEFACT checks."
        ),
    ),
    ExperienceRecord(
        record_id="exp_hermes_2009",
        company="Hermes-DPD JV",
        role="Head of Software Development",
        start_year=2009,
        end_year=2013,
        skills=["ETL", "Message Queues", "B2B Logistics", "ISO 27000"],
        summary=(
            "Directed B2B e-commerce logistics platform architecture, high-volume parcel "
            "tracking ETL pipelines, mobile barcode scanner integrations, and ISO 27000 audits."
        ),
    ),
    ExperienceRecord(
        record_id="exp_luxoft_2004",
        company="Luxoft",
        role="QA, Project Management, and Process Consultant",
        start_year=2004,
        end_year=2009,
        skills=["CMMI", "RUP", "Agile", "Oracle", "PostgreSQL"],
        summary=(
            "Led CMMI and Agile process transformations, IT security audits, and Oracle/"
            "PostgreSQL data architectures for Deutsche Bank and credit bureau aggregators."
        ),
    ),
    ExperienceRecord(
        record_id="exp_king_2001",
        company="King Products",
        role="Test Architect",
        start_year=2001,
        end_year=2004,
        skills=["CMMI", "ETL", "Telemetry", "Distributed Appliances"],
        summary=(
            "Architected automated test harnesses, context-aware ETL daemons, and remote "
            "diagnostic telemetry pipelines for distributed unattended kiosk appliances."
        ),
    ),
    ExperienceRecord(
        record_id="exp_sectorbase_1999",
        company="Sectorbase",
        role="Head of Software Development",
        start_year=1999,
        end_year=2001,
        skills=["kdb", "Tick Databases", "NLP", "DSL", "ETL"],
        summary=(
            "Led engineering for high-frequency tick databases, near real-time custom "
            "financial index calculation, semantic NLP news-mining engines, and DSL compilers."
        ),
    ),
    ExperienceRecord(
        record_id="exp_att_1997",
        company="AT&T Bell Labs",
        role="QA Data Architect",
        start_year=1997,
        end_year=1999,
        skills=["C++", "RBAC", "DLP", "Federal IT Security 822"],
        summary=(
            "Developed C++ controller software, RBAC access verification, Data Loss Prevention "
            "(DLP) compliance suites, and statistical test-data generation."
        ),
    ),
    ExperienceRecord(
        record_id="exp_aerospace_1989",
        company="Institute of Space Technologies",
        role="Senior Software Engineer — Satellite Diagnostics",
        start_year=1989,
        end_year=1997,
        skills=["Fortran", "C", "Prolog", "Predicate Logic", "Telemetry"],
        summary=(
            "Engineered satellite electromechanical telemetry diagnostics, 14-dimensional "
            "variational optimization in Fortran/C, and predicate logic inference in Prolog."
        ),
    ),
    ExperienceRecord(
        record_id="exp_aiqa_2026",
        company="Independent AI QA Lab",
        role="Principal AI QA and Neuro-Symbolic Architect",
        start_year=2026,
        end_year=2026,
        skills=["Z3", "FastMCP", "Pydantic", "DuckDB", "pgvector", "CEGIS"],
        summary=(
            "Designed neuro-symbolic verification harnesses combining Z3 SMT solvers, "
            "FastMCP stdio contracts, CEGIS repair loops, and hybrid pgvector RRF retrieval."
        ),
    ),
]


GOLDEN_QUERIES: list[GoldenQuery] = [
    GoldenQuery(
        query_id="q01_z3_cegis",
        query_text="Z3 SMT solver CEGIS verification loops and FastMCP",
        relevant_ids=("exp_aiqa_2026",),
        category="hybrid",
    ),
    GoldenQuery(
        query_id="q02_semiconductor_load",
        query_text="semiconductor post-merger Locust JMeter Selenium Grid load testing",
        relevant_ids=("exp_infineon_2023",),
        category="hybrid",
    ),
    GoldenQuery(
        query_id="q03_hl7_jsonb",
        query_text="HL7 healthcare telemetry ETL into PostgreSQL JSONB and SPARQL",
        relevant_ids=("exp_hl7_2016",),
        category="exact_token",
    ),
    GoldenQuery(
        query_id="q04_gdpr_iso27001",
        query_text="GDPR BDSG data protection compliance and ISO/IEC 27001 DevSecOps",
        relevant_ids=("exp_dhl_2013",),
        category="exact_token",
    ),
    GoldenQuery(
        query_id="q05_robot_bdd",
        query_text="Robot Framework BDD UAT test strategy for Django REST APIs",
        relevant_ids=("exp_prounix_2022",),
        category="hybrid",
    ),
    GoldenQuery(
        query_id="q06_bpmn_ecm",
        query_text="enterprise ECM BPMN workflow automation and Tomcat JAR extensions",
        relevant_ids=("exp_ser_2017",),
        category="exact_token",
    ),
    GoldenQuery(
        query_id="q07_parcel_logistics",
        query_text="B2B e-commerce parcel tracking ETL and barcode scanner logistics",
        relevant_ids=("exp_hermes_2009",),
        category="semantic",
    ),
    GoldenQuery(
        query_id="q08_cmmi_banking",
        query_text="CMMI process improvement and Oracle PostgreSQL architecture for banking",
        relevant_ids=("exp_luxoft_2004",),
        category="hybrid",
    ),
    GoldenQuery(
        query_id="q09_kiosk_telemetry",
        query_text="remote diagnostic telemetry for unattended distributed kiosk appliances",
        relevant_ids=("exp_king_2001",),
        category="semantic",
    ),
    GoldenQuery(
        query_id="q10_tick_nlp",
        query_text="high-frequency financial tick databases and NLP news-mining DSL",
        relevant_ids=("exp_sectorbase_1999",),
        category="hybrid",
    ),
    GoldenQuery(
        query_id="q11_dlp_cpp",
        query_text="C++ controller software Data Loss Prevention DLP and RBAC security",
        relevant_ids=("exp_att_1997",),
        category="exact_token",
    ),
    GoldenQuery(
        query_id="q12_satellite_prolog",
        query_text="satellite telemetry diagnostics variational optimization Fortran and Prolog",
        relevant_ids=("exp_aerospace_1989",),
        category="hybrid",
    ),
    GoldenQuery(
        query_id="q13_formal_logic_reasoning",
        query_text="formal predicate logic and SMT constraint verification systems",
        relevant_ids=("exp_aiqa_2026", "exp_aerospace_1989"),
        category="semantic",
    ),
    GoldenQuery(
        query_id="q14_security_rbac_audits",
        query_text="RBAC access control verification and enterprise IT security audits",
        relevant_ids=("exp_ser_2017", "exp_att_1997", "exp_dhl_2013"),
        category="semantic",
    ),
    GoldenQuery(
        query_id="q15_realtime_etl_pipelines",
        query_text="real-time event ingestion ETL pipelines and message queue telemetry",
        relevant_ids=("exp_hl7_2016", "exp_hermes_2009", "exp_sectorbase_1999"),
        category="semantic",
    ),
    GoldenQuery(
        query_id="q16_python_test_automation",
        query_text="Python automated test frameworks and schema validation pipelines",
        relevant_ids=("exp_infineon_2023", "exp_prounix_2022", "exp_ser_2017"),
        category="semantic",
    ),
]


_TOKEN_RE = re.compile(r"[a-z0-9_/+.-]+")

_CONCEPT_CLUSTERS: dict[str, tuple[str, ...]] = {
    "formal_verification": ("z3", "smt", "cegis", "prolog", "predicate", "logic", "constraint"),
    "security_compliance": ("gdpr", "bdsg", "iso", "27001", "rbac", "dlp", "devsecops", "security"),
    "test_automation": ("qa", "test", "selenium", "pytest", "robot", "jmeter", "locust", "bdd"),
    "data_etl": ("etl", "telemetry", "pipeline", "postgresql", "jsonb", "tick", "kdb", "hl7"),
    "logistics_enterprise": ("logistics", "parcel", "bpmn", "ecm", "kiosk", "banking", "oracle"),
}


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) > 1]


def deterministic_concept_vector(text: str, dims: int = 32) -> list[float]:
    """Deterministic semantic-bucket + hashed n-gram embedding for offline IR tests."""
    tokens = _tokenize(text)
    vec = [0.0] * dims
    for idx, (_, keywords) in enumerate(_CONCEPT_CLUSTERS.items()):
        hits = sum(1 for tok in tokens if any(kw in tok for kw in keywords))
        if hits > 0:
            vec[idx] = 2.0 + math.log1p(hits)
    offset = len(_CONCEPT_CLUSTERS)
    span = dims - offset
    for tok in tokens:
        bucket = offset + (sum(ord(ch) for ch in tok) % span)
        vec[bucket] += 0.35
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class InMemoryHybridEngine:
    """Offline reference implementation mirroring PgHybridStore RRF (k=60) semantics."""

    def __init__(self, records: list[ExperienceRecord]) -> None:
        self._records = list(records)
        self._vectors: dict[str, list[float]] = {
            rec.record_id: deterministic_concept_vector(
                f"{rec.role} {rec.company} {' '.join(rec.skills)} {rec.summary}"
            )
            for rec in self._records
        }
        self._doc_tokens: dict[str, list[str]] = {
            rec.record_id: _tokenize(f"{rec.role} {' '.join(rec.skills)} {rec.summary}")
            for rec in self._records
        }

    def dense_search(
        self, query_text: str, top_k: int = 3
    ) -> list[tuple[ExperienceRecord, float]]:
        q_vec = deterministic_concept_vector(query_text)
        scored = [
            (rec, _cosine_similarity(q_vec, self._vectors[rec.record_id]))
            for rec in self._records
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def lexical_search(
        self, query_text: str, top_k: int = 3
    ) -> list[tuple[ExperienceRecord, float]]:
        q_tokens = set(_tokenize(query_text))
        scored: list[tuple[ExperienceRecord, float]] = []
        for rec in self._records:
            d_tokens = self._doc_tokens[rec.record_id]
            if not d_tokens:
                continue
            tf_hits = sum(1 for tok in d_tokens if tok in q_tokens)
            if tf_hits > 0:
                score = tf_hits / math.sqrt(len(d_tokens))
                scored.append((rec, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def hybrid_search(
        self, query_text: str, top_k: int = 3, rrf_k: float = 60.0
    ) -> list[tuple[ExperienceRecord, float]]:
        vec_ranked = self.dense_search(query_text, top_k=20)
        fts_ranked = self.lexical_search(query_text, top_k=20)
        vec_pos = {rec.record_id: idx + 1 for idx, (rec, _) in enumerate(vec_ranked)}
        fts_pos = {rec.record_id: idx + 1 for idx, (rec, _) in enumerate(fts_ranked)}
        fused: list[tuple[ExperienceRecord, float]] = []
        for rec in self._records:
            rid = rec.record_id
            r_vec = vec_pos.get(rid)
            r_fts = fts_pos.get(rid)
            score = (1.0 / (rrf_k + r_vec) if r_vec is not None else 0.0) + (
                1.0 / (rrf_k + r_fts) if r_fts is not None else 0.0
            )
            fused.append((rec, score))
        fused.sort(key=lambda item: item[1], reverse=True)
        return fused[:top_k]


def compute_recall_at_k(
        retrieved_ids: list[str], relevant_ids: tuple[str, ...], k: int = 3
) -> float:
    if not relevant_ids:
        return 1.0
    top_set = set(retrieved_ids[:k])
    rel_set = set(relevant_ids)
    # Standard IR Recall@K capped by min(K, |relevant|) so K=3 cannot penalize |relevant| > 3
    denom = min(k, len(rel_set))
    return len(top_set & rel_set) / float(denom)


def compute_reciprocal_rank(retrieved_ids: list[str], relevant_ids: tuple[str, ...]) -> float:
    rel_set = set(relevant_ids)
    for rank_idx, rid in enumerate(retrieved_ids, start=1):
        if rid in rel_set:
            return 1.0 / float(rank_idx)
    return 0.0


def compute_p95_ms(latencies_ms: list[float]) -> float:
    if not latencies_ms:
        return 0.0
    ordered = sorted(latencies_ms)
    idx = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[idx]


def evaluate_retrieval_mode(
    search_fn: Callable[[str, int], list[tuple[ExperienceRecord, float]]],
    queries: list[GoldenQuery],
    mode: RetrievalMode,
    suite_name: str = "cr011_golden_v1",
    top_k: int = 3,
    min_recall: float = 0.90,
    min_mrr: float = 0.85,
    max_p95_ms: float = 150.0,
) -> BenchmarkReport:
    recalls: list[float] = []
    rrs: list[float] = []
    latencies_ms: list[float] = []

    for q in queries:
        t0 = time.perf_counter()
        hits = search_fn(q.query_text, top_k)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        hit_ids = [rec.record_id for rec, _ in hits]
        recalls.append(compute_recall_at_k(hit_ids, q.relevant_ids, k=top_k))
        rrs.append(compute_reciprocal_rank(hit_ids, q.relevant_ids))

    mean_recall = sum(recalls) / float(len(recalls))
    mean_mrr = sum(rrs) / float(len(rrs))
    p95_ms = compute_p95_ms(latencies_ms)
    passed = (mean_recall >= min_recall) and (mean_mrr >= min_mrr) and (p95_ms < max_p95_ms)

    return BenchmarkReport(
        suite_name=suite_name,
        mode=mode,
        query_count=len(queries),
        recall_at_k=round(mean_recall, 4),
        mrr=round(mean_mrr, 4),
        p95_latency_ms=round(p95_ms, 3),
        passed_gate=passed,
    )


def persist_benchmark_report(db_path: str | Path, report: BenchmarkReport) -> None:
    """Persist IR benchmark report to DuckDB (compatible with sandbox-init telemetry schema)."""
    conn = duckdb.connect(str(db_path))
    try:
        conn.execute("SET memory_limit='512MB'; SET threads=2;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_benchmarks (
                ts TIMESTAMP DEFAULT current_timestamp,
                suite_name VARCHAR NOT NULL,
                mode VARCHAR NOT NULL,
                query_count INTEGER NOT NULL,
                recall_at_k DOUBLE NOT NULL,
                mrr DOUBLE NOT NULL,
                p95_latency_ms DOUBLE NOT NULL,
                passed_gate BOOLEAN NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO rag_benchmarks (
                suite_name, mode, query_count, recall_at_k, mrr, p95_latency_ms, passed_gate
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                report.suite_name,
                report.mode,
                report.query_count,
                report.recall_at_k,
                report.mrr,
                report.p95_latency_ms,
                report.passed_gate,
            ],
        )
    finally:
        conn.close()
