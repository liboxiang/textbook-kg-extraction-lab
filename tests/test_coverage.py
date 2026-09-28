from schemas.models import KnowledgePointInput, Stage1LLMResult
from services.source_segmenter import segment_source_text
from services.coverage_validator import validate_and_resolve_stage1
from pydantic import ValidationError


def test_full_coverage_pass():
    kp = KnowledgePointInput(kp_id="KP1", kp_name="测试", source_text="A。B。C。", page_start=1, page_end=1)
    blocks = segment_source_text(kp.source_text)
    result = Stage1LLMResult.model_validate({
        "knowledge_units": [
            {"temp_ku_id":"KU_01","order_index":1,"title":"AB","main_question":"AB?","start_block_id":blocks[0].block_id,"end_block_id":blocks[1].block_id},
            {"temp_ku_id":"KU_02","order_index":2,"title":"C","main_question":"C?","start_block_id":blocks[2].block_id,"end_block_id":blocks[2].block_id},
        ],
        "evidence": {"ku_split": [
            {"temp_ku_id": "KU_01", "evidence": "A 与 B 共同构成一个主题。"},
            {"temp_ku_id": "KU_02", "evidence": "C 转向另一个主题。"},
        ]},
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
        ],
        "evidence": {"ku_split": [
            {"temp_ku_id": "KU_01", "evidence": "A 构成一个主题。"},
            {"temp_ku_id": "KU_02", "evidence": "C 构成另一个主题。"},
        ]},
    })
    resolved = validate_and_resolve_stage1(kp, blocks, result)
    assert resolved.validation.status == "FAIL"
    assert resolved.validation.gap_count == 1


def test_stage1_evidence_rejects_source_block_ids():
    try:
        Stage1LLMResult.model_validate({
            "knowledge_units": [],
            "evidence": {"ku_split": [{
                "temp_ku_id": "KU_01",
                "evidence": "证据",
                "source_block_ids": ["S0001"],
            }]},
        })
    except ValidationError:
        return
    raise AssertionError("source_block_ids should be rejected")


def test_legacy_stage1_resolved_evidence_defaults_empty():
    from schemas.models import Stage1ResolvedResult

    legacy = Stage1ResolvedResult.model_validate({
        "kp_id": "KP1",
        "kp_name": "测试",
        "source_blocks": [],
        "knowledge_units": [],
        "validation": {
            "coverage_rate": 0,
            "gap_count": 0,
            "overlap_count": 0,
            "order_valid": True,
            "all_blocks_covered": False,
            "status": "FAIL",
        },
    })
    assert legacy.evidence.ku_split == []
