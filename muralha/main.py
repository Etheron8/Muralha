from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from muralha.catalog import load_catalog, public_challenge
from muralha.sandbox import run_hidden_tests
from muralha.scoring import score_diagnosis
from muralha.store import Store

APP_VERSION = "0.1.0"
BENCHMARK_ID = "muralha-baseline-v1"
GOLDEN_DIR = Path(os.getenv("MURALHA_GOLDEN_DIR", "./private_oracles")).resolve()

app = FastAPI(
    title="Muralha Benchmark API",
    description=(
        "Central independente de desafios para IAs locais/remotas. "
        "A API retorna resultados estruturados que o próprio agente pode consumir."
    ),
    version=APP_VERSION,
)
store = Store()
rate_windows: dict[tuple[str, str], deque[float]] = defaultdict(deque)


class SessionCreate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=100)
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=120)
    benchmark_id: str = Field(default=BENCHMARK_ID, max_length=80)


class Finding(BaseModel):
    cwe: str = Field(min_length=1, max_length=40)
    severity: str = Field(min_length=1, max_length=20)
    file: str = Field(min_length=1, max_length=240)
    line: int = Field(ge=1, le=1_000_000)
    description: str = Field(min_length=1, max_length=4000)
    fix_summary: str = Field(min_length=1, max_length=4000)


class Submission(BaseModel):
    session_id: str = Field(min_length=36, max_length=36)
    challenge_id: str = Field(min_length=1, max_length=100)
    finding: Finding
    candidate_files: dict[str, str] = Field(default_factory=dict)
    agent_notes: str | None = Field(default=None, max_length=4000)


def private_golden(challenge_id: str) -> dict[str, Any] | None:
    path = (GOLDEN_DIR / f"{challenge_id}.json").resolve()
    if GOLDEN_DIR not in path.parents or not path.is_file():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


@app.middleware("http")
async def basic_rate_limit(request: Request, call_next):
    # Proteção básica por processo; o proxy/serviço de produção também deve limitar tráfego.
    client = request.client.host if request.client else "unknown"
    bucket = "submission" if request.url.path == "/v1/submissions" else "general"
    limit = 10 if bucket == "submission" else 120
    now = time.monotonic()
    window = rate_windows[(client, bucket)]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        return JSONResponse(status_code=429, content={
            "error": "rate_limit_exceeded",
            "message": "Limite temporário de requisições atingido. Tente novamente em breve.",
        })
    window.append(now)
    return await call_next(request)


@app.get("/v1/health", tags=["service"])
def health() -> dict[str, Any]:
    challenges = load_catalog()
    private_ready = all(private_golden(c["id"]) is not None for c in challenges)
    sandbox_enabled = os.getenv("MURALHA_ENABLE_SANDBOX", "false").lower() == "true"
    return {
        "service": "Muralha Benchmark API",
        "version": APP_VERSION,
        "status": "ready" if private_ready else "catalog_only",
        "catalog_loaded": True,
        "private_evaluators_configured": private_ready,
        "sandbox_enabled": sandbox_enabled,
        "benchmark_id": BENCHMARK_ID,
    }


@app.get("/v1/benchmarks", tags=["catalog"])
def benchmarks() -> dict[str, Any]:
    catalog = load_catalog()
    return {
        "benchmarks": [{
            "id": BENCHMARK_ID,
            "name": "Muralha Baseline",
            "version": "1",
            "challenge_count": len(catalog),
            "protocol_version": "1.0",
        }]
    }


@app.get("/v1/challenges", tags=["catalog"])
def challenges() -> dict[str, Any]:
    return {"challenges": [public_challenge(item) for item in load_catalog()]}


@app.get("/v1/challenges/{challenge_id}", tags=["catalog"])
def challenge_detail(challenge_id: str) -> dict[str, Any]:
    for item in load_catalog():
        if item["id"] == challenge_id:
            return public_challenge(item, include_files=True)
    raise HTTPException(status_code=404, detail="Desafio não encontrado.")


@app.post("/v1/sessions", tags=["evaluation"])
def create_session(payload: SessionCreate) -> dict[str, Any]:
    if payload.benchmark_id != BENCHMARK_ID:
        raise HTTPException(status_code=400, detail="Benchmark desconhecido.")
    session_id = str(uuid.uuid4())
    store.create_session(session_id, payload.agent_name.strip(), payload.provider,
                         payload.model, payload.benchmark_id)
    return {
        "session_id": session_id,
        "agent_name": payload.agent_name.strip(),
        "benchmark_id": payload.benchmark_id,
        "status": "created",
        "next_step": "GET /v1/challenges",
        "submit_to": "POST /v1/submissions",
        "results_url": f"/v1/sessions/{session_id}/results",
    }


@app.post("/v1/submissions", tags=["evaluation"])
def submit(payload: Submission) -> dict[str, Any]:
    session = store.get_session(payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    catalog = {item["id"]: item for item in load_catalog()}
    challenge = catalog.get(payload.challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Desafio não encontrado.")

    golden = private_golden(payload.challenge_id)
    if golden is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "evaluator_not_configured",
                "message": "O catálogo está disponível, mas o avaliador privado ainda não foi instalado.",
                "required": f"Arquivo {payload.challenge_id}.json em MURALHA_GOLDEN_DIR",
            },
        )

    diagnosis = score_diagnosis(payload.finding.model_dump(), golden)
    if payload.candidate_files:
        functional = run_hidden_tests(
            payload.challenge_id, challenge, payload.candidate_files
        )
    else:
        functional = {
            "status": "not_submitted",
            "passed": None,
            "message": "Nenhum arquivo corrigido foi enviado; testes funcionais não executados.",
        }

    functional_status = functional.get("status")
    tests_passed = functional_status == "passed"
    tests_failed = functional_status in ("failed", "timeout")
    tests_executed = tests_passed or tests_failed
    score = diagnosis["diagnostic_score"] + (30 if tests_passed else 0) if tests_executed else None
    result = {
        "schema_version": "1.0",
        "submission_id": str(uuid.uuid4()),
        "session_id": payload.session_id,
        "benchmark_id": challenge.get("benchmark_id", BENCHMARK_ID),
        "challenge_id": payload.challenge_id,
        "agent": {
            "name": session["agent_name"],
            "provider": session["provider"],
            "model": session["model"],
        },
        "score": score,
        "score_max": 100 if tests_executed else None,
        "diagnostic_score": diagnosis["diagnostic_score"],
        "diagnostic_score_max": diagnosis["diagnostic_max"],
        "score_breakdown": diagnosis["score_breakdown"],
        "tests": functional,
        "status": (
            "failed" if tests_failed or (tests_passed and diagnosis["diagnostic_score"] < 50)
            else "passed" if tests_passed
            else "pending"
        ),
        "feedback": diagnosis["feedback"],
        "recommendation": (
            "Revise o feedback e envie uma nova submissão."
            if score is None or score < 80
            else "Resultado forte neste desafio; continue com outros desafios."
        ),
    }
    store.add_submission(result["submission_id"], payload.session_id, payload.challenge_id,
                         score, result)
    return result


@app.get("/v1/sessions/{session_id}/results", tags=["evaluation"])
def session_results(session_id: str) -> dict[str, Any]:
    if not store.get_session(session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    results = store.session_results(session_id)
    scored = [item["score"] for item in results if isinstance(item.get("score"), int)]
    return {
        "session_id": session_id,
        "submissions_count": len(results),
        "final_score_average": round(sum(scored) / len(scored), 2) if scored else None,
        "results": results,
    }


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": "Muralha Benchmark API",
        "docs": "/docs",
        "health": "/v1/health",
    }
