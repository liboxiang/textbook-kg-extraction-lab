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
from services.source_segmenter import segment_source_text, render_blocks_for_prompt
from services.payload_builders import build_stage1_input, build_stage2_input
from services.coverage_validator import validate_and_resolve_stage1
from services.stage2_validator import validate_and_build_final
from services.prompt_loader import (
    list_prompt_versions,
    load_prompt,
    prompt_widget_key,
    sync_prompt_selection,
)
from services.task_bridge import create_codex_task, load_codex_result
from services.llm_client import OpenAICompatibleClient
from services.json_utils import extract_json_object
from services.report_renderer import render_html_report
from services.experiment_checkpoint import (
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
)
from repositories.run_store import RunStore

st.set_page_config(page_title="教材知识单元 AI 抽取实验台", layout="wide")
store = RunStore()

DEFAULT_STAGE1_PROMPT_VERSION = "v1.4"


def persist_current_experiment() -> None:
    save_checkpoint(st.session_state)


def new_run_id() -> str:
    return f"RUN_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"


def load_example_kp() -> dict:
    """Load the newest task KP as the editable example on a fresh app session."""
    pending_root = ROOT / ".kg_tasks" / "pending"
    candidates = []
    if pending_root.exists():
        for task_dir in pending_root.iterdir():
            input_path = task_dir / "input.json"
            if input_path.is_file():
                try:
                    payload = json.loads(input_path.read_text(encoding="utf-8"))
                    kp = payload.get("knowledge_point")
                    if kp and kp.get("kp_id") and kp.get("kp_name") and kp.get("source_text"):
                        candidates.append((task_dir.stat().st_mtime, kp))
                except (OSError, json.JSONDecodeError):
                    continue
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return {"kp_id": "", "kp_name": "", "source_text": "", "page_start": None, "page_end": None}


def initialize_example_kp() -> None:
    """Prefill the form once; Streamlit reruns will preserve later edits."""
    example = load_example_kp()
    for key in ("kp_id", "kp_name", "source_text", "page_start", "page_end"):
        value = example.get(key)
        if key in ("page_start", "page_end") and value is None:
            value = 0
        st.session_state.setdefault(key, value)


def current_kp() -> KnowledgePointInput:
    return KnowledgePointInput(
        kp_id=st.session_state.get("kp_id", "").strip(),
        kp_name=st.session_state.get("kp_name", "").strip(),
        source_text=st.session_state.get("source_text", ""),
        page_start=st.session_state.get("page_start") or None,
        page_end=st.session_state.get("page_end") or None,
    )


def ensure_kp(kp: KnowledgePointInput) -> bool:
    if not kp.kp_id or not kp.kp_name or not kp.source_text.strip():
        st.error("请先填写 KP ID、KP 名称和完整原文。")
        return False
    return True


def parse_stage1(raw: str, kp: KnowledgePointInput):
    data = extract_json_object(raw)
    llm_result = Stage1LLMResult.model_validate(data)
    blocks = segment_source_text(kp.source_text)
    resolved = validate_and_resolve_stage1(kp, blocks, llm_result)
    return llm_result, resolved


def parse_stage2(raw: str, kp: KnowledgePointInput, stage1):
    data = extract_json_object(raw)
    llm_result = Stage2LLMResult.model_validate(data)
    final = validate_and_build_final(kp, stage1, llm_result)
    return llm_result, final


st.title("教材知识单元 AI 抽取实验台")
st.caption("V1.0：KP → KU完整划分 → Coverage校验 → 人工确认 → KU属性/内容要素抽取")
restored_checkpoint = load_checkpoint()
for checkpoint_key, checkpoint_value in restored_checkpoint.items():
    st.session_state.setdefault(checkpoint_key, checkpoint_value)
initialize_example_kp()
if restored_checkpoint:
    st.caption("已自动恢复最近一次实验进度；你可以从上次状态继续。")
else:
    st.caption("已自动载入最近一次任务中的 KP 作为示例；你可以直接修改后重复运行。")

