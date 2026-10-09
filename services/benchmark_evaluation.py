from __future__ import annotations

import json
from typing import Any

from services.model_stability import STABILITY_ELIGIBLE_STATUSES


BENCHMARK_VERSION = "V1"

# The count range is intentionally kept separate from the human-readable
# benchmark document. Boundary semantics are shown with every result and can
# be promoted to machine checks after human review.
BENCHMARKS: list[dict[str, Any]] = [
    {"id": "B01", "kp_id": "KP_2.2.1.8", "name": "双壁钢围堰施工要求", "min": 1, "max": 1, "risk": "嵌套编号误拆", "boundary": "全文应作为一个连续施工模块；不得按浮运定位下的①～⑦或施工阶段拆分。"},
    {"id": "B02", "kp_id": "KP_2.2.2.2", "name": "钻孔灌注桩基础", "min": 6, "max": 7, "risk": "顶层过并、下层过拆", "boundary": "泥浆护壁、干作业、清孔、钢筋笼、混凝土灌注必须分开；准备/流程与成孔方式可合并。"},
    {"id": "B03", "kp_id": "KP_2.7.2.2", "name": "钻孔灌注桩施工质量控制", "min": 3, "max": 3, "risk": "同级编号误拆、异常处置独立", "boundary": "成孔控制、灌注与桩身质量控制、成孔成桩检验三部分；灌注中断处理归入灌注控制。"},
    {"id": "B04", "kp_id": "KP_2.7.2.8", "name": "钢管混凝土浇筑施工质量控制", "min": 2, "max": 3, "risk": "不同结构对象过并", "boundary": "钢管柱与钢管拱必须分开；基本要求可并入前一模块或独立。"},
    {"id": "B05", "kp_id": "KP_2.1.1.2", "name": "桥梁的主要类型", "min": 2, "max": 2, "risk": "分类维度误拆", "boundary": "城市桥梁主要类型与其他分类标准分开；其他分类维度不得各自拆分。"},
    {"id": "B06", "kp_id": "KP_2.4.3.2", "name": "钢梁安装技术要求", "min": 5, "max": 5, "risk": "全过程过并", "boundary": "安装方法、安装前准备、安装连接、落梁就位、现场涂装五个模块均应分开。"},
    {"id": "B07", "kp_id": "KP_2.5.1.4", "name": "伸缩装置安装技术", "min": 3, "max": 3, "risk": "前言误拆、步骤误拆", "boundary": "性能要求、储存、施工安装分别成模块；安装步骤不得继续拆分。"},
    {"id": "B08", "kp_id": "KP_2.6.2.2", "name": "工艺流程与施工技术要点", "min": 1, "max": 1, "risk": "连续流程误拆", "boundary": "检查、启动、挖土、顶进、监控属于同一套连续顶进工艺。"},
    {"id": "B09", "kp_id": "KP_2.1.2.3", "name": "混凝土施工技术", "min": 5, "max": 5, "risk": "稳定拆分对照", "boundary": "一般要求、原材料、配合比、施工、检验评定五个主题分别成模块。"},
    {"id": "B10", "kp_id": "KP_2.7.2.4", "name": "预应力张拉施工质量控制", "min": 1, "max": 1, "risk": "稳定合并对照", "boundary": "下料安装、张拉锚固、压浆封锚属于同一连续质量控制任务。"},
]


def _final(run: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(run.get("final_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _latest_runs(runs: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    selected = [
        run for run in runs
        if (run.get("batch_label") or "未标记") == label
        and run.get("status") in STABILITY_ELIGIBLE_STATUSES
        and run.get("final_json")
    ]
    latest: dict[str, dict[str, Any]] = {}
    for run in selected:
        key = run.get("kp_id") or run.get("kp_name") or ""
        old = latest.get(key)
        if old is None or (run.get("created_at") or "") >= (old.get("created_at") or ""):
            latest[key] = run
    return latest


def build_benchmark_report(runs: list[dict[str, Any]], label: str) -> dict[str, Any]:
    latest = _latest_runs(runs, label)
    results: list[dict[str, Any]] = []
    for item in BENCHMARKS:
        run = latest.get(item["kp_id"])
        if not run:
            results.append({**item, "status": "未覆盖", "actual_count": None, "run_id": None, "model_name": None, "prompt_version": None, "titles": []})
            continue
        final = _final(run)
        units = sorted(final.get("knowledge_units", []), key=lambda x: x.get("order_index", 0))
        count = len(units)
        if count < item["min"]:
            status = "过度合并"
        elif count > item["max"]:
            status = "过度拆分"
        else:
            status = "数量通过"
        results.append({
            **item,
            "status": status,
            "actual_count": count,
            "run_id": run.get("run_id"),
            "model_name": run.get("model_name"),
            "prompt_version": run.get("prompt_version"),
            "titles": [unit.get("title", "") for unit in units],
            "boundary_review": "请结合基准中的必须/禁止边界复核标题和起止块；当前自动判定依据为 KU 数量范围。",
        })
    counts = {status: sum(row["status"] == status for row in results) for status in ("数量通过", "过度拆分", "过度合并", "未覆盖")}
    covered = len(results) - counts["未覆盖"]
    passed = counts["数量通过"]
    if covered == 0:
        conclusion = "该标签尚未覆盖任何基准知识点。"
    elif passed == covered:
        conclusion = "所有已覆盖基准知识点的 KU 数量均在允许范围内；请继续查看每项的边界提醒。"
    else:
        conclusion = f"已覆盖 {covered} 个基准知识点，其中 {passed} 个数量通过；存在过度拆分或过度合并。"
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "label": label,
        "total": len(results),
        "covered": covered,
        "passed": passed,
        "counts": counts,
        "conclusion": conclusion,
        "results": results,
    }


def render_benchmark_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 知识单元拆分基准评测报告", "",
        f"- 基准版本：{report['benchmark_version']}",
        f"- 实验标签：{report['label']}",
        f"- 基准覆盖：{report['covered']} / {report['total']}",
        f"- 数量通过：{report['passed']}",
        "", "## 总体结论", report["conclusion"], "",
        "## 评测明细", "| 编号 | 知识点 | 实际 KU | 基准范围 | 结果 | 风险 |", "|---|---|---:|---:|---|---|",
    ]
    for row in report["results"]:
        expected = str(row["min"]) if row["min"] == row["max"] else f"{row['min']}～{row['max']}"
        actual = "—" if row["actual_count"] is None else str(row["actual_count"])
        lines.append(f"| {row['id']} | {row['name']} | {actual} | {expected} | {row['status']} | {row['risk']} |")
        if row.get("titles"):
            lines.append(f"|  | 实际标题 |  |  |  | {'；'.join(row['titles'])} |")
    lines.extend(["", "## 边界复核提醒"])
    for row in report["results"]:
        lines.append(f"- **{row['id']} {row['name']}**：{row['boundary']}")
    return "\n".join(lines)
