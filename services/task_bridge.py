from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PENDING = ROOT / ".kg_tasks" / "pending"


def create_codex_task(
    stage: str,
    run_id: str,
    system_prompt: str,
    input_payload: dict[str, Any],
) -> Path:
    task_dir = PENDING / f"{run_id}_{stage.lower()}"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "input.json").write_text(
        json.dumps(input_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    task_md = f"""# Pending textbook KG task\n\nStage: {stage}\nRun ID: {run_id}\nCreated: {datetime.now().isoformat(timespec='seconds')}\n\n## Instructions\n\n{system_prompt}\n\n## Input\nRead `input.json` in this directory.\n\n## Required action\nPerform the task yourself using the current Codex model and repository instructions. Write only the final JSON object to `result.json`. Then run:\n\n```bash\npython scripts/validate_codex_result.py {task_dir.as_posix()}\n```\n\nDo not edit `input.json`.\n"""
    (task_dir / "task.md").write_text(task_md, encoding="utf-8")
    return task_dir


def load_codex_result(task_dir: Path) -> str | None:
    path = task_dir / "result.json"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")
