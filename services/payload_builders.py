from __future__ import annotations

from schemas.models import KnowledgePointInput, SourceBlock, Stage1ResolvedResult


def build_stage1_input(kp: KnowledgePointInput, blocks: list[SourceBlock]) -> dict:
    return {
        "knowledge_point": kp.model_dump(),
        "source_blocks": [b.model_dump() for b in blocks],
        "note": "Source Block 仅用于定位。必须对全部 blocks 做连续、有序、无遗漏、无重叠的 KU 分区。",
    }


def build_stage2_input(stage1: Stage1ResolvedResult) -> dict:
    block_map = {b.block_id: b for b in stage1.source_blocks}
    units = []
    for ku in sorted(stage1.knowledge_units, key=lambda x: x.order_index):
        start_idx = block_map[ku.start_block_id].index
        end_idx = block_map[ku.end_block_id].index
        ku_blocks = [
            b.model_dump()
            for b in stage1.source_blocks
            if start_idx <= b.index <= end_idx
        ]
        units.append(
            {
                "temp_ku_id": ku.temp_ku_id,
                "order_index": ku.order_index,
                "title": ku.title,
                "main_question": ku.main_question,
                "section_path": ku.section_path,
                "source_text": ku.source_text,
                "source_blocks": ku_blocks,
                "page_start": ku.page_start,
                "page_end": ku.page_end,
            }
        )
    return {"kp_id": stage1.kp_id, "kp_name": stage1.kp_name, "knowledge_units": units}