with st.sidebar:
    st.header("运行模式")
    mode = st.radio(
        "选择模型调用方式",
        ["模式A｜Codex Workspace", "模式B｜API自动调用"],
        help="模式A不需要API Key：应用生成待办任务，你让当前Codex处理并写回结果。模式B由程序直接调用OpenAI-compatible API。",
    )
    if mode.startswith("模式B"):
        st.subheader("API 设置")
        api_base = st.text_input("Base URL", value=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
        api_key = st.text_input("API Key", value=os.getenv("LLM_API_KEY", ""), type="password")
        api_model = st.text_input("Model", value=os.getenv("LLM_MODEL", ""))
        api_temperature = st.slider("Temperature", 0.0, 1.0, float(os.getenv("LLM_TEMPERATURE", "0.1")), 0.05)
    else:
        st.info("模式A使用当前 Codex 会话完成语义抽取。应用按钮不会直接消耗API额度；需要在Codex里执行一次“处理最新任务”。")

page_exp, page_hist, page_prompt = st.tabs(["单 KP 实验", "历史运行", "Prompt 管理"])

with page_exp:
    left, right = st.columns([1, 1])
    with left:
        st.subheader("1. 输入 Knowledge Point")
        st.text_input("KP ID", key="kp_id", placeholder="例如：KP_SZ_001")
        st.text_input("KP 名称", key="kp_name", placeholder="例如：模板拆除")
        p1, p2 = st.columns(2)
        with p1:
            st.number_input("起始页码", min_value=0, step=1, key="page_start")
        with p2:
            st.number_input("结束页码", min_value=0, step=1, key="page_end")
        st.text_area("KP 完整原文", height=360, key="source_text", placeholder="粘贴一个完整知识点的教材原文。")

    with right:
        st.subheader("2. Prompt 与 Source Block")
        split_versions = list_prompt_versions("ku_split")
        split_ver = sync_prompt_selection(
            st.session_state,
            "split_prompt_version",
            "_split_prompt_default_applied",
            split_versions,
            DEFAULT_STAGE1_PROMPT_VERSION,
        )
        if split_ver is None:
            st.error("未找到 Stage 1 Prompt 版本。")
            st.stop()
        split_ver = st.selectbox(
            "Prompt A｜KU划分",
            split_versions,
            key="split_prompt_version",
        )
        split_prompt = load_prompt("ku_split", split_ver)
        split_prompt_runtime = st.text_area(
            "Prompt A 内容（本次可临时修改）",
            value=split_prompt,
            height=240,
            key=prompt_widget_key("split_prompt_runtime", "ku_split", split_ver),
        )

        if st.session_state.get("source_text"):
            blocks_preview = segment_source_text(st.session_state["source_text"])
            st.metric("Source Block 数量", len(blocks_preview))
            with st.expander("查看 Source Block（仅技术定位，不是KU）"):
                st.code(render_blocks_for_prompt(blocks_preview), language="text")

    st.divider()
    st.subheader("阶段 1｜KP → KU 完整划分")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        run_stage1 = st.button("开始 KU 划分", type="primary", use_container_width=True)
    with c2:
        clear_current = st.button("清空当前结果", use_container_width=True)

    if clear_current:
        for k in [
            "stage1_task_dir", "stage1_llm", "stage1_resolved", "stage1_editor",
            "stage1_confirmed", "stage2_task_dir", "stage2_llm", "final_result",
            "current_run_id", "stage2_run_id",
        ]:
            st.session_state.pop(k, None)
        clear_checkpoint()
        st.rerun()

    if run_stage1:
        kp = current_kp()
        if ensure_kp(kp):
            blocks = segment_source_text(kp.source_text)
            payload = build_stage1_input(kp, blocks)
            run_id = new_run_id()
            try:
                if mode.startswith("模式A"):
                    task_dir = create_codex_task("STAGE1", run_id, split_prompt_runtime, payload)
                    st.session_state["stage1_task_dir"] = str(task_dir)
                    st.session_state["current_run_id"] = run_id
                    persist_current_experiment()
                    store.save_run(
                        run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name,
                        stage="STAGE1", mode="CODEX", status="PENDING",
                        prompt_version=split_ver, input_payload=payload,
                    )
                    st.success("已生成 Codex 待办任务。")
                else:
                    client = OpenAICompatibleClient(base_url=api_base, api_key=api_key, model=api_model)
                    raw = client.generate(split_prompt_runtime, json.dumps(payload, ensure_ascii=False), api_temperature)
                    llm, resolved = parse_stage1(raw, kp)
                    st.session_state["stage1_llm"] = llm.model_dump()
                    st.session_state["stage1_resolved"] = resolved.model_dump()
                    st.session_state["stage1_editor"] = json.dumps(llm.model_dump(), ensure_ascii=False, indent=2)
                    st.session_state["current_run_id"] = run_id
                    persist_current_experiment()
                    store.save_run(
                        run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name,
                        stage="STAGE1", mode="API", status=resolved.validation.status,
                        prompt_version=split_ver, model_name=api_model, input_payload=payload,
                        raw_response=raw, parsed_payload=llm, validation_payload=resolved.validation,
                    )
            except Exception as e:
                st.exception(e)

    if st.session_state.get("stage1_task_dir"):
        task_dir = Path(st.session_state["stage1_task_dir"])
        st.info(
            "模式A下一步：在当前 Codex 对话输入 **“处理最新任务”**。Codex 会按仓库 AGENTS.md 处理并写入 result.json。完成后回这里点击“加载 Codex 结果”。"
        )
        st.code(str(task_dir), language="text")
        if st.button("加载 Codex Stage 1 结果"):
            kp = current_kp()
            raw = load_codex_result(task_dir)
            if not raw:
                st.warning("还没有 result.json。请先让 Codex 处理任务。")
            else:
                try:
                    llm, resolved = parse_stage1(raw, kp)
                    st.session_state["stage1_llm"] = llm.model_dump()
                    st.session_state["stage1_resolved"] = resolved.model_dump()
                    st.session_state["stage1_editor"] = json.dumps(llm.model_dump(), ensure_ascii=False, indent=2)
                    persist_current_experiment()
                    store.save_run(
                        run_id=st.session_state.get("current_run_id", new_run_id()),
                        kp_id=kp.kp_id, kp_name=kp.kp_name,
                        stage="STAGE1", mode="CODEX", status=resolved.validation.status,
                        prompt_version=split_ver, input_payload=json.loads((task_dir/"input.json").read_text(encoding="utf-8")),
                        raw_response=raw, parsed_payload=llm, validation_payload=resolved.validation,
                    )
                    st.success("Codex Stage 1 结果已加载。")
                except Exception as e:
                    st.exception(e)

    if st.session_state.get("stage1_resolved"):
        from schemas.models import Stage1ResolvedResult
        resolved = Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"])
        v = resolved.validation
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("KU 数量", len(resolved.knowledge_units))
        m2.metric("Coverage", f"{v.coverage_rate:.0%}")
        m3.metric("Gap", v.gap_count)
        m4.metric("Overlap", v.overlap_count)
        if v.status == "PASS":
            st.success("Coverage Validator：PASS。KU 原文可按顺序精确还原 KP 原文。")
        else:
            st.error("Coverage Validator：FAIL")
            for err in v.errors:
                st.write(f"- {err}")

        for ku in resolved.knowledge_units:
            with st.expander(f"KU {ku.order_index:02d}｜{ku.title}", expanded=True):
                st.write(f"**主问题：** {ku.main_question}")
                st.write(f"**原文范围：** {ku.start_block_id} → {ku.end_block_id}")
                st.text_area("KU 原文（程序从KP原文精确截取）", ku.source_text, height=160, disabled=True, key=f"src_{ku.temp_ku_id}")

        st.markdown("#### 人工修正（实验期）")
        st.caption("可直接修改 Stage 1 JSON 的 KU 边界/标题/主问题，再由程序重新做 Coverage 校验。")
        edited = st.text_area(
            "Stage 1 JSON",
            value=st.session_state.get("stage1_editor", ""),
            height=300,
            key="stage1_editor_widget",
        )
        if st.button("应用人工修改并重新校验"):
            try:
                kp = current_kp()
                llm = Stage1LLMResult.model_validate(json.loads(edited))
                blocks = segment_source_text(kp.source_text)
                resolved2 = validate_and_resolve_stage1(kp, blocks, llm)
                st.session_state["stage1_llm"] = llm.model_dump()
                st.session_state["stage1_resolved"] = resolved2.model_dump()
                st.session_state["stage1_editor"] = edited
                st.session_state["stage1_confirmed"] = False
                persist_current_experiment()
                st.rerun()
            except Exception as e:
                st.exception(e)

        if st.button("确认 KU 划分", disabled=(v.status != "PASS"), type="primary"):
            st.session_state["stage1_confirmed"] = True
            persist_current_experiment()
            st.success("KU 划分已确认，可以进入阶段 2。")

    st.divider()
    st.subheader("阶段 2｜KU → 属性与内容要素")
    extract_versions = list_prompt_versions("ku_extract")
    extract_ver = sync_prompt_selection(
        st.session_state,
        "extract_prompt_version",
        "_extract_prompt_default_applied",
        extract_versions,
    )
    if extract_ver is None:
        st.error("未找到 Stage 2 Prompt 版本。")
        st.stop()
    extract_ver = st.selectbox(
        "Prompt B｜属性抽取",
        extract_versions,
        key="extract_prompt_version",
    )
    extract_prompt = load_prompt("ku_extract", extract_ver)
    extract_prompt_runtime = st.text_area(
        "Prompt B 内容（本次可临时修改）",
        value=extract_prompt,
        height=220,
        key=prompt_widget_key("extract_prompt_runtime", "ku_extract", extract_ver),
    )

    stage2_disabled = not st.session_state.get("stage1_confirmed", False)
    if st.button("开始属性抽取", disabled=stage2_disabled, type="primary"):
        try:
            from schemas.models import Stage1ResolvedResult
            kp = current_kp()
            stage1 = Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"])
            payload2 = build_stage2_input(stage1)
            run_id = new_run_id()
            if mode.startswith("模式A"):
                task_dir2 = create_codex_task("STAGE2", run_id, extract_prompt_runtime, payload2)
                st.session_state["stage2_task_dir"] = str(task_dir2)
                st.session_state["stage2_run_id"] = run_id
                persist_current_experiment()
                store.save_run(
                    run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name,
                    stage="STAGE2", mode="CODEX", status="PENDING",
                    prompt_version=extract_ver, input_payload=payload2,
                )
                st.success("已生成 Codex Stage 2 待办任务。")
            else:
                client = OpenAICompatibleClient(base_url=api_base, api_key=api_key, model=api_model)
                raw2 = client.generate(extract_prompt_runtime, json.dumps(payload2, ensure_ascii=False), api_temperature)
                llm2, final = parse_stage2(raw2, kp, stage1)
                st.session_state["stage2_llm"] = llm2.model_dump()
                st.session_state["final_result"] = final.model_dump()
                persist_current_experiment()
                store.save_run(
                    run_id=run_id, kp_id=kp.kp_id, kp_name=kp.kp_name,
                    stage="STAGE2", mode="API", status="PASS", prompt_version=extract_ver,
                    model_name=api_model, input_payload=payload2, raw_response=raw2,
                    parsed_payload=llm2, validation_payload={"status":"PASS"},
                )
        except Exception as e:
            st.exception(e)

    if st.session_state.get("stage2_task_dir"):
        task_dir2 = Path(st.session_state["stage2_task_dir"])
        st.info("在 Codex 中再次输入 **“处理最新任务”**，完成后点击下面按钮。")
        st.code(str(task_dir2), language="text")
        if st.button("加载 Codex Stage 2 结果"):
            raw2 = load_codex_result(task_dir2)
            if not raw2:
                st.warning("还没有 result.json。")
            else:
                try:
                    from schemas.models import Stage1ResolvedResult
                    kp = current_kp()
                    stage1 = Stage1ResolvedResult.model_validate(st.session_state["stage1_resolved"])
                    llm2, final = parse_stage2(raw2, kp, stage1)
                    st.session_state["stage2_llm"] = llm2.model_dump()
                    st.session_state["final_result"] = final.model_dump()
                    persist_current_experiment()
                    store.save_run(
                        run_id=st.session_state.get("stage2_run_id", new_run_id()),
                        kp_id=kp.kp_id, kp_name=kp.kp_name,
                        stage="STAGE2", mode="CODEX", status="PASS", prompt_version=extract_ver,
                        input_payload=json.loads((task_dir2/"input.json").read_text(encoding="utf-8")),
                        raw_response=raw2, parsed_payload=llm2, validation_payload={"status":"PASS"},
                    )
                    st.success("Codex Stage 2 结果已加载。")
                except Exception as e:
                    st.exception(e)

    if st.session_state.get("final_result"):
        from schemas.models import FinalExtraction
        final = FinalExtraction.model_validate(st.session_state["final_result"])
        st.markdown("### 最终结构化结果")
        st.markdown("### 交互式实体—关系—属性图")
        components.html(render_html_report(final), height=900, scrolling=True)
        for ku in final.knowledge_units:
            with st.expander(f"{ku.ku_id}｜{ku.title}", expanded=True):
                st.write(f"**主问题：** {ku.main_question}")
                st.write(f"**知识对象：** {ku.knowledge_object}")
                st.write(f"**核心结论：** {ku.core_conclusion}")
                knowledge_type_label = ku.knowledge_type_name or ku.knowledge_type
                st.write(f"**知识类型：** {knowledge_type_label}（{ku.knowledge_type}）")
                if ku.content_elements:
                    st.dataframe([ce.model_dump() for ce in ku.content_elements], use_container_width=True)
                st.text_area("原文", ku.source_text, height=160, disabled=True, key=f"final_{ku.ku_id}")

        json_bytes = json.dumps(final.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
        html = render_html_report(final).encode("utf-8")
        d1, d2 = st.columns(2)
        d1.download_button("导出最终 JSON", json_bytes, file_name=f"{final.kp.kp_id}_result.json", mime="application/json", use_container_width=True)
        d2.download_button("导出 HTML 报告", html, file_name=f"{final.kp.kp_id}_report.html", mime="text/html", use_container_width=True)

with page_hist:
    st.subheader("历史运行")
    rows = store.list_runs(200)
    if rows:
        display = [
            {
                "run_id": r["run_id"], "kp_id": r["kp_id"], "kp_name": r["kp_name"],
                "stage": r["stage"], "mode": r["mode"], "model": r["model_name"],
                "prompt": r["prompt_version"], "status": r["status"], "created_at": r["created_at"]
            }
            for r in rows
        ]
        st.dataframe(display, use_container_width=True)
    else:
        st.info("暂无运行记录。")

with page_prompt:
    st.subheader("Prompt 管理")
    st.caption("V1.0 提供文件化 Prompt。实验时可在单KP页面临时编辑；需要固化时可在这里保存成新版本。")
    kind = st.selectbox("Prompt 类型", ["ku_split", "ku_extract"], key="prompt_mgmt_kind")
    versions = list_prompt_versions(kind)
    version_key = f"prompt_mgmt_version_{kind}"
    selected = sync_prompt_selection(
        st.session_state,
        version_key,
        f"_prompt_mgmt_default_applied_{kind}",
        versions,
    )
    if selected is None:
        st.error(f"未找到 {kind} 的 Prompt 版本。")
        st.stop()
    selected = st.selectbox("现有版本", versions, key=version_key)
    content = st.text_area(
        "内容",
        load_prompt(kind, selected),
        height=500,
        key=prompt_widget_key("prompt_mgmt_content", kind, selected),
    )
    new_ver = st.text_input("保存为新版本", placeholder="例如 v1.1")
    if st.button("保存新 Prompt 版本"):
        if not new_ver.strip():
            st.error("请填写新版本号。")
        else:
            path = ROOT / "prompts" / kind / f"{new_ver.strip()}.md"
            if path.exists():
                st.error("该版本已存在，请换一个版本号。")
            else:
                path.write_text(content, encoding="utf-8")
                st.success(f"已保存：{path.relative_to(ROOT)}")
                st.rerun()
