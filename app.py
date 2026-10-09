from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from schemas.models import FinalEvidence, FinalExtraction, FinalKU, FinalKUSplitEvidence, KnowledgePointInput, Stage1LLMResult, Stage2LLMResult
from services.coverage_validator import validate_and_resolve_stage1
from services.experiment_checkpoint import clear_checkpoint, load_checkpoint, save_checkpoint
from services.experiment_state import get_experiment_stage, reset_experiment_state
from services.json_utils import extract_json_object
from services.llm_client import OpenAICompatibleClient
from services.payload_builders import build_stage1_input, build_stage2_input
from services.prompt_loader import list_prompt_versions, load_prompt, prompt_widget_key, sync_prompt_selection
from services.report_renderer import render_html_report, render_history_overview
from services.source_segmenter import render_blocks_for_prompt, segment_source_text
from services.stage2_validator import validate_and_build_final
from services.task_bridge import create_codex_task, load_codex_result
from repositories.run_store import RunStore
from services.model_stability import STABILITY_ELIGIBLE_STATUSES, build_stability_report, render_stability_html
from services.benchmark_evaluation import build_benchmark_report, render_benchmark_markdown

st.set_page_config(page_title="教材知识单元 AI 抽取实验台", layout="wide")
store = RunStore()
DEFAULT_STAGE1_PROMPT_VERSION = "v1.6"
DEFAULT_STAGE2_PROMPT_VERSION = "v1.4"
DEFAULT_EXAMPLE_KP_ID = "KP_SZ_1.1.2"
RECOMMENDED_STAGE1_PROMPT_VERSIONS = {"v1.6", "v1.10"}


def new_run_id():
    return f"RUN_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"


def labels_by_creation_desc(runs):
    """Return distinct labels ordered by the label's first run creation time."""
    first_created = {}
    for run in runs:
        label = run.get("batch_label") or "未标记"
        created_at = run.get("created_at") or ""
        if label not in first_created or created_at < first_created[label]:
            first_created[label] = created_at
    return sorted(first_created, key=lambda label: (first_created[label], label), reverse=True)


def new_batch_id():
    return f"BATCH_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"


def persist():
    save_checkpoint(st.session_state)


def current_kp():
    return KnowledgePointInput(kp_id=st.session_state.get("kp_id", "").strip(), kp_name=st.session_state.get("kp_name", "").strip(), source_text=st.session_state.get("source_text", ""), page_start=st.session_state.get("page_start") or None, page_end=st.session_state.get("page_end") or None)


def parse_stage1(raw, kp):
    llm = Stage1LLMResult.model_validate(extract_json_object(raw))
    return llm, validate_and_resolve_stage1(kp, segment_source_text(kp.source_text), llm)


def parse_stage2(raw, kp, stage1):
    llm = Stage2LLMResult.model_validate(extract_json_object(raw))
    return llm, validate_and_build_final(kp, stage1, llm)


def restart():
    reset_experiment_state(st.session_state)
    for key in ("kp_id", "kp_name", "source_text", "page_start", "page_end"):
        st.session_state.pop(key, None)
    clear_checkpoint()


def load_example_kp():
    pending = ROOT / ".kg_tasks" / "pending"
    candidates = []
    if pending.exists():
        for task_dir in pending.iterdir():
            input_path = task_dir / "input.json"
            if not input_path.is_file():
                continue
            try:
                data = json.loads(input_path.read_text(encoding="utf-8"))
                value = data.get("knowledge_point")
                if value and value.get("kp_id") and value.get("kp_name") and value.get("source_text"):
                    candidates.append((task_dir.stat().st_mtime, value))
            except (OSError, json.JSONDecodeError):
                continue
    preferred = [item for item in candidates if item[1].get("kp_id") == DEFAULT_EXAMPLE_KP_ID]
    if preferred:
        return max(preferred, key=lambda item: item[0])[1]
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return {"kp_id": "", "kp_name": "", "source_text": "", "page_start": 0, "page_end": 0}


def parse_batch_input(raw):
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("knowledge_points", data.get("items", []))
    if not isinstance(data, list) or not data:
        raise ValueError("批量输入必须是非空 JSON 数组，或包含 knowledge_points 数组的对象")
    normalized, seen = [], set()
    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条不是对象")
        if any(not str(item.get(key, "")).strip() for key in ("kp_id", "kp_name", "source_text")):
            raise ValueError(f"第 {index} 条缺少 kp_id、kp_name 或 source_text")
        if item["kp_id"] in seen:
            raise ValueError(f"KP ID 重复：{item['kp_id']}")
        seen.add(item["kp_id"])
        normalized.append({"kp_id": item["kp_id"], "kp_name": item["kp_name"], "source_text": item["source_text"], "page_start": item.get("page_start"), "page_end": item.get("page_end")})
    return normalized


def activate_batch_item(run):
    payload = json.loads(run.get("input_json") or "{}")
    kp = payload.get("knowledge_point") or payload
    for key in ("kp_id", "kp_name", "source_text", "page_start", "page_end"):
        value = kp.get(key, 0 if key in ("page_start", "page_end") else "")
        st.session_state[key] = value or (0 if key in ("page_start", "page_end") else "")
    for key in ("stage1_llm", "stage1_resolved", "stage1_editor", "stage1_confirmed", "stage2_task_dir", "stage2_run_id", "stage2_llm", "final_result"):
        st.session_state.pop(key, None)
    st.session_state["current_run_id"] = run["run_id"]
    task_dir = ROOT / ".kg_tasks" / "pending" / f"{run['run_id']}_stage1"
    if task_dir.exists():
        st.session_state["stage1_task_dir"] = str(task_dir)
    else:
        st.session_state.pop("stage1_task_dir", None)
    st.session_state["pending_app_section"] = "单 KP 实验"
    persist()


