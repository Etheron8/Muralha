from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera resultado JSON do benchmark Muralha.")
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    passed = args.exit_code == 0
    result = {
        "schema_version": "1.0",
        "benchmark_id": "muralha-baseline-v1",
        "challenge_id": "authorization-bypass",
        "pull_request_number": os.getenv("PR_NUMBER"),
        "candidate_commit": os.getenv("HEAD_SHA"),
        "score": 100 if passed else 0,
        "score_max": 100,
        "status": "passed" if passed else "failed",
        "evaluation": {
            "type": "functional-tests",
            "tests_executed": True,
            "passed": passed,
            "runner_exit_code": args.exit_code,
        },
        "feedback": (
            "Todos os testes de comportamento passaram."
            if passed
            else "A correção ainda falha em pelo menos um teste ou o executor não concluiu a execução."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"score={result['score']}\n")
            output.write(f"status={result['status']}\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
