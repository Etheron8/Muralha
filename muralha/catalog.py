from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "catalog" / "challenges.json"


def load_catalog(path: Path = CATALOG_PATH) -> list[dict[str, Any]]:
    """Carrega e valida metadados públicos; nunca carrega gabaritos."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("O catálogo deve ser uma lista.")
    seen: set[str] = set()
    for item in raw:
        challenge_id = item.get("id")
        if not isinstance(challenge_id, str) or not challenge_id:
            raise ValueError("Cada desafio precisa de um id.")
        if challenge_id in seen:
            raise ValueError(f"ID duplicado no catálogo: {challenge_id}")
        seen.add(challenge_id)
        files = item.get("files", [])
        if not isinstance(files, list) or not files:
            raise ValueError(f"O desafio {challenge_id} precisa ter arquivos.")
        for rel in files:
            candidate = Path(rel)
            if candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError(f"Caminho não permitido no desafio {challenge_id}.")
    return raw


def public_challenge(item: dict[str, Any], include_files: bool = False) -> dict[str, Any]:
    """Remove campos internos e, opcionalmente, carrega apenas arquivos listados."""
    result = {
        "id": item["id"],
        "benchmark_id": item.get("benchmark_id", "muralha-baseline-v1"),
        "title": item["title"],
        "category": item["category"],
        "difficulty": item["difficulty"],
        "description": item["description"],
        "task": item["task"],
        "points_available": 100,
    }
    if include_files:
        files: dict[str, str] = {}
        for rel in item["files"]:
            path = (ROOT / "challenges" / item["id"] / rel).resolve()
            challenge_root = (ROOT / "challenges" / item["id"]).resolve()
            if challenge_root not in path.parents or not path.is_file():
                raise ValueError(f"Arquivo do desafio ausente ou inválido: {rel}")
            files[rel] = path.read_text(encoding="utf-8")
        result["files"] = files
        readme = ROOT / "challenges" / item["id"] / "README.md"
        if readme.is_file():
            result["instructions"] = readme.read_text(encoding="utf-8")
    return result