def execute_batch(batch_id, api, split_prompt_version, extract_prompt_version, skip_stage2=False, only_run_id=None):
    """Run every unfinished KP, or one selected KP, through both API stages."""
    client = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"])
    for run in store.list_batch_items(batch_id):
        if only_run_id and run["run_id"] != only_run_id:
            continue
        if run["status"] == "COMPLETED":
            continue
        try:
            payload = json.loads(run.get("input_json") or "{}")
            kp = KnowledgePointInput.model_validate(payload.get("knowledge_point") or payload)
            store.update_batch(
                run_id=run["run_id"],
                status="STAGE1_IN_PROGRESS",
                current_stage="STAGE1",
                model_name=api["model"],
                prompt_version=split_prompt_version,
            )
            split_prompt = load_prompt("ku_split", split_prompt_version)
            raw_stage1 = client.generate(split_prompt, json.dumps(payload, ensure_ascii=False), api["temperature"], api.get("reasoning_effort"))
            stage1_llm, stage1 = parse_stage1(raw_stage1, kp)
            if stage1.validation.status != "PASS":
                raise ValueError("Stage 1 Coverage Validator 未通过")
            store.update_batch(run_id=run["run_id"], status="STAGE1_COMPLETED", current_stage="STAGE1", raw_response=raw_stage1, parsed_payload=stage1_llm, validation_payload=stage1.validation)
            if skip_stage2:
                stage1_final = FinalExtraction(
                    kp=kp,
                    knowledge_units=[
                        FinalKU(
                            ku_id=unit.temp_ku_id,
                            kp_id=kp.kp_id,
                            order_index=unit.order_index,
                            title=unit.title,
                            main_question=unit.main_question,
                            section_path=unit.section_path,
                            knowledge_object="",
                            core_conclusion="",
                            knowledge_type="",
                            start_offset=unit.start_offset,
                            end_offset=unit.end_offset,
                            start_block_id=unit.start_block_id,
                            end_block_id=unit.end_block_id,
                            source_text=unit.source_text,
                            page_start=unit.page_start,
                            page_end=unit.page_end,
                        )
                        for unit in stage1.knowledge_units
                    ],
                    stage1_validation=stage1.validation,
                    evidence=FinalEvidence(ku_split=[FinalKUSplitEvidence(ku_id=item.temp_ku_id, evidence=item.evidence) for item in stage1.evidence.ku_split]),
                )
                store.update_batch(run_id=run["run_id"], status="STAGE1_ONLY", current_stage="STAGE1", final_payload=stage1_final)
                continue
            store.update_batch(run_id=run["run_id"], status="STAGE2_IN_PROGRESS", current_stage="STAGE2")
            stage2_payload = build_stage2_input(stage1)
            extract_prompt = load_prompt("ku_extract", extract_prompt_version)
            raw_stage2 = client.generate(extract_prompt, json.dumps(stage2_payload, ensure_ascii=False), api["temperature"], api.get("reasoning_effort"))
            stage2_llm, final = parse_stage2(raw_stage2, kp, stage1)
            store.update_batch(run_id=run["run_id"], status="COMPLETED", current_stage="STAGE2", raw_response=raw_stage2, parsed_payload=stage2_llm, validation_payload=final, final_payload=final)
        except Exception as item_error:
            store.update_batch(run_id=run["run_id"], status="FAIL", current_stage="STAGE2", raw_response=str(item_error))


