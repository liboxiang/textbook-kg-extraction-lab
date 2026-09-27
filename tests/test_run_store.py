from repositories.run_store import RunStore


def test_update_run_is_scoped_to_run_and_stage(tmp_path):
    store = RunStore(tmp_path / "runs.db")
    common = dict(kp_id="KP1", kp_name="测试", mode="CODEX", status="PENDING", prompt_version="v1")
    store.save_run(run_id="RUN1", stage="STAGE1", input_payload={}, **common)
    store.save_run(run_id="RUN1", stage="STAGE2", input_payload={}, **common)
    store.save_run(run_id="RUN2", stage="STAGE1", input_payload={}, **common)

    assert store.update_run(run_id="RUN1", stage="STAGE1", status="STAGE1_COMPLETED", parsed_payload={"ok": True})
    rows = { (row["run_id"], row["stage"]): row for row in store.list_runs() }
    assert rows[("RUN1", "STAGE1")]["status"] == "STAGE1_COMPLETED"
    assert rows[("RUN1", "STAGE2")]["status"] == "PENDING"
    assert rows[("RUN2", "STAGE1")]["status"] == "PENDING"

    assert not store.update_run(run_id="MISSING", stage="STAGE1", status="FAIL")
