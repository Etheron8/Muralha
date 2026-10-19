from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

UPSTREAM = "Etheron8/Muralha"
WORKFLOW_NAME = "Muralha Challenge Evaluation"
TARGET_PATH = Path("challenges/authorization-bypass/src/access_control.py")
ARTIFACT_PREFIX = "muralha-score-pr-"


class EvaluationError(RuntimeError):
    """Erro recuperável ao enviar/consultar uma avaliação remota."""


def run_command(args: list[str], *, check: bool = True, timeout: int = 60) -> str:
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError as exc:
        raise EvaluationError(f"Comando necessário não encontrado: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise EvaluationError(f"Tempo excedido executando: {args[0]}") from exc
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise EvaluationError(f"Falha em {' '.join(args[:3])}: {detail[-1500:]}")
    if not check and proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def get_fork_owner() -> str:
    return run_command(["gh", "api", "user", "--jq", ".login"])


def ensure_fork(owner: str) -> str:
    repo = f"{owner}/Muralha"
    # Tenta criar o fork; se ele já existir, a verificação abaixo o reutiliza.
    run_command(
        ["gh", "repo", "fork", UPSTREAM, "--remote=false"],
        check=False,
        timeout=120,
    )
    try:
        response = run_command(
            ["gh", "repo", "view", repo, "--json", "nameWithOwner"],
            timeout=30,
        )
    except EvaluationError as exc:
        raise EvaluationError(
            f"Não consegui localizar o fork {repo}. Confira a autenticação do gh e "
            "se a conta pode criar forks."
        ) from exc
    parsed = json.loads(response)
    return parsed["nameWithOwner"]


def find_workflow_run(head_sha: str) -> dict[str, Any] | None:
    # O SHA é hexadecimal retornado por Git, não uma expressão ou comando do usuário.
    jq = (
        f'[.workflow_runs[] | select(.name == "{WORKFLOW_NAME}" '
        f'and .head_sha == "{head_sha}")] | first // null'
    )
    raw = run_command(
        ["gh", "api", f"repos/{UPSTREAM}/actions/runs?per_page=50", "--jq", jq],
        timeout=30,
    )
    return json.loads(raw) if raw else None


def wait_for_result(head_sha: str, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    run: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        run = find_workflow_run(head_sha)
        if run and run.get("status") == "completed":
            return run
        time.sleep(5)
    raise EvaluationError(
        "A avaliação não terminou dentro do limite. Consulte os checks do PR "
        f"(commit {head_sha[:12]}) e tente baixar o artefato quando concluir."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Envia uma correção local ao Muralha e devolve o score JSON da GitHub Actions. "
            "Requer git, GitHub CLI (gh) autenticado e permissão para publicar um fork."
        )
    )
    parser.add_argument(
        "--candidate-file",
        type=Path,
        required=True,
        help="Arquivo Python corrigido por sua IA (access_control.py).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Tempo máximo de espera pela avaliação (segundos; padrão: 600).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Opcional: também grava o resultado JSON neste caminho.",
    )
    parser.add_argument(
        "--keep-pr",
        action="store_true",
        help="Mantém o PR de avaliação aberto para inspeção; por padrão, ele é fechado.",
    )
    args = parser.parse_args()

    if args.timeout < 30 or args.timeout > 3600:
        parser.error("--timeout deve ficar entre 30 e 3600 segundos.")
    candidate = args.candidate_file.expanduser().resolve()
    if not candidate.is_file():
        parser.error(f"Arquivo candidato não encontrado: {candidate}")
    try:
        candidate_text = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        parser.error(f"Não foi possível ler o arquivo como UTF-8: {exc}")
    if not candidate_text.strip() or len(candidate_text.encode("utf-8")) > 256_000:
        parser.error("O arquivo deve conter código e ter no máximo 256 KB.")

    for required in ("git", "gh"):
        if not shutil.which(required):
            raise SystemExit(f"ERRO: instale {required} antes de usar este cliente.")
    run_command(["gh", "auth", "status"], timeout=30)
    # Habilita o auxiliar de credenciais do gh para operações git autenticadas.
    run_command(["gh", "auth", "setup-git"], timeout=30)

    pr_number: int | None = None
    pr_url: str | None = None
    fork_owner = get_fork_owner()
    fork_repo = ensure_fork(fork_owner)
    branch = f"muralha/eval-{uuid.uuid4().hex[:10]}"

    with tempfile.TemporaryDirectory(prefix="muralha-client-") as temp:
        workspace = Path(temp) / "repo"
        run_command(
            ["git", "clone", f"https://github.com/{fork_repo}.git", str(workspace)],
            timeout=120,
        )
        run_command(["git", "-C", str(workspace), "config", "user.name", "Muralha Evaluation Client"])
        run_command([
            "git", "-C", str(workspace), "config", "user.email",
            f"{fork_owner}+muralha-eval@users.noreply.github.com",
        ])
        run_command([
            "git", "-C", str(workspace), "remote", "add", "upstream",
            f"https://github.com/{UPSTREAM}.git",
        ])
        run_command(["git", "-C", str(workspace), "fetch", "upstream", "main"], timeout=120)
        run_command([
            "git", "-C", str(workspace), "checkout", "-b", branch, "upstream/main",
        ])

        destination = workspace / TARGET_PATH
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(candidate_text, encoding="utf-8", newline="\n")
        run_command(["git", "-C", str(workspace), "add", str(TARGET_PATH)])
        diff = subprocess.run(
            ["git", "-C", str(workspace), "diff", "--cached", "--quiet"],
            check=False, capture_output=True, text=True,
        )
        if diff.returncode == 0:
            raise EvaluationError("O arquivo candidato é idêntico ao desafio-base; nada foi enviado.")
        if diff.returncode != 1:
            raise EvaluationError("Não foi possível validar a alteração preparada.")
        run_command([
            "git", "-C", str(workspace), "commit", "-m",
            "eval: submit local AI candidate for Muralha score",
        ])
        head_sha = run_command(["git", "-C", str(workspace), "rev-parse", "HEAD"])
        run_command(["git", "-C", str(workspace), "push", "-u", "origin", branch], timeout=120)

        body = (
            "Submissão automatizada para avaliação do benchmark público Muralha.\n\n"
            "O PR contém somente a fixture candidata. A CI usa os testes da versão-base, "
            "executa cada caso em contêiner restrito e publica um artefato JSON. "
            "Não mesclar automaticamente."
        )
        pr_url = run_command([
            "gh", "pr", "create", "--repo", UPSTREAM,
            "--base", "main", "--head", f"{fork_owner}:{branch}",
            "--title", "[Muralha evaluation] Local AI candidate",
            "--body", body,
        ], timeout=60)
        try:
            pr_number = int(pr_url.rstrip("/").split("/")[-1])
        except ValueError as exc:
            raise EvaluationError(f"Não consegui identificar o número do PR: {pr_url}") from exc

        remote_run = wait_for_result(head_sha, args.timeout)
        run_id = int(remote_run["id"])
        artifact_name = f"{ARTIFACT_PREFIX}{pr_number}"
        artifact_dir = Path(temp) / "artifact"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        run_command([
            "gh", "run", "download", str(run_id),
            "--repo", UPSTREAM, "--name", artifact_name, "--dir", str(artifact_dir),
        ], timeout=120)

        result_path = artifact_dir / "score.json"
        if not result_path.is_file():
            raise EvaluationError(
                f"A execução terminou, mas não encontrei {artifact_name}/score.json. "
                f"Verifique {remote_run.get('html_url', pr_url)}."
            )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["pull_request_url"] = pr_url
        result["workflow_run_url"] = remote_run.get("html_url")
        result["submitted_commit"] = head_sha
        if args.output:
            output_path = args.output.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")

        print(json.dumps(result, ensure_ascii=False, indent=2))

        if not args.keep_pr:
            run_command([
                "gh", "pr", "close", str(pr_number), "--repo", UPSTREAM,
                "--comment", "Avaliação concluída; PR automatizado fechado sem merge.",
            ], check=False, timeout=60)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvaluationError as exc:
        print(json.dumps({"error": "evaluation_failed", "message": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