def render_batch_experiments(mode, api):
    st.subheader("批量知识点实验")
    st.caption("一次导入多个 KP；每个 KP 独立完成两阶段抽取，结果和图谱分别查看。")
    with st.expander("创建批次", expanded=not store.list_batches(1)):
        uploaded = st.file_uploader("上传 JSON 文件（可选）", type=["json"], key="batch_json_file")
        if uploaded:
            uploaded_stem = Path(uploaded.name).stem
            previous_auto_name = st.session_state.get("batch_name_auto_source")
            current_name = st.session_state.get("batch_name_input", "")
            if not current_name or current_name == previous_auto_name:
                st.session_state["batch_name_input"] = uploaded_stem
            st.session_state["batch_name_auto_source"] = uploaded_stem
        batch_name = st.text_input("批次名称", placeholder="例如：道路工程章节批量实验", key="batch_name_input")
        st.session_state.setdefault("batch_label_input", "v1.6-temp0-luna-2.7.3")
        batch_label = st.text_input("实验标签", placeholder="例如：v1.7-temp0", key="batch_label_input")
        st.info("创建后请在运行记录区域点击“执行跑批”；批量执行使用 API 自动完成两个阶段。")
        default_text = "[{\"kp_id\":\"KP_001\",\"kp_name\":\"示例知识点\",\"source_text\":\"请输入教材原文\"}]"
        raw = uploaded.getvalue().decode("utf-8") if uploaded else st.text_area("或粘贴 JSON", value=default_text, height=180, key="batch_json_input")
        if st.button("创建批量实验", type="primary", use_container_width=True):
            try:
                items = parse_batch_input(raw)
                batch_id = new_batch_id()
                name = batch_name.strip() or batch_id
                label = batch_label.strip() or "未标记"
                store.create_batch(batch_id=batch_id, batch_name=name, total_count=len(items), batch_label=label)
                for item in items:
                    run_id = f"{batch_id}_{item['kp_id']}"
                    kp = KnowledgePointInput.model_validate(item)
                    payload = build_stage1_input(kp, segment_source_text(kp.source_text))
                    initial_prompt_version = DEFAULT_STAGE1_PROMPT_VERSION if mode.startswith("模式A") else "待执行"
                    store.save_batch(run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name, mode="CODEX" if mode.startswith("模式A") else "API", model_name="待执行", prompt_version=initial_prompt_version, input_payload=payload, batch_id=batch_id, batch_name=name, batch_label=label)
                    if mode.startswith("模式A"):
                        create_codex_task("STAGE1", run_id, load_prompt("ku_split", DEFAULT_STAGE1_PROMPT_VERSION), payload)
                st.session_state["selected_batch_id"] = batch_id
                # Clear the selectbox widget state so a newly created batch is
                # not replaced by the previously selected batch on rerun.
                st.session_state.pop("batch_selector", None)
                st.session_state["batch_selector_epoch"] = st.session_state.get("batch_selector_epoch", 0) + 1
                st.success(f"批次已创建：{batch_id}，共 {len(items)} 个 KP")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    batches = store.list_batches(100)
    if not batches:
        st.info("还没有批量实验批次。")
        return
    options = {f"{item['batch_name']}｜{item['batch_id']}": item["batch_id"] for item in batches}
    labels = list(options)
    current = st.session_state.get("selected_batch_id")
    index = next((i for i, label in enumerate(labels) if options[label] == current), 0)
    selector_key = f"batch_selector_{st.session_state.get('batch_selector_epoch', 0)}"
    selected_label = st.selectbox("选择批次", labels, index=index, key=selector_key)
    selected_batch_id = options[selected_label]
    st.session_state["selected_batch_id"] = selected_batch_id
    batch = next(item for item in batches if item["batch_id"] == selected_batch_id)
    a, b, c, d = st.columns(4)
    a.metric("KP 总数", batch["total_count"]); b.metric("已完成", batch["completed_count"]); c.metric("失败", batch["failed_count"]); d.metric("批次状态", batch["status"])
    st.caption(f"完成进度：{batch['completed_count']} / {batch['total_count']}；使用模型：{batch['model_name']}；批次执行仅支持 API 自动调用。")
    prompt_cols = st.columns(2)
    split_versions = list_prompt_versions("ku_split")
    extract_versions = list_prompt_versions("ku_extract")
    split_prompt_version = prompt_cols[0].selectbox("Stage 1 Prompt 版本", split_versions, index=len(split_versions) - 1 if split_versions else 0, key=f"batch_split_prompt_{selected_batch_id}")
    extract_prompt_version = prompt_cols[1].selectbox("Stage 2 Prompt 版本", extract_versions, index=len(extract_versions) - 1 if extract_versions else 0, key=f"batch_extract_prompt_{selected_batch_id}")
    skip_stage2 = st.checkbox("跳过 Stage 2（仅执行 KU 划分）", value=True, key=f"batch_skip_stage2_{selected_batch_id}")
    action_cols = st.columns([1, 1, 3])
    can_execute = mode.startswith("模式B") and batch["status"] != "COMPLETED"
    if action_cols[0].button("执行跑批", type="primary", disabled=not can_execute, key=f"execute_batch_{selected_batch_id}"):
        if not api["key"] or not api["model"]:
            st.error("请先在左侧填写 API Key 和 Model。")
        else:
            with st.status("正在执行批次", expanded=True) as progress:
                execute_batch(selected_batch_id, api, split_prompt_version, extract_prompt_version, skip_stage2=skip_stage2)
                progress.update(label="批次执行完成", state="complete")
            # Re-select the batch from the database after execution. The
            # selectbox widget may still hold a previous batch id across the
            # rerun, which can make the UI jump back to an older result.
            st.session_state["selected_batch_id"] = selected_batch_id
            st.session_state.pop("batch_selector", None)
            st.session_state["batch_selector_epoch"] = st.session_state.get("batch_selector_epoch", 0) + 1
            st.rerun()
    if not mode.startswith("模式B"):
        action_cols[0].caption("切换到 API 自动调用后可执行")
    if action_cols[1].button("查看批次结果", disabled=batch["completed_count"] == 0, key=f"batch_result_{selected_batch_id}"):
        st.session_state[f"show_batch_result_{selected_batch_id}"] = True
    if st.session_state.get(f"show_batch_result_{selected_batch_id}"):
        reports = []
        for item in store.list_batch_items(selected_batch_id):
            if item["status"] in ("COMPLETED", "STAGE1_ONLY") and item.get("final_json"):
                try:
                    from schemas.models import FinalExtraction
                    reports.append((item["run_id"], FinalExtraction.model_validate(json.loads(item["final_json"])), item.get("model_name", "gpt-6-luna")))
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
        if reports:
            st.subheader("批次完成结果")
            html = render_history_overview(reports)
            components.html(html, height=900, scrolling=True)
            st.download_button("下载批次 HTML 总览", html, file_name=f"{selected_batch_id}.html", mime="text/html", key=f"download_batch_{selected_batch_id}")
    for run in store.list_batch_items(selected_batch_id):
        cols = st.columns([1.2, 2.2, 1.1, 1.5, 2.2, 1.2, 1.2, 1.2])
        cols[0].write(run["kp_id"]); cols[1].write(run["kp_name"]); cols[2].write(run["status"]); cols[3].write(run.get("model_name") or "gpt-6-luna"); cols[4].write(run.get("status_description") or "")
        if cols[5].button("单独处理", key=f"batch_open_{run['run_id']}"):
            activate_batch_item(run); st.rerun()
        if run["status"] == "FAIL" and cols[6].button("重试", key=f"batch_retry_{run['run_id']}"):
            if not mode.startswith("模式B"):
                st.warning("重试需要切换到 API 自动调用模式。")
            elif not api["key"] or not api["model"]:
                st.error("请先在左侧填写 API Key 和 Model。")
            else:
                with st.spinner(f"正在重试：{run['kp_name']}"):
                    execute_batch(selected_batch_id, api, split_prompt_version, extract_prompt_version, skip_stage2=skip_stage2, only_run_id=run["run_id"])
                st.rerun()
        if run["status"] in ("COMPLETED", "STAGE1_ONLY") and run.get("final_json") and cols[7].button("查看图谱", key=f"batch_graph_{run['run_id']}"):
            show_history_graph(run)


def initialize_example_kp():
    example = load_example_kp()
    for key in ("kp_id", "kp_name", "source_text", "page_start", "page_end"):
        st.session_state.setdefault(key, example.get(key, 0 if key in ("page_start", "page_end") else ""))


def render_flow():
    state = get_experiment_stage(st.session_state)
    current = {"输入 KP": 0, "输入完成": 0, "阶段1进行中": 1, "阶段2待执行": 2, "阶段2进行中": 3, "结果完成": 4}.get(state, 0)
    st.subheader("实验批次流程")
    for col, (num, label) in zip(st.columns(5), enumerate(["输入 KP", "阶段1：KU 划分", "人工确认", "阶段2：属性抽取", "最终结果"], 1)):
        col.metric(("✅" if num < current else "▶️" if num == current else "○") + f" {num}", label)
    st.caption(f"批次：{st.session_state.get('current_run_id', '尚未创建')} ｜ 状态：{state}")


