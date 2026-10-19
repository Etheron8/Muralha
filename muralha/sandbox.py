from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from muralha.catalog import ROOT


def run_hidden_tests(
    challenge_id: str,
    challenge: dict[str, Any],
    candidate_files: dict[str, str],
    *,
    timeout_seconds: int = 25,
) -> dict[str, Any]:
    """Executa testes privados em Docker restrito; desabilitado por padrão.

    O worker deve ser hospedado em VM descartável, sem segredos. Nunca devolve
    stdout/stderr do processo não confiável para o cliente.
    """
    if os.getenv("MURALHA_ENABLE_SANDBOX", "false").lower() != "true":
        return {"status": "not_configured", "passed": None, "message": "Executor desabilitado."}

    private_root = Path(os.getenv("MURALHA_PRIVATE_TESTS_DIR", "./private_tests")).resolve()
    tests_dir = (private_root / challenge_id / "tests").resolve()
    if private_root not in tests_dir.parents or not tests_dir.is_dir():
        return {"status": "not_configured", "passed": None, "message": "Testes privados ausentes."}
    if not shutil.which("docker"):
        return {"status": "not_configured", "passed": None, "message": "Docker não está disponível."}

    allowed_files = set(challenge.get("files", []))
    if set(candidate_files) - allowed_files:
        return {"status": "rejected", "passed": False, "message": "A submissão contém caminhos não permitidos."}
    if sum(len(content.encode("utf-8")) for content in candidate_files.values()) > 256_000:
        return {"status": "rejected", "passed": False, "message": "A submissão excede 256 KB."}

    image = os.getenv("MURALHA_DOCKER_IMAGE", "python:3.12-slim")
    with tempfile.TemporaryDirectory(prefix="muralha-") as temp:
        candidate_root = Path(temp) / "candidate"
        candidate_root.mkdir()
        source_root = (ROOT / "challenges" / challenge_id).resolve()
        for rel in allowed_files:
            source = (source_root / rel).resolve()
            if source_root not in source.parents or not source.is_file():
                return {"status": "error", "passed": None, "message": "Fixture inválida."}
            target = (candidate_root / rel).resolve()
            if candidate_root.resolve() not in target.parents:
                return {"status": "rejected", "passed": False, "message": "Caminho inválido."}
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(candidate_files.get(rel, source.read_text(encoding="utf-8")),
                              encoding="utf-8")

        command = [
            "docker", "run", "--rm",
            "--network=none", "--cpus=0.5", "--memory=256m", "--memory-swap=256m",
            "--pids-limit=64", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
            "--read-only", "--user=65534:65534",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
            "-v", f"{candidate_root}:/candidate:ro",
            "-v", f"{tests_dir}:/tests:ro",
            "-w", "/candidate",
            image, "python", "-I", "-m", "pytest", "-q", "/tests",
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout_seconds, check=False
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "passed": False, "message": "Tempo de teste excedido."}
        except OSError:
            return {"status": "error", "passed": None, "message": "Falha ao iniciar o executor."}

        if completed.returncode == 0:
            return {"status": "passed", "passed": True, "message": "Testes funcionais aprovados."}
        return {"status": "failed", "passed": False, "message": "Um ou mais testes funcionais falharam."}
