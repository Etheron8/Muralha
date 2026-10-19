"""Wrapper confiável dentro do contêiner; recebe somente um caso por execução."""
from __future__ import annotations

import json
import os
import subprocess
import sys


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def main() -> int:
    try:
        raw = sys.stdin.read(65_537)
        if len(raw.encode("utf-8")) > 65_536:
            emit({"ok": False, "error": "input_too_large"})
            return 0
        request = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        emit({"ok": False, "error": "invalid_request"})
        return 0

    if not isinstance(request, dict) or request.get("function") != "can_access_document":
        emit({"ok": False, "error": "unsupported_function"})
        return 0
    kwargs = request.get("kwargs")
    if not isinstance(kwargs, dict):
        emit({"ok": False, "error": "invalid_arguments"})
        return 0

    safe_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        child = subprocess.run(
            [sys.executable, "-I", "-B", "/opt/muralha/invoke_candidate.py"],
            input=json.dumps(kwargs, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=4,
            env=safe_env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        emit({"ok": False, "error": "candidate_timeout"})
        return 0
    except OSError:
        emit({"ok": False, "error": "candidate_launch_failed"})
        return 0

    lines = child.stdout.splitlines()
    if child.returncode != 0 or len(lines) != 1:
        emit({"ok": False, "error": "candidate_execution_failed"})
        return 0
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError:
        emit({"ok": False, "error": "candidate_returned_invalid_json"})
        return 0
    if type(value) is not bool:
        emit({"ok": False, "error": "candidate_return_type_invalid"})
        return 0

    emit({"ok": True, "value": value})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
