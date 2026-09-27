from schemas.models import KnowledgePointInput, Stage1LLMResult, Stage2LLMResult
from services.source_segmenter import segment_source_text
from services.coverage_validator import validate_and_resolve_stage1
from services.stage2_validator import validate_and_build_final


def test_stage2_builds_final():
    kp = KnowledgePointInput(kp_id="KP1", kp_name="测试", source_text="模板达到要求后方可拆除。")
    blocks = segment_source_text(kp.source_text)
    s1 = Stage1LLMResult.model_validate({
        "knowledge_units":[{
            "temp_ku_id":"KU_01","order_index":1,"title":"模板拆除条件",
            "main_question":"模板在什么条件下可以拆除？",
            "start_block_id":blocks[0].block_id,"end_block_id":blocks[-1].block_id
        }]
    })
    resolved = validate_and_resolve_stage1(kp, blocks, s1)
    s2 = Stage2LLMResult.model_validate({
        "knowledge_units":[{
            "temp_ku_id":"KU_01","title":"模板拆除条件","main_question":"模板在什么条件下可以拆除？",
            "knowledge_object":"模板拆除","core_conclusion":"模板达到要求后方可拆除。","knowledge_type":"CONDITION",
            "content_elements":[]
        }]
    })
    final = validate_and_build_final(kp, resolved, s2)
    assert final.knowledge_units[0].source_text == kp.source_text
    assert final.knowledge_units[0].ku_id == "KP1_KU_01"


def test_stage2_preserves_open_semantic_type_names():
    kp = KnowledgePointInput(kp_id="KP2", kp_name="测试", source_text="由垫层、基层和面层组成。")
    blocks = segment_source_text(kp.source_text)
    s1 = Stage1LLMResult.model_validate({
        "knowledge_units": [{
            "temp_ku_id": "KU_01", "order_index": 1, "title": "结构组成",
            "main_question": "结构由哪些部分组成？",
            "start_block_id": blocks[0].block_id, "end_block_id": blocks[-1].block_id,
        }]
    })
    resolved = validate_and_resolve_stage1(kp, blocks, s1)
    s2 = Stage2LLMResult.model_validate({
        "knowledge_units": [{
            "temp_ku_id": "KU_01", "title": "结构组成", "main_question": "结构由哪些部分组成？",
            "knowledge_object": "结构", "core_conclusion": "结构由多个部分组成。",
            "knowledge_type": "STRUCTURAL_COMPOSITION", "knowledge_type_name": "结构组成",
            "content_elements": [{
                "element_id": "CE_01", "element_type": "STRUCTURAL_COMPONENT",
                "element_type_name": "结构组成部分", "name": "结构组成部分",
                "content": "垫层、基层和面层",
            }],
        }]
    })
    final = validate_and_build_final(kp, resolved, s2)
    assert final.knowledge_units[0].knowledge_type == "STRUCTURAL_COMPOSITION"
    assert final.knowledge_units[0].knowledge_type_name == "结构组成"
    assert final.knowledge_units[0].content_elements[0].element_type == "STRUCTURAL_COMPONENT"
