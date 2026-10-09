import json

from services.model_stability import build_stability_report


def _run(label: str, status: str, end_block_id: str) -> dict:
    final = {
        "knowledge_units": [
            {
                "order_index": 1,
                "start_block_id": "S0001",
                "end_block_id": end_block_id,
            }
        ]
    }
    return {
        "kp_id": "KP_TEST",
        "kp_name": "测试知识点",
        "batch_label": label,
        "model_name": label,
        "status": status,
        "created_at": "2026-09-30T12:00:00",
        "final_json": json.dumps(final),
    }


def test_stability_report_accepts_stage1_only_runs():
    report = build_stability_report(
        [
            _run("label-a", "STAGE1_ONLY", "S0003"),
            _run("label-b", "STAGE1_ONLY", "S0003"),
        ],
        selected_labels=("label-a", "label-b"),
    )

    assert report["total"] == 1
    assert report["exact_count"] == 1


def test_stability_report_ignores_unfinished_runs():
    report = build_stability_report(
        [
            _run("label-a", "PENDING", "S0003"),
            _run("label-b", "STAGE1_ONLY", "S0003"),
        ],
        selected_labels=("label-a", "label-b"),
    )

    assert report["total"] == 0
