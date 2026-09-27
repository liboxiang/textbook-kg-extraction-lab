from __future__ import annotations

from schemas.models import Stage1ResolvedResult, Stage2LLMResult, FinalExtraction, FinalKU, KnowledgePointInput


def validate_and_build_final(
    kp: KnowledgePointInput,
    stage1: Stage1ResolvedResult,
    stage2: Stage2LLMResult,
) -> FinalExtraction:
    s1_map = {u.temp_ku_id: u for u in stage1.knowledge_units}
    s2_map = {u.temp_ku_id: u for u in stage2.knowledge_units}

    if set(s1_map) != set(s2_map):
        missing = set(s1_map) - set(s2_map)
        extra = set(s2_map) - set(s1_map)
        raise ValueError(f"Stage2 KU集合与已确认Stage1不一致。missing={missing}, extra={extra}")

    finals: list[FinalKU] = []
    for s1 in sorted(stage1.knowledge_units, key=lambda x: x.order_index):
        s2 = s2_map[s1.temp_ku_id]
        finals.append(
            FinalKU(
                ku_id=f"{kp.kp_id}_KU_{s1.order_index:02d}",
                kp_id=kp.kp_id,
                order_index=s1.order_index,
                title=s2.title or s1.title,
                main_question=s2.main_question or s1.main_question,
                section_path=s1.section_path,
                knowledge_object=s2.knowledge_object,
                core_conclusion=s2.core_conclusion,
                knowledge_type=s2.knowledge_type,
                knowledge_type_name=s2.knowledge_type_name,
                page_start=s1.page_start,
                page_end=s1.page_end,
                start_offset=s1.start_offset,
                end_offset=s1.end_offset,
                start_block_id=s1.start_block_id,
                end_block_id=s1.end_block_id,
                source_text=s1.source_text,
                content_elements=s2.content_elements,
            )
        )

    return FinalExtraction(kp=kp, knowledge_units=finals, stage1_validation=stage1.validation)
