import json

from services.benchmark_evaluation import build_benchmark_report, render_benchmark_markdown


def _run(kp_id, label, count, created_at="2026-10-03T12:00:00"):
    final = {"knowledge_units": [{"order_index": i + 1, "title": f"KU{i + 1}"} for i in range(count)]}
    return {"kp_id": kp_id, "batch_label": label, "status": "STAGE1_ONLY", "final_json": json.dumps(final), "created_at": created_at, "model_name": "gpt-6-luna", "prompt_version": "v1.9", "run_id": f"RUN_{kp_id}"}


def test_benchmark_report_classifies_count_and_uncovered():
    report = build_benchmark_report([
        _run("KP_2.2.1.8", "label-a", 1),
        _run("KP_2.7.2.2", "label-a", 7),
    ], "label-a")
    rows = {row["kp_id"]: row for row in report["results"]}
    assert rows["KP_2.2.1.8"]["status"] == "数量通过"
    assert rows["KP_2.7.2.2"]["status"] == "过度拆分"
    assert rows["KP_2.2.2.2"]["status"] == "未覆盖"
    assert report["covered"] == 2


def test_benchmark_report_uses_latest_run_for_same_label_and_kp():
    report = build_benchmark_report([
        _run("KP_2.2.1.8", "label-a", 4, "2026-10-03T12:00:00"),
        _run("KP_2.2.1.8", "label-a", 1, "2026-10-03T13:00:00"),
    ], "label-a")
    row = next(row for row in report["results"] if row["kp_id"] == "KP_2.2.1.8")
    assert row["actual_count"] == 1
    assert row["status"] == "数量通过"


def test_benchmark_markdown_contains_summary_and_boundary_rules():
    report = build_benchmark_report([_run("KP_2.2.1.8", "label-a", 1)], "label-a")
    markdown = render_benchmark_markdown(report)
    assert "知识单元拆分基准评测报告" in markdown
    assert "B01" in markdown
    assert "边界复核提醒" in markdown
