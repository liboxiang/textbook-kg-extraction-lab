from schemas.models import KnowledgePointInput, Stage1LLMResult
from services.source_segmenter import segment_source_text
from services.coverage_validator import validate_and_resolve_stage1


def test_full_coverage_pass():
    kp = KnowledgePointInput(kp_id="KP1", kp_name="测试", source_text="A。B。C。", page_start=1, page_end=1)
    blocks = segment_source_text(kp.source_text)
    result = Stage1LLMResult.model_validate({
        "knowledge_units": [
            {"temp_ku_id":"KU_01","order_index":1,"title":"AB","main_question":"AB?","start_block_id":blocks[0].block_id,"end_block_id":blocks[1].block_id},
            {"temp_ku_id":"KU_02","order_index":2,"title":"C","main_question":"C?","start_block_id":blocks[2].block_id,"end_block_id":blocks[2].block_id},
        ]
    })
    resolved = validate_and_resolve_stage1(kp, blocks, result)
    assert resolved.validation.status == "PASS"
    assert "".join(u.source_text for u in resolved.knowledge_units) == kp.source_text


def test_gap_fails():
    kp = KnowledgePointInput(kp_id="KP1", kp_name="测试", source_text="A。B。C。")
    blocks = segment_source_text(kp.source_text)
    result = Stage1LLMResult.model_validate({
        "knowledge_units": [
            {"temp_ku_id":"KU_01","order_index":1,"title":"A","main_question":"A?","start_block_id":blocks[0].block_id,"end_block_id":blocks[0].block_id},
            {"temp_ku_id":"KU_02","order_index":2,"title":"C","main_question":"C?","start_block_id":blocks[2].block_id,"end_block_id":blocks[2].block_id},
        ]
    })
    resolved = validate_and_resolve_stage1(kp, blocks, result)
    assert resolved.validation.status == "FAIL"
    assert resolved.validation.gap_count == 1
