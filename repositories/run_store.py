from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app.db"


class RunStore:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_run (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    kp_id TEXT NOT NULL,
                    kp_name TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model_name TEXT,
                    prompt_version TEXT,
                    status TEXT NOT NULL,
                    input_json TEXT,
                    raw_response TEXT,
                    parsed_json TEXT,
                    validation_json TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_run(
        self,
        *,
        run_id: str,
        kp_id: str,
        kp_name: str,
        stage: str,
        mode: str,
        status: str,
        prompt_version: str,
        model_name: str | None = None,
        input_payload: Any = None,
        raw_response: str | None = None,
        parsed_payload: Any = None,
        validation_payload: Any = None,
    ) -> None:
        def dumps(x):
            if x is None:
                return None
            if hasattr(x, "model_dump"):
                x = x.model_dump()
            return json.dumps(x, ensure_ascii=False, indent=2)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experiment_run(
                    run_id,kp_id,kp_name,stage,mode,model_name,prompt_version,status,
                    input_json,raw_response,parsed_json,validation_json,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    kp_id,
                    kp_name,
                    stage,
                    mode,
                    model_name,
                    prompt_version,
                    status,
                    dumps(input_payload),
                    raw_response,
                    dumps(parsed_payload),
                    dumps(validation_payload),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            conn.commit()

    def list_runs(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM experiment_run ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
