from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_PATH = ROOT / "data" / "active_experiment.json"

CHECKPOINT_KEYS = (
    "kp_id",
    "kp_name",
    "source_text",
    "page_start",
    "page_end",
    "stage1_task_dir",
    "current_run_id",
    "stage1_llm",
    "stage1_resolved",
    "stage1_editor",
    "stage1_confirmed",
    "stage2_task_dir",
    "stage2_run_id",
    "stage2_llm",
    "final_result",
)


def load_checkpoint(path: Path = CHECKPOINT_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {key: data[key] for key in CHECKPOINT_KEYS if key in data}


def save_checkpoint(
    state: Mapping[str, Any], path: Path = CHECKPOINT_PATH
) -> None:
    payload = {key: state[key] for key in CHECKPOINT_KEYS if key in state}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_path.replace(path)


def clear_checkpoint(path: Path = CHECKPOINT_PATH) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