def render_stage1(mode, api):
    left, right = st.columns([1, 1])
    with left:
        st.subheader("输入 Knowledge Point")
        st.text_input("KP ID", key="kp_id")
        st.text_input("KP 名称", key="kp_name")
        p1, p2 = st.columns(2)
        p1.number_input("起始页码", min_value=0, step=1, key="page_start")
        p2.number_input("结束页码", min_value=0, step=1, key="page_end")
        st.text_area("KP 完整原文", height=360, key="source_text")
    with right:
        versions = list_prompt_versions("ku_split")
        sync_prompt_selection(st.session_state, "split_prompt_version", "_split_prompt_default_applied", versions, DEFAULT_STAGE1_PROMPT_VERSION)
        selected = st.selectbox("Prompt A｜KU划分", versions, key="split_prompt_version")
        prompt = st.text_area("Prompt A 内容（本次可临时修改）", load_prompt("ku_split", selected), height=240, key=prompt_widget_key("split_prompt_runtime", "ku_split", selected))
        if st.session_state.get("source_text"):
            blocks = segment_source_text(st.session_state["source_text"])
            st.metric("Source Block 数量", len(blocks))
            with st.expander("查看 Source Block"):
                st.code(render_blocks_for_prompt(blocks), language="text")
    if st.button("开始 KU 划分", type="primary", use_container_width=True):
        kp = current_kp()
        if not kp.kp_id or not kp.kp_name or not kp.source_text.strip():
            st.error("请先填写 KP ID、KP 名称和完整原文。")
        else:
            payload, run_id = build_stage1_input(kp, segment_source_text(kp.source_text)), new_run_id()
            try:
                store.save_batch(run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name, mode="CODEX" if mode.startswith("模式A") else "API", model_name=api["model"] or "gpt-6-luna", prompt_version=selected, input_payload=payload)
                if mode.startswith("模式A"):
                    task = create_codex_task("STAGE1", run_id, prompt, payload)
                    st.session_state.update(stage1_task_dir=str(task), current_run_id=run_id)
                    persist(); st.success("已生成 Codex Stage 1 待办任务。")
                else:
                    if not api["base"] or not api["key"] or not api["model"]:
                        raise ValueError("请先填写 Base URL、API Key 和 Model。")
                    with st.spinner("正在调用中转站执行 Stage 1，请耐心等待…"):
                        raw = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"]).generate(prompt, json.dumps(payload, ensure_ascii=False), api["temperature"], api.get("reasoning_effort"))
                    llm, resolved = parse_stage1(raw, kp)
                    st.session_state.update(stage1_llm=llm.model_dump(), stage1_resolved=resolved.model_dump(), stage1_editor=json.dumps(llm.model_dump(), ensure_ascii=False, indent=2), current_run_id=run_id)
                    store.update_batch(run_id=run_id, status="STAGE1_COMPLETED", current_stage="STAGE1", raw_response=raw, parsed_payload=llm, validation_payload=resolved.validation)
                    persist(); st.success("Stage 1 已完成。")
            except Exception as exc:
                store.update_batch(run_id=run_id, status="FAIL", current_stage="STAGE1")
                st.exception(exc)
    if st.session_state.get("stage1_task_dir"):
        task = Path(st.session_state["stage1_task_dir"])
        st.info("请在 Codex 输入“处理最新任务”，完成后点击加载。")
        st.code(str(task))
        if st.button("加载 Codex Stage 1 结果"):
            raw = load_codex_result(task)
            if not raw: st.warning("还没有 result.json。")
            else:
                try:
                    llm, resolved = parse_stage1(raw, current_kp())
                    store.update_batch(run_id=st.session_state.get("current_run_id", ""), status="STAGE1_COMPLETED", current_stage="STAGE1", raw_response=raw, parsed_payload=llm, validation_payload=resolved.validation)
                    st.session_state.update(stage1_llm=llm.model_dump(), stage1_resolved=resolved.model_dump(), stage1_editor=json.dumps(llm.model_dump(), ensure_ascii=False, indent=2))
                    persist(); st.success("Codex Stage 1 结果已加载。")
                except Exception as exc:
                    store.update_batch(run_id=st.session_state.get("current_run_id", ""), status="FAIL", current_stage="STAGE1", raw_response=raw)
                    st.exception(exc)
    if st.session_state.get("stage1_resolved"):
        from schemas.models import Stage1ResolvedResult
        resolved = Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"])
        v = resolved.validation
        a, b, c, d = st.columns(4)
        a.metric("KU 数量", len(resolved.knowledge_units)); b.metric("Coverage", f"{v.coverage_rate:.0%}"); c.metric("Gap", v.gap_count); d.metric("Overlap", v.overlap_count)
        if v.status == "PASS": st.success("Coverage Validator：PASS")
        else: st.error("Coverage Validator：FAIL")
        ku_evidence = {item.temp_ku_id: item.evidence for item in resolved.evidence.ku_split}
        for unit in resolved.knowledge_units:
            with st.expander(f"KU {unit.order_index:02d}｜{unit.title}", expanded=True):
                st.write(f"主问题：{unit.main_question}")
                st.write(f"原文范围：{unit.start_block_id} → {unit.end_block_id}")
                st.text_area("KU 原文", unit.source_text, height=160, disabled=True, key=f"src_{unit.temp_ku_id}")
                st.markdown("**KU 拆分证据**")
                st.info(ku_evidence.get(unit.temp_ku_id, "暂无拆分证据"))
        if st.button("确认 KU 划分", disabled=v.status != "PASS", type="primary"):
            st.session_state["stage1_confirmed"] = True; persist(); st.success("KU 划分已确认，可以进入阶段2。")


def render_stage2(mode, api):
    if not st.session_state.get("stage1_confirmed"):
        st.warning("请先在阶段1确认 KU 划分。"); return
    from schemas.models import Stage1ResolvedResult
    versions = list_prompt_versions("ku_extract")
    sync_prompt_selection(st.session_state, "extract_prompt_version", "_extract_prompt_default_applied", versions, DEFAULT_STAGE2_PROMPT_VERSION)
    selected = st.selectbox("Prompt B｜属性抽取", versions, key="extract_prompt_version")
    prompt = st.text_area("Prompt B 内容（本次可临时修改）", load_prompt("ku_extract", selected), height=260, key=prompt_widget_key("extract_prompt_runtime", "ku_extract", selected))
    if st.button("开始属性抽取", type="primary"):
        kp, stage1 = current_kp(), Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"])
        payload = build_stage2_input(stage1)
        run_id = st.session_state.get("current_run_id") or new_run_id()
        try:
            store.save_batch(run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name, mode="CODEX" if mode.startswith("模式A") else "API", model_name=api["model"] or "gpt-6-luna", prompt_version=selected, input_payload=payload)
            if mode.startswith("模式A"):
                task = create_codex_task("STAGE2", run_id, prompt, payload); store.update_batch(run_id=run_id, status="STAGE2_IN_PROGRESS", current_stage="STAGE2"); st.session_state.update(stage2_task_dir=str(task), stage2_run_id=run_id); persist(); st.success("已生成 Codex Stage 2 待办任务。")
            else:
                if not api["base"] or not api["key"] or not api["model"]:
                    raise ValueError("请先填写 Base URL、API Key 和 Model。")
                with st.spinner("正在调用中转站执行 Stage 2，请耐心等待…"):
                    raw = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"]).generate(prompt, json.dumps(payload, ensure_ascii=False), api["temperature"], api.get("reasoning_effort"))
                llm, final = parse_stage2(raw, kp, stage1); store.update_batch(run_id=run_id, status="COMPLETED", current_stage="STAGE2", raw_response=raw, parsed_payload=llm, validation_payload=final, final_payload=final); st.session_state.update(stage2_llm=llm.model_dump(), final_result=final.model_dump()); persist(); st.success("Stage 2 已完成。")
        except Exception as exc:
            store.update_batch(run_id=run_id, status="FAIL", current_stage="STAGE2")
            st.exception(exc)
    if st.session_state.get("stage2_task_dir"):
        task = Path(st.session_state["stage2_task_dir"]); st.info("请在 Codex 输入“处理最新任务”，完成后点击加载。"); st.code(str(task))
        if st.button("加载 Codex Stage 2 结果"):
            raw = load_codex_result(task)
            if not raw: st.warning("还没有 result.json。")
            else:
                try:
                    stage1 = Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"]); llm, final = parse_stage2(raw, current_kp(), stage1); store.update_batch(run_id=st.session_state.get("stage2_run_id", ""), status="COMPLETED", current_stage="STAGE2", raw_response=raw, parsed_payload=llm, validation_payload=final, final_payload=final); st.session_state.update(stage2_llm=llm.model_dump(), final_result=final.model_dump()); persist(); st.success("Codex Stage 2 结果已加载。")
                except Exception as exc:
                    store.update_batch(run_id=st.session_state.get("stage2_run_id", ""), status="FAIL", current_stage="STAGE2", raw_response=raw)
                    st.exception(exc)


