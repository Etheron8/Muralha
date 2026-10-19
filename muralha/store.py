from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(os.getenv("MURALHA_DB_PATH", "./data/muralha.sqlite3"))


class Store:
    def __init__(self, path: Path = DEFAULT_DB) -> None:
        self.path = path
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    benchmark_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    submission_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    challenge_id TEXT NOT NULL,
                    score INTEGER,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)

    def create_session(
        self, session_id: str, agent_name: str, provider: str | None,
        model: str | None, benchmark_id: str
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO sessions(session_id,agent_name,provider,model,benchmark_id) "
                "VALUES(?,?,?,?,?)",
                (session_id, agent_name, provider, model, benchmark_id),
            )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return dict(row) if row else None

    def add_submission(
        self, submission_id: str, session_id: str, challenge_id: str,
        score: int | None, result: dict[str, Any]
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO submissions(submission_id,session_id,challenge_id,score,result_json) "
                "VALUES(?,?,?,?,?)",
                (submission_id, session_id, challenge_id, score,
                 json.dumps(result, ensure_ascii=False)),
            )

    def session_results(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT result_json FROM submissions WHERE session_id=? ORDER BY created_at",
                (session_id,),
            ).fetchall()
        return [json.loads(row["result_json"]) for row in rows]
