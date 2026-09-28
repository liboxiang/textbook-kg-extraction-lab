from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app.db"

STATUS_DESCRIPTIONS = {
    "PENDING": "批次已创建",
    "STAGE1_COMPLETED": "阶段 1：考点拆分（KU 切分）已完成，等待确认/阶段 2",
    "STAGE2_IN_PROGRESS": "阶段 2：知识单元属性与内容要素任务已创建",
    "COMPLETED": "最终图谱结果已生成",
    "FAIL": "当前批次某一步失败",
}


class RunStore:
    def __init__(self, db_path: Path = DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _dumps(value):
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        return json.dumps(value, ensure_ascii=False, indent=2)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS experiment_run (
                id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, kp_id TEXT NOT NULL,
                kp_name TEXT NOT NULL, stage TEXT NOT NULL, mode TEXT NOT NULL, model_name TEXT,
                prompt_version TEXT, status TEXT NOT NULL, input_json TEXT, raw_response TEXT,
                parsed_json TEXT, validation_json TEXT, created_at TEXT NOT NULL,
                current_stage TEXT, status_description TEXT, final_json TEXT)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS experiment_batch (
                batch_id TEXT PRIMARY KEY, batch_name TEXT NOT NULL, total_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(experiment_run)")}
            for name in ("current_stage", "status_description", "final_json", "batch_id", "batch_name"):
                if name not in columns:
                    conn.execute(f"ALTER TABLE experiment_run ADD COLUMN {name} TEXT")
            self._deduplicate(conn)
            conn.execute("UPDATE experiment_run SET status='COMPLETED', current_stage='STAGE2', status_description=? WHERE status='PASS'", (STATUS_DESCRIPTIONS["COMPLETED"],))
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_experiment_run_run_id ON experiment_run(run_id)")
            conn.commit()

    def _deduplicate(self, conn):
        run_ids = [row[0] for row in conn.execute("SELECT DISTINCT run_id FROM experiment_run")]
        for run_id in run_ids:
            rows = conn.execute("SELECT * FROM experiment_run WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
            if len(rows) <= 1:
                continue
            chosen = max(rows, key=lambda row: (row["status"] in ("COMPLETED", "PASS"), row["id"]))
            conn.execute("DELETE FROM experiment_run WHERE run_id=?", (run_id,))
            names = ("run_id", "kp_id", "kp_name", "stage", "mode", "model_name", "prompt_version", "status", "input_json", "raw_response", "parsed_json", "validation_json", "created_at", "current_stage", "status_description", "final_json", "batch_id", "batch_name")
            conn.execute("INSERT INTO experiment_run (" + ",".join(names) + ") VALUES (" + ",".join("?" for _ in names) + ")", tuple(chosen[name] for name in names))

    def create_batch(self, *, batch_id: str, batch_name: str, total_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO experiment_batch(batch_id,batch_name,total_count,created_at) VALUES (?,?,?,?)",
                (batch_id, batch_name, total_count, datetime.now().isoformat(timespec="seconds")),
            )
            conn.commit()

    def save_batch(self, *, run_id: str, kp_id: str, kp_name: str, mode: str,
                   prompt_version: str, input_payload: Any = None,
                   model_name: str | None = None, batch_id: str | None = None,
                   batch_name: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute("""INSERT INTO experiment_run
                (run_id,kp_id,kp_name,stage,mode,model_name,prompt_version,status,input_json,created_at,current_stage,status_description,batch_id,batch_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING""",
                (run_id, kp_id, kp_name, "BATCH", mode, model_name, prompt_version, "PENDING",
                 self._dumps(input_payload), datetime.now().isoformat(timespec="seconds"), "STAGE1", STATUS_DESCRIPTIONS["PENDING"], batch_id, batch_name))
            conn.commit()

    def update_batch(self, *, run_id: str, status: str, current_stage: str,
                     raw_response: str | None = None, parsed_payload: Any = None,
                     validation_payload: Any = None, final_payload: Any = None) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("""UPDATE experiment_run SET stage='BATCH', status=?, current_stage=?, status_description=?,
                raw_response=COALESCE(?,raw_response), parsed_json=COALESCE(?,parsed_json),
                validation_json=COALESCE(?,validation_json), final_json=COALESCE(?,final_json) WHERE run_id=?""",
                (status, current_stage, STATUS_DESCRIPTIONS.get(status, status), raw_response,
                 self._dumps(parsed_payload), self._dumps(validation_payload), self._dumps(final_payload), run_id))
            conn.commit()
            return cursor.rowcount == 1

    def list_runs(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM experiment_run ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def list_batch_items(self, batch_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM experiment_run WHERE batch_id=? ORDER BY id", (batch_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def list_batches(self, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM experiment_batch ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            result = []
            for batch in rows:
                items = conn.execute("SELECT status FROM experiment_run WHERE batch_id=?", (batch["batch_id"],)).fetchall()
                counts = {}
                for item in items:
                    counts[item["status"]] = counts.get(item["status"], 0) + 1
                total = batch["total_count"]
                completed = counts.get("COMPLETED", 0)
                failed = counts.get("FAIL", 0)
                status = "COMPLETED" if completed == total and total else "FAIL" if failed else "IN_PROGRESS"
                result.append({**dict(batch), "status": status, "completed_count": completed, "failed_count": failed, "counts": counts})
        return result

    def get_batch(self, run_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM experiment_run WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def save_run(self, *, run_id: str, kp_id: str, kp_name: str, stage: str, mode: str,
                 status: str, prompt_version: str, model_name: str | None = None,
                 input_payload: Any = None, raw_response: str | None = None,
                 parsed_payload: Any = None, validation_payload: Any = None) -> None:
        self.save_batch(run_id=run_id, kp_id=kp_id, kp_name=kp_name, mode=mode,
                        prompt_version=prompt_version, input_payload=input_payload, model_name=model_name)
        if status != "PENDING":
            self.update_batch(run_id=run_id, status=status, current_stage=stage,
                              raw_response=raw_response, parsed_payload=parsed_payload,
                              validation_payload=validation_payload)
