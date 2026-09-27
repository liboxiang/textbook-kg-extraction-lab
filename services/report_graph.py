from __future__ import annotations

from schemas.models import FinalExtraction


def build_graph_data(result: FinalExtraction) -> dict:
    """Build a serializable KP -> KU -> content-element graph."""
    nodes: list[dict] = []
    edges: list[dict] = []
    top = 50
    ku_gap = 50
    node_height = 60
    element_gap = 30
    current_y = top
    ku_positions: list[tuple[str, int]] = []

    kp_id = f"kp:{result.kp.kp_id}"
    nodes.append({
        "id": kp_id,
        "kind": "kp",
        "label": result.kp.kp_name,
        "x": 40,
        "y": 50,
        "attributes": {"kp_id": result.kp.kp_id, "kp_name": result.kp.kp_name},
    })

    for ku in result.knowledge_units:
        ku_id = f"ku:{ku.ku_id}"
        element_count = len(ku.content_elements)
        cluster_height = max(node_height, element_count * (node_height + element_gap))
        ku_y = current_y + max(0, (cluster_height - node_height) // 2)
        ku_positions.append((ku_id, ku_y))
        nodes.append({
            "id": ku_id,
            "kind": "ku",
            "label": f"KU-{ku.order_index:02d} {ku.title}",
            "x": 330,
            "y": ku_y,
            "attributes": {
                "title": ku.title,
                "section_path": ku.section_path,
                "main_question": ku.main_question,
                "knowledge_object": ku.knowledge_object,
                "core_conclusion": ku.core_conclusion,
                "knowledge_type": ku.knowledge_type,
                "knowledge_type_name": ku.knowledge_type_name,
                "source_range": f"{ku.start_block_id} ~ {ku.end_block_id}",
                "source_text": ku.source_text,
            },
        })
        edges.append({"source": kp_id, "target": ku_id, "label": "包含"})
        for element_index, element in enumerate(ku.content_elements):
            element_id = f"ce:{ku.ku_id}:{element.element_id}"
            element_y = current_y + element_index * (node_height + element_gap)
            nodes.append({
                "id": element_id,
                "kind": "element",
                "label": element.name,
                "x": 650,
                "y": element_y,
                "attributes": {
                    "element_type": element.element_type,
                    "element_type_name": element.element_type_name,
                    "name": element.name,
                    "content": element.content,
                },
            })
            edges.append({"source": ku_id, "target": element_id, "label": "包含"})
        current_y += cluster_height + ku_gap

    height = max(760, current_y + 30)
    return {"nodes": nodes, "edges": edges, "width": 1220, "height": height}
