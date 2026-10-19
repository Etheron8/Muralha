from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera resultado JSON do benchmark Muralha.")
    parser.add_argument("--passed-count", type=int, required=True)
    parser.add_argument("--total-count", type=int, required=True)
    parser.add_argument("--failed-test", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    valid_counts = args.total_count > 0 and 0 <= args.passed_count <= args.total_count
    passed_count = args.passed_count if valid_counts else 0
    total_count = args.total_count if args.total_count > 0 else 1
    score = round(100 * passed_count / total_count) if valid_counts else 0
    passed = valid_counts and passed_count == total_count
    result = {
        "schema_version": "1.0",
        "benchmark_id": "muralha-baseline-v1",
        "challenge_id": "authorization-bypass",
        "pull_request_number": os.getenv("PR_NUMBER"),
        "candidate_commit": os.getenv("HEAD_SHA"),
        "score": score,
        "score_max": 100,
        "status": "passed" if passed else "failed",
        "evaluation": {
            "type": "functional-tests",
            "tests_executed": total_count,
            "tests_passed": passed_count,
            "tests_failed": total_count - passed_count,
            "failed_test_names": args.failed_test,
        },
        "feedback": (
            "Todos os testes de comportamento passaram."
            if passed
            else f"{passed_count}/{total_count} testes passaram. Consulte os nomes de testes que falharam."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"score={score}\n")
            output.write(f"status={result['status']}\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