def render_result():
    if not st.session_state.get("final_result"):
        st.info("完成阶段2后，最终结果会显示在这里。"); return
    from schemas.models import FinalExtraction
    final = FinalExtraction.model_validate(st.session_state["final_result"])
    components.html(render_html_report(final), height=900, scrolling=True)
    ku_evidence = {item.ku_id: item.evidence for item in final.evidence.ku_split}
    element_evidence = {
        (item.ku_id, item.element_id): item.evidence
        for item in final.evidence.content_element_split
    }
    for unit in final.knowledge_units:
        with st.expander(f"{unit.ku_id}｜{unit.title}", expanded=True):
            st.write(f"主问题：{unit.main_question}")
            st.write(f"知识对象：{unit.knowledge_object}")
            st.write(f"核心结论：{unit.core_conclusion}")
            st.text_area("教材原文", unit.source_text, height=160, disabled=True, key=f"final_{unit.ku_id}")
            st.markdown("**KU 拆分证据**")
            st.info(ku_evidence.get(unit.ku_id, "暂无拆分证据"))
            if unit.content_elements:
                st.markdown("**内容要素及拆分证据**")
                for element in unit.content_elements:
                    st.write(f"**{element.name}**：{element.content}")
                    st.caption(element_evidence.get((unit.ku_id, element.element_id), "暂无拆分证据"))
    st.download_button("导出最终 JSON", json.dumps(final.model_dump(), ensure_ascii=False, indent=2), file_name=f"{final.kp.kp_id}_result.json", mime="application/json", use_container_width=True)


@st.dialog("最终图谱", width="large")
def show_history_graph(run):
    from schemas.models import FinalExtraction
    final = FinalExtraction.model_validate(json.loads(run["final_json"]))
    components.html(render_html_report(final), height=900, scrolling=True)


for key, value in load_checkpoint().items(): st.session_state.setdefault(key, value)
initialize_example_kp()
st.title("教材知识单元 AI 抽取实验台")
with st.sidebar:
    st.header("运行模式")
    mode = st.radio("模型调用方式", ["模式A｜Codex Workspace", "模式B｜API自动调用"], index=1, key="run_mode")
    api_panel = st.empty()
    api_panel.empty()
    api = {"base": "", "key": "", "model": "gpt-5.6-sol", "temperature": 0.0, "reasoning_effort": "medium"}
    if mode == "模式B｜API自动调用":
        with api_panel.container():
            api["base"] = st.text_input("Base URL", value=os.getenv("LLM_BASE_URL", "https://new-api.reg.highso.com.cn/v1"), key="api_base_url")
            api["key"] = st.text_input("API Key", value=os.getenv("LLM_API_KEY", ""), type="password", key="api_key")
            api["model"] = st.text_input("Model", value=os.getenv("LLM_MODEL", "gpt-5.6-sol"), key="api_model")
            api["temperature"] = st.slider("Temperature", 0.0, 1.0, 0.0, 0.05, key="api_temperature")
            api["reasoning_effort"] = st.selectbox("Reasoning effort", ["none", "low", "medium", "high"], index=2, key="api_reasoning_effort")
            if st.button("校验 API 配置", use_container_width=True, key="validate_api_config"):
                try:
                    message = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"]).validate_configuration()
                    st.success(message)
                except Exception as exc:
                    st.error(f"配置校验失败：{exc}")
    else:
        for key in ("api_base_url", "api_key", "api_model", "api_temperature", "api_reasoning_effort"):
            st.session_state.pop(key, None)
        with api_panel.container():
            st.info("模式A使用当前 Codex 会话完成语义抽取。")
    st.divider(); st.header("功能菜单")
    if st.session_state.pop("pending_app_section", None):
        st.session_state["app_section"] = "单 KP 实验"
    section = st.radio("选择功能", ["单 KP 实验", "批量实验", "HTML 总览", "模型稳定性评测", "基准评测", "历史评测", "历史运行", "Prompt 管理"], key="app_section", label_visibility="collapsed")
    if st.button("重新开始实验", use_container_width=True): restart(); st.rerun()

