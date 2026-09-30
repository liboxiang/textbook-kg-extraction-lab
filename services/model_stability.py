from __future__ import annotations

from collections import defaultdict
import json
from html import escape
from dataclasses import dataclass
from typing import Any


DEFAULT_MODEL = "gpt-6-luna"


def render_stability_html(report: dict[str, Any], model_a: str = "", model_b: str = "") -> str:
    advice_lines = []
    for line in str(report.get('ai_advice', '') or '').splitlines():
        text = escape(line.strip())
        if text.startswith('### '):
            advice_lines.append(f"<h4>{text[4:]}</h4>")
        elif text.startswith('## '):
            advice_lines.append(f"<h3>{text[3:]}</h3>")
        elif text.startswith('# '):
            advice_lines.append(f"<h2>{text[2:]}</h2>")
        elif text.startswith('- '):
            advice_lines.append(f"<li>{text[2:]}</li>")
        elif text:
            advice_lines.append(f"<p>{text}</p>")
    advice_html = ''.join(advice_lines) or '<p>暂无模型综合分析建议。</p>'
    raw = json.dumps(report, ensure_ascii=False, indent=2)
    rows = "".join(
        f"<tr><td>{escape(x.get('kp_name', ''))}</td><td>{escape(x.get('model_a', ''))}</td><td>{escape(x.get('model_b', ''))}</td><td>{x.get('count_a', 0)} / {x.get('count_b', 0)}</td><td>{escape(x.get('kind', ''))}</td></tr>"
        for x in report.get('comparisons', [])
    )
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>模型稳定性评测结果</title><style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:1400px;margin:24px auto;padding:0 24px;color:#1f2937;background:#f8fafc}}.panel{{background:#fff;border:1px solid #dbe3ee;border-radius:10px;padding:18px;margin:14px 0}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #dbe3ee;padding:8px;text-align:left}}th{{background:#f1f5f9}}pre{{white-space:pre-wrap;overflow:auto;background:#f8fafc;padding:14px;border-radius:8px}}.advice{{line-height:1.8}}.advice p{{margin:8px 0}}.advice li{{margin:6px 0}}</style></head><body><h1>模型稳定性评测结果</h1><p>模型 A：{escape(model_a)}　模型 B：{escape(model_b)}</p><div class='panel'><h2>总体结论</h2><p>{escape(report.get('conclusion', ''))}</p><p>可比较知识点：{report.get('total', 0)}　｜　KU 一致：{report.get('exact_count', 0)}</p></div><div class='panel'><details><summary>模型综合分析建议</summary><div class='advice'>{advice_html}</div></details></div><div class='panel'><h2>知识点对比明细</h2><table><tr><th>知识点</th><th>模型 A</th><th>模型 B</th><th>KU 数量</th><th>评价</th></tr>{rows}</table></div><div class='panel'><h2>原始评测结果</h2><pre>{escape(raw)}</pre></div></body></html>"""

    # Legacy interactive renderer retained below for reference.
    from services.report_graph import build_graph_data

    def graph_only(result: Any) -> str:
        graph = json.dumps(build_graph_data(result), ensure_ascii=False).replace("</", "<\\/")
        return """<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><style>
body{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif;color:#1f2937;background:#fff}.layout{display:grid;grid-template-columns:minmax(420px,1fr) 320px;gap:12px;padding:10px}.graph{overflow:auto;background:#0f172a;border-radius:8px;padding:8px}.details{border:1px solid #dbe3ee;border-radius:8px;padding:12px;background:#f8fafc;min-height:300px}.details h3{margin-top:0}.source{white-space:pre-wrap;background:#fff;border:1px solid #dbe3ee;border-radius:6px;padding:8px;font-size:12px;max-height:300px;overflow:auto}.node{cursor:pointer}.node text{font-size:13px;fill:#e5e7eb;pointer-events:none}.edge{stroke:#94a3b8;stroke-width:1.5}.edge-label{font-size:11px;fill:#cbd5e1}
</style></head><body><div class='layout'><div class='graph'><svg id='graph' width='1220' height='760'></svg></div><div id='details' class='details'><h3>选择一个实体</h3><p>点击左侧节点查看详情。</p></div></div><script>const DATA=""" + graph + """;const svg=document.getElementById('graph'),details=document.getElementById('details'),ns='http://www.w3.org/2000/svg';const by=Object.fromEntries(DATA.nodes.map(n=>[n.id,n]));function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}function el(t,a){const x=document.createElementNS(ns,t);for(const[k,v]of Object.entries(a))x.setAttribute(k,v);return x;}function show(n){let h='<h3>'+esc(n.label)+'</h3>';for(const[k,v]of Object.entries(n.attributes||{})){const x=Array.isArray(v)?v.join(' › '):v;h+='<p><b>'+esc(k)+'</b><br>'+esc(x)+'</p>';}if(n.evidence)h+='<p><b>拆分证据</b></p><div class='+'"source"'+ '>'+esc(n.evidence)+'</div>';details.innerHTML=h;}for(const e of DATA.edges){const a=by[e.source],b=by[e.target];if(!a||!b)continue;svg.appendChild(el('line',{x1:a.x+200,y1:a.y+30,x2:b.x,y2:b.y+30,class:'edge'}));const t=el('text',{x:(a.x+b.x)/2+80,y:(a.y+b.y)/2+25,class:'edge-label'});t.textContent=e.label;svg.appendChild(t);}for(const n of DATA.nodes){const g=el('g',{});g.classList.add('node');g.onclick=()=>show(n);const fill=n.kind==='kp'?'#1d4ed8':n.kind==='ku'?'#047857':'#b45309';g.appendChild(el('rect',{x:n.x,y:n.y,width:200,height:60,rx:10,fill,stroke:'#cbd5e1'}));const t=el('text',{x:n.x+10,y:n.y+25});t.textContent=n.label.length>24?n.label.slice(0,24)+'…':n.label;g.appendChild(t);const k=el('text',{x:n.x+10,y:n.y+45});k.textContent=n.kind;g.appendChild(k);svg.appendChild(g);}</script></body></html>"""

    def iframe(result: dict[str, Any]) -> str:
        final = __import__('schemas.models', fromlist=['FinalExtraction']).FinalExtraction.model_validate(result)
        return "<iframe class='graph-frame' srcdoc='" + escape(graph_only(final), quote=True) + "' title='知识图谱'></iframe>"
    rows = "".join(
        f"<tr><td>{escape(x['kp_name'])}</td><td>{escape(x['model_a'])}</td><td>{escape(x['model_b'])}</td><td>{x['count_a']} / {x['count_b']}</td><td>{escape(x['kind'])}</td></tr>"
        for x in report.get("comparisons", [])
    )
    ai_advice = escape(report.get("ai_advice", ""))
    graph_sections = []
    graph_options = []
    for index, item in enumerate(report.get("comparisons", [])):
        graph_options.append(f"<option value='{index}'>{escape(item['kp_name'])}</option>")
        if item.get("final_a") and item.get("final_b"):
            graph_sections.append(f"<div class='graph-item' data-index='{index}'><div class='graphs'><div><h3>模型 A｜{escape(item['model_a'])}</h3>{iframe(item['final_a'])}</div><div><h3>模型 B｜{escape(item['model_b'])}</h3>{iframe(item['final_b'])}</div></div></div>")
    graphs_html = "".join(graph_sections)
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>模型稳定性评测报告</title>
<style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:1400px;margin:24px auto;padding:0 24px;color:#1f2937;background:#f8fafc}}.card{{display:inline-block;background:white;border:1px solid #dbe3ee;border-radius:10px;padding:14px 22px;margin:0 10px 12px 0}}.card b{{display:block;color:#64748b;font-size:13px}}.card strong{{display:block;font-size:26px;margin-top:5px}}.panel{{background:white;border:1px solid #dbe3ee;border-radius:10px;padding:18px;margin:14px 0}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #dbe3ee;padding:8px;text-align:left}}th{{background:#f1f5f9}}.conclusion{{font-size:16px;line-height:1.8}}.graphs{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:12px}}.graphs>div{{background:white;border:1px solid #dbe3ee;padding:12px;overflow:auto}}.graph-frame{{width:100%;height:760px;border:0;background:white}}</style></head><body>
<h1>模型稳定性评测报告</h1><p>模型 A：{escape(model_a)}　模型 B：{escape(model_b)}</p>
<div><div class='card'><b>可比较知识点</b><strong>{report.get('total', 0)}</strong></div><div class='card'><b>KU 一致</b><strong>{report.get('exact_count', 0)}</strong></div></div>
<div class='panel'><h2>总体结论</h2><p class='conclusion'>{escape(report.get('conclusion', ''))}</p></div><div class='panel'><details><summary>模型综合分析建议（点击展开）</summary><div class='conclusion'>{ai_advice or '暂无模型综合分析建议。'}</div></details></div>
<div class='panel'><h2>知识点对比明细</h2><table><tr><th>知识点</th><th>模型 A</th><th>模型 B</th><th>KU 数量</th><th>评价</th></tr>{rows}</table></div><div class='panel'><h2>知识点图谱对比</h2><select id='graph-picker'><option value='' selected>请选择知识点</option>{''.join(graph_options)}</select><div id='graph-results'>{graphs_html or '暂无可嵌入的图谱数据。'}</div></div><script>const gp=document.getElementById('graph-picker');const gi=[...document.querySelectorAll('.graph-item')];function showGraph(){{gi.forEach((x)=>x.style.display=gp.value!==''&&x.dataset.index===gp.value?'block':'none')}}if(gp){{gp.addEventListener('change',showGraph);showGraph()}}</script></body></html>"""


def _key(run: dict[str, Any]) -> str:
    return (run.get("kp_id") or run.get("kp_name") or "").strip()


def _units(run: dict[str, Any]) -> list[dict[str, Any]]:
    value = run.get("final_result")
    if value is None and run.get("final_json"):
        try:
            value = json.loads(run["final_json"])
        except (TypeError, ValueError, json.JSONDecodeError):
            value = {}
    return sorted((value or {}).get("knowledge_units", []), key=lambda x: x.get("order_index", 0))


def _final_payload(run: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(run.get("final_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def build_stability_report(runs: list[dict[str, Any]], selected_models: tuple[str, str] | None = None) -> dict[str, Any]:
    if selected_models:
        runs = [run for run in runs if (run.get("model_name") or DEFAULT_MODEL) in selected_models]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run.get("status") == "COMPLETED" and run.get("final_json"):
            groups[_key(run)].append(run)
    comparisons = []
    for kp_key, items in groups.items():
        if len(items) < 2:
            continue
        base = items[0]
        for other in items[1:]:
            if (base.get("model_name") or DEFAULT_MODEL) == (other.get("model_name") or DEFAULT_MODEL):
                continue
            a, b = _units(base), _units(other)
            same_count = len(a) == len(b)
            same_boundaries = [
                (x.get("start_block_id"), x.get("end_block_id")) == (y.get("start_block_id"), y.get("end_block_id"))
                for x, y in zip(a, b)
            ]
            boundary_rate = sum(same_boundaries) / max(len(a), len(b), 1)
            exact = same_count and boundary_rate == 1
            if exact:
                kind = "KU 一致"
            elif same_count:
                kind = "KU 不一致｜边界差异"
            elif len(a) < len(b):
                kind = "模型B拆分更多"
            else:
                kind = "模型B合并更多"
            comparisons.append({"kp_key": kp_key, "kp_name": base.get("kp_name", kp_key), "model_a": base.get("model_name") or DEFAULT_MODEL, "model_b": other.get("model_name") or DEFAULT_MODEL, "count_a": len(a), "count_b": len(b), "boundary_rate": boundary_rate, "kind": kind, "units_a": a, "units_b": b, "final_a": _final_payload(base), "final_b": _final_payload(other)})
    total = len(comparisons)
    exact_count = sum(x["kind"] == "KU 一致" for x in comparisons)
    kind_counts = {kind: sum(x["kind"] == kind for x in comparisons) for kind in sorted({x["kind"] for x in comparisons})}
    total_units = sum(x["count_a"] + x["count_b"] for x in comparisons)
    count_equal = sum(x["count_a"] == x["count_b"] for x in comparisons)
    avg_boundary = sum(x["boundary_rate"] for x in comparisons) / total if total else 0
    if not total:
        conclusion = "当前没有同一知识点的多模型完成记录，暂时无法进行稳定性评测。"
    elif exact_count / total >= 0.8:
        conclusion = "总体拆分稳定性较高，多数模型给出了相同或高度接近的 KU 边界。"
    elif exact_count / total >= 0.5:
        conclusion = "总体拆分稳定性中等，部分知识点存在合并、拆分或边界判断差异。"
    else:
        conclusion = "总体拆分稳定性偏低，建议先统一 KU 边界判定规则，再比较模型能力。"
    suggestions = []
    if any(x["kind"] in ("模型B拆分更多", "模型B合并更多") for x in comparisons):
        suggestions.append("在 Prompt 中明确‘可独立回答的作者性解释模块’判定，并补充合并与拆分的正反例，减少粒度漂移。")
    if any(x["kind"] == "边界差异" for x in comparisons):
        suggestions.append("在输入中强调标题不是自动边界，要求模型结合主题转换、main_question 和完整解释闭合性判断边界。")
    if avg_boundary < 0.8:
        suggestions.append("增加 Stage 1 结果复核：对边界不一致的知识点进入人工确认或二次裁决流程，不建议直接进入 Stage 2。")
    if not suggestions:
        suggestions.append("当前差异较少，建议保持现有 Prompt，并持续积累跨模型样本后再调整规则。")
    return {"comparisons": comparisons, "total": total, "exact_count": exact_count, "count_equal": count_equal, "avg_boundary": avg_boundary, "kind_counts": kind_counts, "conclusion": conclusion, "suggestions": suggestions}
