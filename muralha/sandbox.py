from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from muralha.catalog import ROOT

MAX_CANDIDATE_BYTES = 256_000
MAX_CASES = 100


def evaluate_cases_in_docker(
    candidate_root: Path,
    manifest: dict[str, Any],
    *,
    timeout_seconds: int = 25,
) -> dict[str, Any]:
    """Compara resultados de uma função candidata com casos mantidos fora do contêiner.

    Somente um caso por execução entra no contêiner. O gabarito esperado e a lista
    completa de casos nunca são montados no filesystem do código candidato.
    """
    cases = manifest.get("cases")
    function_name = manifest.get("function")
    if function_name != "can_access_document" or not isinstance(cases, list):
        return {"runner_status": "error", "message": "Manifesto de casos inválido."}
    if not 1 <= len(cases) <= MAX_CASES:
        return {"runner_status": "error", "message": "Quantidade de casos inválida."}
    if not candidate_root.is_dir() or not (candidate_root / "src" / "access_control.py").is_file():
        return {"runner_status": "error", "message": "Código candidato ausente."}
    if not shutil.which("docker"):
        return {"runner_status": "not_configured", "message": "Docker não está disponível."}

    image = os.getenv("MURALHA_DOCKER_IMAGE", "muralha-test-runner:py312")
    try:
        inspected = subprocess.run(
            ["docker", "image", "inspect", image],
            check=False, capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"runner_status": "not_configured", "message": "Não foi possível verificar a imagem do executor."}
    if inspected.returncode != 0:
        return {"runner_status": "not_configured", "message": "Imagem local de testes ausente."}

    candidate_path = candidate_root.resolve()
    results: list[dict[str, Any]] = []
    deadline = time.monotonic() + timeout_seconds

    for index, case in enumerate(cases):
        name = str(case.get("name", f"case-{index + 1}"))[:100] if isinstance(case, dict) else f"case-{index + 1}"
        if not isinstance(case, dict) or not isinstance(case.get("kwargs"), dict):
            return {"runner_status": "error", "message": "Formato de caso inválido."}
        if type(case.get("expected")) is not bool:
            return {"runner_status": "error", "message": "Resultado esperado deve ser booleano."}

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            results.append({"name": name, "passed": False})
            results.extend({"name": str(next_case.get("name", f"case-{n + 1}"))[:100],
                            "passed": False}
                           for n, next_case in enumerate(cases[index + 1:], start=index + 1)
                           if isinstance(next_case, dict))
            return {
                "runner_status": "timeout",
                "cases": results,
                "passed_count": sum(1 for item in results if item["passed"]),
                "total_count": len(cases),
                "message": "Tempo total de avaliação excedido.",
            }

        request = json.dumps(
            {"function": function_name, "kwargs": case["kwargs"]},
            ensure_ascii=False,
        )
        command = [
            "docker", "run", "--rm", "--pull=never", "-i",
            "--network=none", "--cpus=0.5", "--memory=256m", "--memory-swap=256m",
            "--pids-limit=64", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
            "--read-only", "--user=65534:65534",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
            "--mount", f"type=bind,src={candidate_path},dst=/candidate,readonly",
            "--workdir=/tmp", image,
            "python", "-I", "-B", "/opt/muralha/worker.py",
        ]
        try:
            completed = subprocess.run(
                command,
                input=request,
                capture_output=True,
                text=True,
                timeout=max(1, min(8, remaining)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            results.append({"name": name, "passed": False})
            results.extend({"name": str(next_case.get("name", f"case-{n + 1}"))[:100],
                            "passed": False}
                           for n, next_case in enumerate(cases[index + 1:], start=index + 1)
                           if isinstance(next_case, dict))
            return {
                "runner_status": "timeout",
                "cases": results,
                "passed_count": sum(1 for item in results if item["passed"]),
                "total_count": len(cases),
                "message": "Um caso excedeu o limite de tempo.",
            }
        except OSError:
            return {"runner_status": "error", "message": "Falha ao iniciar o contêiner."}

        passed = False
        try:
            lines = completed.stdout.splitlines()
            if completed.returncode == 0 and len(lines) == 1:
                response = json.loads(lines[0])
                passed = (
                    isinstance(response, dict)
                    and response.get("ok") is True
                    and type(response.get("value")) is bool
                    and response["value"] is case["expected"]
                )
        except (json.JSONDecodeError, TypeError):
            passed = False
        results.append({"name": name, "passed": passed})

    passed_count = sum(1 for item in results if item["passed"])
    return {
        "runner_status": "completed",
        "cases": results,
        "passed_count": passed_count,
        "total_count": len(cases),
        "message": "Todos os casos passaram." if passed_count == len(cases)
        else f"{passed_count}/{len(cases)} casos passaram.",
    }


def run_hidden_tests(
    challenge_id: str,
    challenge: dict[str, Any],
    candidate_files: dict[str, str],
    *,
    timeout_seconds: int = 25,
) -> dict[str, Any]:
    """Executa casos privados sem montar o gabarito dentro do contêiner."""
    if os.getenv("MURALHA_ENABLE_SANDBOX", "false").lower() != "true":
        return {"status": "not_configured", "passed": None, "message": "Executor desabilitado."}

    private_root = Path(os.getenv("MURALHA_PRIVATE_TESTS_DIR", "./private_tests")).resolve()
    manifest_path = (private_root / challenge_id / "cases.json").resolve()
    if private_root not in manifest_path.parents or not manifest_path.is_file():
        return {"status": "not_configured", "passed": None, "message": "Casos privados ausentes."}

    allowed_files = set(challenge.get("files", []))
    if set(candidate_files) - allowed_files:
        return {"status": "rejected", "passed": False, "message": "A submissão contém caminhos não permitidos."}
    if sum(len(content.encode("utf-8")) for content in candidate_files.values()) > MAX_CANDIDATE_BYTES:
        return {"status": "rejected", "passed": False, "message": "A submissão excede 256 KB."}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "error", "passed": None, "message": "Manifesto privado inválido."}

    with tempfile.TemporaryDirectory(prefix="muralha-") as temp:
        candidate_root = Path(temp) / "candidate"
        candidate_root.mkdir()
        source_root = (ROOT / "challenges" / challenge_id).resolve()
        for rel in allowed_files:
            source = (source_root / rel).resolve()
            target = (candidate_root / rel).resolve()
            if source_root not in source.parents or candidate_root.resolve() not in target.parents or not source.is_file():
                return {"status": "error", "passed": None, "message": "Fixture inválida."}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(candidate_files.get(rel, source.read_text(encoding="utf-8")),
                              encoding="utf-8")

        report = evaluate_cases_in_docker(candidate_root, manifest, timeout_seconds=timeout_seconds)

    runner_status = report.get("runner_status")
    if runner_status != "completed":
        return {
            "status": runner_status,
            "passed": None,
            "message": report.get("message", "Executor indisponível."),
        }

    passed_count = report["passed_count"]
    total_count = report["total_count"]
    passed = passed_count == total_count
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "passed_count": passed_count,
        "total_count": total_count,
        "message": report["message"],
    }
