from __future__ import annotations

import json
from html import escape

from schemas.models import FinalExtraction
from services.report_graph import build_graph_data


def _safe_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_html_report(result: FinalExtraction) -> str:
    graph_data = build_graph_data(result)
    graph_json = _safe_json(graph_data)
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        "<title>教材知识图谱完整报告</title>",
        "<style>",
        "body{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:1400px;margin:24px auto;padding:0 20px;color:#1f2937;background:#f8fafc}",
        ".meta,.ku,.graph-wrap{background:white;border:1px solid #dbe3ee;border-radius:12px;padding:18px;margin:16px 0;box-shadow:0 2px 10px #0f172a0d}",
        ".ku h2{margin-top:0}.tag{display:inline-block;background:#e8eef7;border-radius:6px;padding:3px 8px;margin-right:6px}",
        ".source{white-space:pre-wrap;background:#f8fafc;padding:12px;border-radius:8px;border-left:4px solid #94a3b8;max-height:280px;overflow:auto}",
        "table{border-collapse:collapse;width:100%;margin-top:10px}td,th{border:1px solid #dbe3ee;padding:8px;text-align:left;vertical-align:top}th{background:#f1f5f9}",
        ".graph-toolbar{display:flex;justify-content:flex-end;margin:8px 0}.fullscreen-btn{border:1px solid #94a3b8;border-radius:6px;background:#0f172a;color:#f8fafc;padding:7px 12px;cursor:pointer}.graph-shell{background:white}.graph-shell:fullscreen{padding:18px;background:#f8fafc;overflow:auto}.graph-shell:fullscreen .graph-layout{height:calc(100vh - 90px);grid-template-columns:minmax(0,1fr) 380px}.graph-shell:fullscreen .graph{height:100%}.graph-shell:fullscreen .details{overflow:auto}.graph-layout{display:grid;grid-template-columns:minmax(600px,1fr) 360px;gap:16px}.graph{overflow:auto;border:1px solid #dbe3ee;border-radius:10px;background:#0f172a;padding:8px}.details{border:1px solid #dbe3ee;border-radius:10px;padding:14px;background:#f8fafc;min-height:300px}.details h3{margin-top:0}.detail-source{white-space:pre-wrap;background:white;border:1px solid #dbe3ee;border-radius:6px;padding:8px;max-height:420px;overflow:auto;font-family:inherit;font-size:12px}.node{cursor:pointer}.node text{font-size:13px;fill:#e5e7eb;pointer-events:none}.edge{stroke:#94a3b8;stroke-width:1.5}.edge-label{font-size:11px;fill:#cbd5e1}.hint{color:#64748b;font-size:13px}",
        "</style></head><body>",
        f"<h1>{escape(result.kp.kp_name)}｜知识图谱完整报告</h1>",
        "<div class='meta'>",
        f"<b>KP ID：</b>{escape(result.kp.kp_id)}<br>",
        f"<b>页码：</b>{result.kp.page_start or '-'} - {result.kp.page_end or '-'}<br>",
        f"<b>KU 数量：</b>{len(result.knowledge_units)}<br>",
        f"<b>Coverage：</b>{result.stage1_validation.coverage_rate:.0%}",
        "</div>",
        "<div class='graph-wrap'><h2>实体—关系—属性图</h2><p class='hint'>点击 KP、KU 或内容要素节点，在右侧查看属性。</p>",
        "<div id='graph-shell' class='graph-shell'><div class='graph-toolbar'><button id='fullscreen-btn' class='fullscreen-btn' type='button'>全屏展示</button></div>",
        f"<div class='graph-layout'><div class='graph'><svg id='graph' width='{graph_data['width']}' height='{graph_data['height']}' role='img' aria-label='知识图谱'></svg></div><div id='details' class='details'><h3>选择一个实体</h3><p>图中实体包括 KP、KU 和内容要素。</p></div></div></div></div>",
    ]
    for ku in result.knowledge_units:
        parts += [
            "<div class='ku'>",
            f"<h2>{ku.order_index}. {escape(ku.title)}</h2>",
            f"<p><span class='tag'>{escape(ku.knowledge_type_name or ku.knowledge_type)}（{escape(ku.knowledge_type)}）</span><b>主问题：</b>{escape(ku.main_question)}</p>",
            f"<p><b>知识对象：</b>{escape(ku.knowledge_object)}</p>",
            f"<p><b>核心结论：</b>{escape(ku.core_conclusion)}</p>",
            f"<p><b>原文范围：</b>{escape(ku.start_block_id)} ~ {escape(ku.end_block_id)}</p>",
            f"<div class='source'>{escape(ku.source_text)}</div>",
        ]
        if ku.content_elements:
            parts.append("<h3>内容要素</h3><table><tr><th>类型代码</th><th>类型中文</th><th>名称</th><th>内容</th></tr>")
            for ce in ku.content_elements:
                parts.append(
                    "<tr>"
                    f"<td>{escape(ce.element_type)}</td>"
                    f"<td>{escape(ce.element_type_name)}</td>"
                    f"<td>{escape(ce.name)}</td>"
                    f"<td>{escape(ce.content)}</td>"
                    "</tr>"
                )
            parts.append("</table>")
        parts.append("</div>")
    parts += [
        f"<script>const GRAPH={graph_json};",
        "const svg=document.getElementById('graph'),details=document.getElementById('details'),shell=document.getElementById('graph-shell'),fullscreenBtn=document.getElementById('fullscreen-btn');",
        "const byId=Object.fromEntries(GRAPH.nodes.map(n=>[n.id,n]));const ns='http://www.w3.org/2000/svg';",
        "function el(tag,attrs){const x=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))x.setAttribute(k,v);return x;}",
        "function escapeHtml(v){return String(v).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));}",
        "function show(n){details.innerHTML='<h3>'+escapeHtml(n.label)+'</h3>'+Object.entries(n.attributes).map(([k,v])=>{const value=Array.isArray(v)?v.join(', '):String(v);return k==='source_text'?'<p><b>教材原文</b></p><div class=\"detail-source\">'+escapeHtml(value)+'</div>':'<p><b>'+escapeHtml(k)+'</b><br>'+escapeHtml(value)+'</p>';}).join('');}",
        "function updateFullscreenLabel(){fullscreenBtn.textContent=document.fullscreenElement?'退出全屏':'全屏展示';}",
        "fullscreenBtn.addEventListener('click',async()=>{try{if(document.fullscreenElement){await document.exitFullscreen();}else{await shell.requestFullscreen();}}catch(e){fullscreenBtn.textContent='全屏不可用';}});document.addEventListener('fullscreenchange',updateFullscreenLabel);",
        "for(const e of GRAPH.edges){const a=byId[e.source],b=byId[e.target];if(!a||!b)continue;svg.appendChild(el('line',{x1:a.x+200,y1:a.y+30,x2:b.x,y2:b.y+30,class:'edge'}));const t=el('text',{x:(a.x+b.x)/2+80,y:(a.y+b.y)/2+25,class:'edge-label'});t.textContent=e.label;svg.appendChild(t);}",
        "for(const n of GRAPH.nodes){const g=el('g',{});g.classList.add('node');g.addEventListener('click',()=>show(n));const fill=n.kind==='kp'?'#1d4ed8':n.kind==='ku'?'#047857':n.kind==='element'?'#b45309':'#475569';g.appendChild(el('rect',{x:n.x,y:n.y,width:200,height:60,rx:10,fill,stroke:'#cbd5e1'}));const t=el('text',{x:n.x+10,y:n.y+25});t.textContent=n.label.length>24?n.label.slice(0,24)+'…':n.label;g.appendChild(t);const k=el('text',{x:n.x+10,y:n.y+45});k.textContent=n.kind;g.appendChild(k);svg.appendChild(g);}",
        "</script></body></html>",
    ]
    return "".join(parts)