main_panel = st.empty()
with main_panel.container():
    if section == "单 KP 实验":
        tab1, tab2, tab3 = st.tabs(["阶段1｜KU 划分", "阶段2｜属性与内容要素", "最终结果｜图谱与导出"])
        with tab1:
            render_stage1(mode, api)
        with tab2:
            render_stage2(mode, api)
        with tab3:
            render_result()
    elif section == "批量实验":
        render_batch_experiments(mode, api)
    elif section == "HTML 总览":
        st.subheader("历史完成结果 HTML 总览")
        rows = store.list_runs(500)
        completed_reports = []
        for run in rows:
            if run["status"] in ("COMPLETED", "STAGE1_ONLY") and run.get("final_json"):
                try:
                    from schemas.models import FinalExtraction
                    completed_reports.append((run["run_id"], FinalExtraction.model_validate(json.loads(run["final_json"])), run.get("model_name", "gpt-6-luna")))
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
        if completed_reports:
            overview_html = render_history_overview(completed_reports)
            components.html(overview_html, height=1050, scrolling=True)
            st.download_button("下载历史完成结果 HTML", overview_html, file_name="completed_history_overview.html", mime="text/html", use_container_width=True)
        else:
            st.info("暂无 COMPLETED 历史记录。")
    elif section == "模型稳定性评测":
        st.subheader("模型稳定性评测")
        st.info("评测会读取已完成的多模型结果并进行 KU 边界比较。只有点击下方按钮后才开始，避免任务未完成时提前计算。")
        evaluation_runs = store.list_runs(1000)
        available_labels = labels_by_creation_desc([
            run for run in evaluation_runs
            if run.get("status") in STABILITY_ELIGIBLE_STATUSES and run.get("final_json")
        ])
        if len(available_labels) < 2:
            st.warning("当前已完成记录中少于两个不同实验标签，暂时无法进行对比。")
            st.stop()
        m1, m2 = st.columns(2)
        label_a = m1.selectbox("实验标签 A", available_labels, key="stability_label_a")
        label_b_options = [label for label in available_labels if label != label_a]
        label_b = m2.selectbox("实验标签 B", label_b_options, key="stability_label_b")
        if st.button("开始稳定性评测", type="primary", key="start_stability_evaluation"):
            with st.spinner("正在汇总并比较不同模型的拆分结果…"):
                report = build_stability_report(evaluation_runs, selected_labels=(label_a, label_b))
                if api["key"] and api["model"]:
                    advice_payload = {
                        "labels": [label_a, label_b],
                        "total": report["total"],
                        "ku_consistent": report["exact_count"],
                        "kind_counts": report.get("kind_counts", {}),
                        "conclusion": report["conclusion"],
                        "representative_differences": [
                            {"kp_name": x["kp_name"], "count_a": x["count_a"], "count_b": x["count_b"], "kind": x["kind"], "units_a": x["units_a"], "units_b": x["units_b"]}
                            for x in report["comparisons"][:10] if x["kind"] != "KU 一致"
                        ],
                    }
                    advice_prompt = "你是教材知识单元拆分评测专家。请根据以下两个模型的 Stage 1 KU 对比结果，给出一份总体评价和统一优化建议。不要逐个知识点机械给建议；请归纳最主要的稳定性问题，并区分 Prompt 优化、流程优化和人工复核建议。输出中文，结构为：总体评价、主要问题、优化建议、建议优先级。\n\n" + json.dumps(advice_payload, ensure_ascii=False)
                    try:
                        report["ai_advice"] = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"]).generate("你负责知识抽取稳定性评测。", advice_prompt, 0.0, api.get("reasoning_effort"))
                    except Exception as exc:
                        report["ai_advice_error"] = str(exc)
                st.session_state["stability_report"] = report
                evaluation_id = store.save_stability_evaluation(label_a, label_b, report)
                st.session_state["stability_evaluation_id"] = evaluation_id
        report = st.session_state.get("stability_report")
        if not report:
            st.warning("尚未开始评测。请等待相关模型任务完成后，再点击“开始稳定性评测”。")
            st.stop()
        a, b = st.columns(2)
        a.metric("可比较知识点", report["total"])
        b.metric("KU 一致", report["exact_count"])
        st.markdown("#### 总体分析结论")
        exact_rate = report["exact_count"] / report["total"] if report["total"] else 0
        count_rate = report["count_equal"] / report["total"] if report["total"] else 0
        st.write(f"本次共比较 **{report['total']}** 个知识点，KU 一致率为 **{exact_rate:.0%}**。")
        st.info(report["conclusion"])
        if report["kind_counts"]:
            st.write("差异类型分布：" + "；".join(f"{kind} {count} 个" for kind, count in report["kind_counts"].items()) + "。")
        if report.get("ai_advice"):
            with st.expander("模型综合分析建议（点击展开）", expanded=False):
                st.markdown(report["ai_advice"])
        elif report.get("ai_advice_error"):
            st.warning(f"模型建议生成失败，已保留规则分析结果：{report['ai_advice_error']}")
        report_json = json.dumps(report, ensure_ascii=False, indent=2)
        report_md = "\n".join([
            "# 模型稳定性评测报告", "",
            f"- 可比较知识点：{report['total']}",
            f"- KU 一致：{report['exact_count']}",
            "",
            "## 总体结论", report["conclusion"], "",
            "## 统一改进建议", *[f"- {item}" for item in report["suggestions"]], "",
            "## 对比明细", "| 知识点 | 模型 A | 模型 B | KU 数量 | 评价 |", "|---|---|---|---:|---|",
            *[f"| {x['kp_name']} | {x['model_a']} | {x['model_b']} | {x['count_a']} / {x['count_b']} | {x['boundary_rate']:.0%} | {x['kind']} |" for x in report["comparisons"]],
        ])
        dl1, dl2 = st.columns(2)
        dl1.download_button("下载当前评测 JSON", report_json, file_name="model_stability_evaluation.json", mime="application/json", key="download_stability_json")
        dl2.download_button("下载当前评测 Markdown", report_md, file_name="model_stability_evaluation.md", mime="text/markdown", key="download_stability_md")
        st.download_button("下载当前评测 HTML", render_stability_html(report, label_a, label_b), file_name="model_stability_evaluation.html", mime="text/html", key="download_stability_html")
        if report["comparisons"]:
            st.markdown("#### 知识点对比明细")
            st.dataframe([
                {"知识点": x["kp_name"], "模型 A": x["model_a"], "模型 B": x["model_b"], "KU 数量": f"{x['count_a']} / {x['count_b']}", "评价": x["kind"]}
                for x in report["comparisons"]
            ], use_container_width=True, hide_index=True)
            selected = st.selectbox("查看差异知识点", [x["kp_name"] for x in report["comparisons"]], key="stability_kp")
            detail = next(x for x in report["comparisons"] if x["kp_name"] == selected)
            st.write(f"{detail.get('label_a', label_a)}：{detail['count_a']} 个 KU；{detail.get('label_b', label_b)}：{detail['count_b']} 个 KU；评价：{detail['kind']}")
            st.caption("以下为两个模型的知识图谱结果；整体改进建议以上方汇总为准。")
            if not detail.get("final_a") or not detail.get("final_b"):
                historical_runs = store.list_runs(1000)
                for candidate in historical_runs:
                    candidate_model = candidate.get("model_name") or "gpt-6-luna"
                    if candidate.get("kp_id") == detail.get("kp_key") and (candidate.get("batch_label") or "未标记") == detail.get("label_a", label_a) and candidate.get("final_json"):
                        detail["final_a"] = json.loads(candidate["final_json"])
                    if candidate.get("kp_id") == detail.get("kp_key") and (candidate.get("batch_label") or "未标记") == detail.get("label_b", label_b) and candidate.get("final_json"):
                        detail["final_b"] = json.loads(candidate["final_json"])
            if detail.get("final_a") and detail.get("final_b"):
                from schemas.models import FinalExtraction
                from services.report_renderer import render_html_report
                graph_a, graph_b = st.columns(2)
                with graph_a:
                    st.markdown(f"**标签 A｜{detail.get('label_a', label_a)}（{detail['model_a']}）**")
                    components.html(render_html_report(FinalExtraction.model_validate(detail["final_a"])), height=720, scrolling=True)
                with graph_b:
                    st.markdown(f"**标签 B｜{detail.get('label_b', label_b)}（{detail['model_b']}）**")
                    components.html(render_html_report(FinalExtraction.model_validate(detail["final_b"])), height=720, scrolling=True)
            else:
                st.info("该历史评测记录未保存完整图谱数据，仅提供文字差异对比。重新评测后即可查看并排图谱。")
        else:
            st.warning("需要同一知识点至少有两个已完成 Stage 1 的不同标签记录后才能评测。")
    elif section == "基准评测":
        st.subheader("知识单元拆分基准评测")
        st.info("选择一个实验标签，与知识单元拆分评测基准 V1 对比。评测读取历史完成结果，不会重新调用模型。")
        benchmark_doc_path = ROOT / "references" / "知识单元拆分评测基准V1.md"
        if benchmark_doc_path.exists():
            with st.expander("查看评测基准 Markdown", expanded=False):
                st.markdown(benchmark_doc_path.read_text(encoding="utf-8"))
        evaluation_runs = store.list_runs(1000)
        available_labels = labels_by_creation_desc([
            run for run in evaluation_runs
            if run.get("status") in STABILITY_ELIGIBLE_STATUSES and run.get("final_json")
        ])
        if not available_labels:
            st.warning("当前没有可用于基准评测的完成记录。")
            st.stop()
        benchmark_label = st.selectbox("实验标签", available_labels, key="benchmark_label")
        if st.button("开始基准评测", type="primary", key="start_benchmark_evaluation"):
            with st.spinner("正在将实验结果与基准逐项对比…"):
                benchmark_report = build_benchmark_report(evaluation_runs, benchmark_label)
                st.session_state["benchmark_report"] = benchmark_report
                st.session_state["benchmark_evaluation_id"] = store.save_benchmark_evaluation(benchmark_label, benchmark_report["benchmark_version"], benchmark_report)
        report = st.session_state.get("benchmark_report")
        if not report or report.get("label") != benchmark_label:
            st.warning("尚未开始评测，请选择标签后点击“开始基准评测”。")
            st.stop()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("基准覆盖", f"{report['covered']} / {report['total']}")
        m2.metric("数量通过", report["passed"])
        m3.metric("过度拆分", report["counts"]["过度拆分"])
        m4.metric("过度合并", report["counts"]["过度合并"])
        st.info(report["conclusion"])
        st.caption("当前自动判定依据为 KU 数量范围；每项下方同时展示基准边界规则，便于复核具体拆分位置。")
        table = []
        for row in report["results"]:
            expected = str(row["min"]) if row["min"] == row["max"] else f"{row['min']}～{row['max']}"
            table.append({"编号": row["id"], "知识点": row["name"], "实际 KU": row["actual_count"] if row["actual_count"] is not None else "—", "基准范围": expected, "结果": row["status"], "模型": row.get("model_name") or "—", "Prompt": row.get("prompt_version") or "—"})
        st.dataframe(table, use_container_width=True, hide_index=True)
        for row in report["results"]:
            with st.expander(f"{row['id']}｜{row['name']}｜{row['status']}", expanded=row["status"] in ("过度拆分", "过度合并")):
                st.write(f"基准范围：{row['min']}～{row['max']} KU；实际：{row['actual_count'] if row['actual_count'] is not None else '未覆盖'}")
                st.write(f"主要风险：{row['risk']}")
                st.write(f"边界规则：{row['boundary']}")
                if row.get("titles"):
                    st.write("实际 KU 标题：" + "；".join(row["titles"]))
                    st.caption(row["boundary_review"])
        report_json = json.dumps(report, ensure_ascii=False, indent=2)
        report_md = render_benchmark_markdown(report)
        d1, d2 = st.columns(2)
        d1.download_button("下载基准评测 JSON", report_json, file_name="knowledge_unit_benchmark_evaluation.json", mime="application/json", key="download_benchmark_json")
        d2.download_button("下载基准评测 Markdown", report_md, file_name="knowledge_unit_benchmark_evaluation.md", mime="text/markdown", key="download_benchmark_md")
        benchmark_history = store.list_benchmark_evaluations(50)
        if benchmark_history:
            st.markdown("#### 基准评测记录")
            history_options = {
                f"#{item['id']}｜{item['created_at']}｜{item['batch_label']}｜通过 {item['report'].get('passed', 0)}/{item['report'].get('covered', 0)}": item
                for item in benchmark_history
            }
            selected_history = st.selectbox("选择历史基准评测", list(history_options), key="benchmark_history_selector")
            history_item = history_options[selected_history]
            historical_report = history_item["report"]
            st.caption(f"记录时间：{history_item['created_at']}；标签：{history_item['batch_label']}；基准版本：{history_item['benchmark_version']}")
            hd1, hd2 = st.columns(2)
            hd1.download_button("下载历史基准 JSON", json.dumps(historical_report, ensure_ascii=False, indent=2), file_name=f"benchmark_evaluation_{history_item['id']}.json", mime="application/json", key=f"download_benchmark_history_json_{history_item['id']}")
            hd2.download_button("下载历史基准 Markdown", render_benchmark_markdown(historical_report), file_name=f"benchmark_evaluation_{history_item['id']}.md", mime="text/markdown", key=f"download_benchmark_history_md_{history_item['id']}")
    elif section == "历史评测":
        st.subheader("历史评测结果")
        history = store.list_stability_evaluations()
        if history:
            history_options = {f"#{item['id']}｜{item['created_at']}｜{item['model_a']} vs {item['model_b']}": item for item in history}
            chosen = st.selectbox("选择历史评测", list(history_options), key="stability_history_selector")
            historical = history_options[chosen]["report"]
            ha, hb = st.columns(2)
            ha.metric("可比较知识点", historical.get("total", 0))
            hb.metric("KU 一致", historical.get("exact_count", 0))
            st.markdown("#### 总体分析结论")
            total_h = historical.get("total", 0)
            st.write(f"本次共比较 **{total_h}** 个知识点。" if total_h else "暂无可比较知识点。")
            st.info(historical.get("conclusion", ""))
            if historical.get("kind_counts"):
                st.write("差异类型分布：" + "；".join(f"{kind} {count} 个" for kind, count in historical["kind_counts"].items()) + "。")
            if historical.get("ai_advice"):
                with st.expander("模型综合分析建议（点击展开）", expanded=False):
                    st.markdown(historical["ai_advice"])
            if historical.get("comparisons"):
                st.dataframe([
                    {"知识点": x["kp_name"], "模型 A": x["model_a"], "模型 B": x["model_b"], "KU 数量": f"{x['count_a']} / {x['count_b']}", "评价": x["kind"]}
                    for x in historical["comparisons"]
                ], use_container_width=True, hide_index=True)
                history_kp = st.selectbox("查看历史评测知识点", [x["kp_name"] for x in historical["comparisons"]], key=f"history_stability_kp_{history_options[chosen]['id']}")
                history_detail = next(x for x in historical["comparisons"] if x["kp_name"] == history_kp)
                runs_for_history = store.list_runs(1000)
                history_payloads = {}
                for candidate in runs_for_history:
                    candidate_model = candidate.get("model_name") or "gpt-6-luna"
                    candidate_label = candidate.get("batch_label") or "未标记"
                    if candidate.get("kp_id") == history_detail.get("kp_key") and candidate.get("final_json"):
                        if candidate_label == history_detail.get("label_a", history_detail["model_a"]):
                            history_payloads["a"] = json.loads(candidate["final_json"])
                        elif candidate_label == history_detail.get("label_b", history_detail["model_b"]):
                            history_payloads["b"] = json.loads(candidate["final_json"])
                if "a" in history_payloads and "b" in history_payloads:
                    from schemas.models import FinalExtraction
                    from services.report_renderer import render_html_report
                    st.markdown(f"**标签 A｜{history_detail.get('label_a', history_detail['model_a'])}（{history_detail.get('model_a', '')}）**")
                    components.html(render_html_report(FinalExtraction.model_validate(history_payloads["a"])), height=720, scrolling=True)
                    st.markdown(f"**标签 B｜{history_detail.get('label_b', history_detail['model_b'])}（{history_detail.get('model_b', '')}）**")
                    components.html(render_html_report(FinalExtraction.model_validate(history_payloads["b"])), height=720, scrolling=True)
            historical_json = json.dumps(historical, ensure_ascii=False, indent=2)
            st.download_button("下载历史评测 JSON", historical_json, file_name=f"stability_evaluation_{history_options[chosen]['id']}.json", mime="application/json", key=f"download_history_stability_{history_options[chosen]['id']}")
            st.download_button("下载历史评测 HTML", render_stability_html(historical, history_options[chosen]["model_a"], history_options[chosen]["model_b"]), file_name=f"stability_evaluation_v2_{history_options[chosen]['id']}.html", mime="text/html", key=f"download_history_stability_html_v2_{history_options[chosen]['id']}")
        else:
            st.caption("暂无历史评测记录。")
    elif section == "历史运行":
        st.subheader("历史运行")
        if st.button("刷新记录", key="refresh_history_runs"):
            st.rerun()
        all_rows = store.list_runs(1000)
        label_options = ["全部标签"] + labels_by_creation_desc(all_rows)
        selected_history_label = st.selectbox("按实验标签筛选", label_options, key="history_run_label_filter")
        status_options = ["全部状态", "PENDING", "STAGE1_IN_PROGRESS", "STAGE1_COMPLETED", "STAGE1_ONLY", "STAGE2_IN_PROGRESS", "COMPLETED", "FAIL"]
        selected_history_status = st.selectbox("按状态筛选", status_options, key="history_run_status_filter")
        rows = all_rows if selected_history_label == "全部标签" else [
            run for run in all_rows if (run.get("batch_label") or "未标记") == selected_history_label
        ]
        if selected_history_status != "全部状态":
            rows = [run for run in rows if run.get("status") == selected_history_status]
        page_size = st.selectbox("每页条数", [20, 50, 100, 200], index=2, key="history_run_page_size")
        total_pages = max((len(rows) + page_size - 1) // page_size, 1)
        page_number = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1, key=f"history_run_page_{selected_history_label}_{selected_history_status}")
        start = (page_number - 1) * page_size
        page_rows = rows[start:start + page_size]
        st.caption(f"共 {len(rows)} 条记录；当前第 {page_number} / {total_pages} 页")
        header = st.columns([1.1, 1.5, 1.3, 1.6, 1.0, 0.7, 1.0, 1.4, 2.1, 1.0])
        for col, label in zip(header, ["KP ID", "实验标签", "知识点", "创建时间", "状态", "KU 数量", "Stage 1 Prompt", "模型", "状态说明", "操作"]):
            col.markdown(f"**{label}**")
        for run in page_rows:
            cols = st.columns([1.1, 1.5, 1.3, 1.6, 1.0, 0.7, 1.0, 1.4, 2.1, 1.0])
            cols[0].write(run["kp_id"])
            cols[1].write(run.get("batch_label") or "未标记")
            cols[2].write(run["kp_name"])
            cols[3].write(run.get("created_at") or "—")
            cols[4].write(run["status"])
            ku_count = "—"
            if run["status"] in ("COMPLETED", "STAGE1_ONLY") and run.get("final_json"):
                try:
                    ku_count = len(json.loads(run["final_json"]).get("knowledge_units", []))
                except (TypeError, ValueError, json.JSONDecodeError):
                    ku_count = "—"
            cols[5].write(ku_count)
            cols[6].write(run.get("prompt_version") or "—")
            cols[7].write(run.get("model_name") or "gpt-6-luna")
            cols[8].write(run.get("status_description") or run["status"])
            if run["status"] in ("COMPLETED", "STAGE1_ONLY") and run.get("final_json"):
                if cols[9].button("查看图谱", key=f"graph_{run['run_id']}"):
                    show_history_graph(run)
            else:
                cols[9].write("—")
    else:
        st.subheader("Prompt 管理")
        kind = st.selectbox("Prompt 类型", ["ku_split", "ku_extract"], key="prompt_mgmt_kind")
        versions = list_prompt_versions(kind)
        version_key = f"prompt_mgmt_version_{kind}"
        sync_prompt_selection(st.session_state, version_key, f"_prompt_mgmt_default_applied_{kind}", versions)
        selected = st.selectbox(
            "现有版本",
            versions,
            key=version_key,
            format_func=lambda version: f"{version}｜推荐" if kind == "ku_split" and version in RECOMMENDED_STAGE1_PROMPT_VERSIONS else version,
        )
        if kind == "ku_split" and selected in RECOMMENDED_STAGE1_PROMPT_VERSIONS:
            st.caption("推荐版本：已通过当前项目基准样本的人工复核，适合作为后续对比起点。")
        content = st.text_area("内容", load_prompt(kind, selected), height=500, key=prompt_widget_key("prompt_mgmt_content", kind, selected))
        new_ver = st.text_input("保存为新 Prompt 版本")
        if st.button("保存新 Prompt 版本"):
            path = ROOT / "prompts" / kind / f"{new_ver.strip()}.md"
            if not new_ver.strip(): st.error("请填写版本号。")
            elif path.exists(): st.error("该版本已存在。")
            else: path.write_text(content, encoding="utf-8"); st.success(f"已保存：{path.relative_to(ROOT)}")
