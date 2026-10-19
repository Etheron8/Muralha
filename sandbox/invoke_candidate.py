"""Processo sem acesso ao gabarito; executa uma única chamada à fixture candidata."""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/candidate/src")

from access_control import can_access_document  # noqa: E402


def main() -> int:
    request = json.load(sys.stdin)
    if not isinstance(request, dict):
        return 2
    value = can_access_document(**request)
    if type(value) is not bool:
        return 3
    print(json.dumps(value, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
