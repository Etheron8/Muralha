from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from muralha.sandbox import evaluate_cases_in_docker  # noqa: E402
from score_ci_result import build_result, write_result  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa casos do benchmark em contêineres isolados.")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        manifest = json.loads(args.cases.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
        report = {"runner_status": "error", "message": "Não foi possível ler o manifesto de casos."}
    else:
        report = evaluate_cases_in_docker(args.candidate, manifest)

    runner_status = report.get("runner_status", "error")
    cases = report.get("cases", [])
    total_count = report.get("total_count", len(manifest.get("cases", [])))
    passed_count = report.get("passed_count", 0) if runner_status == "completed" else 0
    failed_tests = [item["name"] for item in cases if not item.get("passed", False)]
    result = build_result(
        passed_count=passed_count,
        total_count=total_count,
        failed_tests=failed_tests,
        runner_status=runner_status,
        runner_message=report.get("message", ""),
    )
    result["candidate_path"] = "challenges/authorization-bypass/src"
    write_result(result, args.output)

    for item in cases:
        print(f"{'PASS' if item.get('passed') else 'FAIL'} {item['name']}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
