from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CURRENT_BATCH_KEYS = (
    "stage1_task_dir",
    "stage1_llm",
    "stage1_resolved",
    "stage1_editor",
    "stage1_confirmed",
    "stage2_task_dir",
    "stage2_run_id",
    "stage2_llm",
    "final_result",
    "current_run_id",
)


def get_experiment_stage(state: Mapping[str, Any]) -> str:
    if "final_result" in state:
        return "结果完成"
    if "stage2_llm" in state or state.get("stage2_task_dir"):
        return "阶段2进行中"
    if state.get("stage1_confirmed"):
        return "阶段2待执行"
    if "stage1_resolved" in state or state.get("stage1_task_dir"):
        return "阶段1进行中"
    if state.get("kp_id") and state.get("source_text", "").strip():
        return "输入完成"
    return "输入 KP"


def reset_experiment_state(state: dict[str, Any]) -> None:
    for key in CURRENT_BATCH_KEYS:
        state.pop(key, None)
