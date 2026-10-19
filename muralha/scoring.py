from __future__ import annotations

from typing import Any


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _contains_any(text: str, phrases: list[str]) -> bool:
    normalized = _norm(text)
    return any(_norm(phrase) in normalized for phrase in phrases if _norm(phrase))


def score_diagnosis(finding: dict[str, Any], golden: dict[str, Any]) -> dict[str, Any]:
    """Pontua um diagnóstico em até 70 pontos. Não executa código submetido."""
    details: dict[str, dict[str, Any]] = {}

    cwe_ok = _norm(finding.get("cwe")) == _norm(golden.get("cwe"))
    details["classification"] = {"earned": 20 if cwe_ok else 0, "max": 20, "passed": cwe_ok}

    severity_ok = _norm(finding.get("severity")) == _norm(golden.get("severity"))
    details["severity"] = {"earned": 10 if severity_ok else 0, "max": 10, "passed": severity_ok}

    expected_file = _norm(golden.get("file"))
    actual_file = _norm(finding.get("file"))
    file_ok = bool(expected_file and (actual_file == expected_file or actual_file.endswith("/" + expected_file)))
    details["location_file"] = {"earned": 10 if file_ok else 0, "max": 10, "passed": file_ok}

    line_range = golden.get("line_range", [1, 1])
    try:
        line = int(finding.get("line"))
        line_ok = int(line_range[0]) <= line <= int(line_range[1])
    except (TypeError, ValueError, IndexError):
        line_ok = False
    details["location_line"] = {"earned": 5 if line_ok else 0, "max": 5, "passed": line_ok}

    root_phrases = golden.get("root_cause_phrases", [])
    root_ok = _contains_any(finding.get("description", ""), root_phrases)
    details["root_cause"] = {"earned": 15 if root_ok else 0, "max": 15, "passed": root_ok}

    fix_phrases = golden.get("fix_phrases", [])
    fix_ok = _contains_any(finding.get("fix_summary", ""), fix_phrases)
    details["proposed_fix"] = {"earned": 10 if fix_ok else 0, "max": 10, "passed": fix_ok}

    total = sum(item["earned"] for item in details.values())
    feedback = [
        f"{name}: {'ok' if value['passed'] else 'não atingiu o critério'} "
        f"({value['earned']}/{value['max']})."
        for name, value in details.items()
    ]
    return {
        "diagnostic_score": total,
        "diagnostic_max": 70,
        "score_breakdown": details,
        "feedback": feedback,
    }
