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

from schemas.models import KnowledgePointInput, Stage1LLMResult, Stage2LLMResult
from services.coverage_validator import validate_and_resolve_stage1
from services.experiment_checkpoint import clear_checkpoint, load_checkpoint, save_checkpoint
from services.experiment_state import get_experiment_stage, reset_experiment_state
from services.json_utils import extract_json_object
from services.llm_client import OpenAICompatibleClient
from services.payload_builders import build_stage1_input, build_stage2_input
from services.prompt_loader import list_prompt_versions, load_prompt, prompt_widget_key, sync_prompt_selection
from services.report_renderer import render_html_report
from services.source_segmenter import render_blocks_for_prompt, segment_source_text
from services.stage2_validator import validate_and_build_final
from services.task_bridge import create_codex_task, load_codex_result
from repositories.run_store import RunStore

st.set_page_config(page_title="教材知识单元 AI 抽取实验台", layout="wide")
store = RunStore()
DEFAULT_STAGE1_PROMPT_VERSION = "v1.5"


def new_run_id():
    return f"RUN_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"


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
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return {"kp_id": "", "kp_name": "", "source_text": "", "page_start": 0, "page_end": 0}


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
                store.save_batch(run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name, mode="CODEX" if mode.startswith("模式A") else "API", prompt_version=selected, input_payload=payload)
                if mode.startswith("模式A"):
                    task = create_codex_task("STAGE1", run_id, prompt, payload)
                    st.session_state.update(stage1_task_dir=str(task), current_run_id=run_id)
                    persist(); st.success("已生成 Codex Stage 1 待办任务。")
                else:
                    raw = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"]).generate(prompt, json.dumps(payload, ensure_ascii=False), api["temperature"])
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
        for unit in resolved.knowledge_units:
            with st.expander(f"KU {unit.order_index:02d}｜{unit.title}", expanded=True):
                st.write(f"主问题：{unit.main_question}")
                st.write(f"原文范围：{unit.start_block_id} → {unit.end_block_id}")
                st.text_area("KU 原文", unit.source_text, height=160, disabled=True, key=f"src_{unit.temp_ku_id}")
        if st.button("确认 KU 划分", disabled=v.status != "PASS", type="primary"):
            st.session_state["stage1_confirmed"] = True; persist(); st.success("KU 划分已确认，可以进入阶段2。")


def render_stage2(mode, api):
    if not st.session_state.get("stage1_confirmed"):
        st.warning("请先在阶段1确认 KU 划分。"); return
    from schemas.models import Stage1ResolvedResult
    versions = list_prompt_versions("ku_extract")
    sync_prompt_selection(st.session_state, "extract_prompt_version", "_extract_prompt_default_applied", versions)
    selected = st.selectbox("Prompt B｜属性抽取", versions, key="extract_prompt_version")
    prompt = st.text_area("Prompt B 内容（本次可临时修改）", load_prompt("ku_extract", selected), height=260, key=prompt_widget_key("extract_prompt_runtime", "ku_extract", selected))
    if st.button("开始属性抽取", type="primary"):
        kp, stage1 = current_kp(), Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"])
        payload = build_stage2_input(stage1)
        run_id = st.session_state.get("current_run_id") or new_run_id()
        try:
            store.save_batch(run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name, mode="CODEX" if mode.startswith("模式A") else "API", prompt_version=selected, input_payload=payload)
            if mode.startswith("模式A"):
                task = create_codex_task("STAGE2", run_id, prompt, payload); store.update_batch(run_id=run_id, status="STAGE2_IN_PROGRESS", current_stage="STAGE2"); st.session_state.update(stage2_task_dir=str(task), stage2_run_id=run_id); persist(); st.success("已生成 Codex Stage 2 待办任务。")
            else:
                raw = OpenAICompatibleClient(base_url=api["base"], api_key=api["key"], model=api["model"]).generate(prompt, json.dumps(payload, ensure_ascii=False), api["temperature"])
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
    for unit in final.knowledge_units:
        with st.expander(f"{unit.ku_id}｜{unit.title}", expanded=True):
            st.write(f"主问题：{unit.main_question}")
            st.write(f"知识对象：{unit.knowledge_object}")
            st.write(f"核心结论：{unit.core_conclusion}")
            st.text_area("教材原文", unit.source_text, height=160, disabled=True, key=f"final_{unit.ku_id}")
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
    mode = st.radio("模型调用方式", ["模式A｜Codex Workspace", "模式B｜API自动调用"], key="run_mode")
    api_panel = st.empty()
    api_panel.empty()
    api = {"base": "", "key": "", "model": "", "temperature": 0.1}
    if mode == "模式B｜API自动调用":
        with api_panel.container():
            api["base"] = st.text_input("Base URL", value=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"), key="api_base_url")
            api["key"] = st.text_input("API Key", value=os.getenv("LLM_API_KEY", ""), type="password", key="api_key")
            api["model"] = st.text_input("Model", value=os.getenv("LLM_MODEL", ""), key="api_model")
            api["temperature"] = st.slider("Temperature", 0.0, 1.0, 0.1, 0.05, key="api_temperature")
    else:
        for key in ("api_base_url", "api_key", "api_model", "api_temperature"):
            st.session_state.pop(key, None)
        with api_panel.container():
            st.info("模式A使用当前 Codex 会话完成语义抽取。")
    st.divider(); st.header("功能菜单")
    section = st.radio("选择功能", ["单 KP 实验", "历史运行", "Prompt 管理"], key="app_section", label_visibility="collapsed")
    if st.button("重新开始实验", use_container_width=True): restart(); st.rerun()

main_panel = st.empty()
with main_panel.container():
    render_flow()
    if section == "单 KP 实验":
        tab1, tab2, tab3 = st.tabs(["阶段1｜KU 划分", "阶段2｜属性与内容要素", "最终结果｜图谱与导出"])
        with tab1:
            render_stage1(mode, api)
        with tab2:
            render_stage2(mode, api)
        with tab3:
            render_result()
    elif section == "历史运行":
        st.subheader("历史运行")
        rows = store.list_runs(200)
        for run in rows:
            cols = st.columns([1.3, 1.4, 1.2, 2.8, 1.2])
            cols[0].write(run["kp_id"])
            cols[1].write(run["kp_name"])
            cols[2].write(run["status"])
            cols[3].write(run.get("status_description") or run["status"])
            if run["status"] == "COMPLETED" and run.get("final_json"):
                if cols[4].button("查看图谱", key=f"graph_{run['run_id']}"):
                    show_history_graph(run)
            else:
                cols[4].write("—")
    else:
        st.subheader("Prompt 管理")
        kind = st.selectbox("Prompt 类型", ["ku_split", "ku_extract"], key="prompt_mgmt_kind")
        versions = list_prompt_versions(kind)
        version_key = f"prompt_mgmt_version_{kind}"
        sync_prompt_selection(st.session_state, version_key, f"_prompt_mgmt_default_applied_{kind}", versions)
        selected = st.selectbox("现有版本", versions, key=version_key)
        content = st.text_area("内容", load_prompt(kind, selected), height=500, key=prompt_widget_key("prompt_mgmt_content", kind, selected))
        new_ver = st.text_input("保存为新 Prompt 版本")
        if st.button("保存新 Prompt 版本"):
            path = ROOT / "prompts" / kind / f"{new_ver.strip()}.md"
            if not new_ver.strip(): st.error("请填写版本号。")
            elif path.exists(): st.error("该版本已存在。")
            else: path.write_text(content, encoding="utf-8"); st.success(f"已保存：{path.relative_to(ROOT)}")
