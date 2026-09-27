from repositories.run_store import RunStore


def test_one_batch_row_advances_through_stages(tmp_path):
    store = RunStore(tmp_path / "runs.db")
    store.save_batch(run_id="RUN1", kp_id="KP1", kp_name="测试", mode="CODEX", prompt_version="v1", input_payload={})
    store.save_batch(run_id="RUN1", kp_id="KP1", kp_name="测试", mode="CODEX", prompt_version="v1", input_payload={})

    assert len(store.list_runs()) == 1
    assert store.list_runs()[0]["status"] == "PENDING"
    assert store.update_batch(run_id="RUN1", status="STAGE1_COMPLETED", current_stage="STAGE1")
    assert store.update_batch(run_id="RUN1", status="STAGE2_IN_PROGRESS", current_stage="STAGE2")
    assert store.update_batch(run_id="RUN1", status="COMPLETED", current_stage="STAGE2", final_payload={"ok": True})

    row = store.get_batch("RUN1")
    assert row["status"] == "COMPLETED"
    assert row["status_description"] == "最终图谱结果已生成"
    assert row["final_json"] == '{\n  "ok": true\n}'
    assert not store.update_batch(run_id="MISSING", status="FAIL", current_stage="STAGE2")
