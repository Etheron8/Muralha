from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def build_result(
    passed_count: int,
    total_count: int,
    failed_tests: list[str] | None = None,
    runner_status: str = "completed",
    runner_message: str = "",
) -> dict[str, Any]:
    valid_counts = total_count > 0 and 0 <= passed_count <= total_count
    passed = passed_count if valid_counts else 0
    total = total_count if total_count > 0 else 0
    runner_completed = runner_status == "completed"
    score = round(100 * passed / total) if valid_counts and runner_completed else None
    status = (
        ("passed" if passed == total else "failed")
        if valid_counts and runner_completed
        else runner_status
    )
    if not runner_completed:
        feedback = runner_message or "O executor não conseguiu concluir os testes."
    elif passed == total:
        feedback = "Todos os testes de comportamento passaram."
    else:
        feedback = f"{passed}/{total} testes passaram. Revise os casos reprovados."

    return {
        "schema_version": "1.0",
        "benchmark_id": "muralha-baseline-v1",
        "challenge_id": "authorization-bypass",
        "pull_request_number": os.getenv("PR_NUMBER"),
        "candidate_commit": os.getenv("HEAD_SHA"),
        "score": score,
        "score_max": 100,
        "status": status,
        "evaluation": {
            "type": "functional-tests",
            "runner_status": runner_status,
            "tests_executed": total if runner_completed else 0,
            "tests_passed": passed if runner_completed else 0,
            "tests_failed": total - passed if runner_completed else 0,
            "failed_test_names": failed_tests or [],
            "runner_message": runner_message or None,
        },
        "feedback": feedback,
    }


def write_result(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"score={result['score'] if result['score'] is not None else 'null'}\n")
            output.write(f"status={result['status']}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera resultado JSON do benchmark Muralha.")
    parser.add_argument("--passed-count", type=int, required=True)
    parser.add_argument("--total-count", type=int, required=True)
    parser.add_argument("--failed-test", action="append", default=[])
    parser.add_argument("--runner-status", choices=["completed", "not_configured", "error", "timeout"],
                        default="completed")
    parser.add_argument("--runner-message", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_result(args.passed_count, args.total_count, args.failed_test,
                          args.runner_status, args.runner_message)
    write_result(result, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
