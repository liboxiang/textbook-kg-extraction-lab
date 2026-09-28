from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class KnowledgePointInput(BaseModel):
    kp_id: str
    kp_name: str
    source_text: str
    page_start: int | None = None
    page_end: int | None = None


class SourceBlock(BaseModel):
    block_id: str
    index: int
    start_offset: int
    end_offset: int
    text: str


class KUSplitItem(BaseModel):
    temp_ku_id: str
    order_index: int
    title: str
    main_question: str
    section_path: list[str] = Field(default_factory=list)
    start_block_id: str
    end_block_id: str


class KUSplitEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temp_ku_id: str
    evidence: str = Field(min_length=1)


class Stage1Evidence(BaseModel):
    ku_split: list[KUSplitEvidence]


class Stage1LLMResult(BaseModel):
    knowledge_units: list[KUSplitItem]
    evidence: Stage1Evidence


class Stage1Validation(BaseModel):
    coverage_rate: float
    gap_count: int
    overlap_count: int
    order_valid: bool
    all_blocks_covered: bool
    status: Literal["PASS", "FAIL"]
    errors: list[str] = Field(default_factory=list)


class KUResolved(BaseModel):
    temp_ku_id: str
    order_index: int
    title: str
    main_question: str
    section_path: list[str] = Field(default_factory=list)
    start_block_id: str
    end_block_id: str
    start_offset: int
    end_offset: int
    source_text: str
    page_start: int | None = None
    page_end: int | None = None


class Stage1ResolvedResult(BaseModel):
    kp_id: str
    kp_name: str
    source_blocks: list[SourceBlock]
    knowledge_units: list[KUResolved]
    validation: Stage1Validation
    evidence: Stage1Evidence


# 类型不是封闭枚举：教材知识角色不可预先穷举，模型需要根据语义生成稳定标识。
ContentElementType = str
KnowledgeType = str


class ContentElement(BaseModel):
    element_id: str
    element_type: ContentElementType
    element_type_name: str = ""
    name: str
    content: str

    @model_validator(mode="after")
    def fill_legacy_type_name(self):
        """Keep old fixed-type results readable; new custom types must provide a name."""
        if not self.element_type_name:
            legacy_names = {
                "APPLICABLE_CONDITION": "适用条件",
                "QUANTITATIVE_REQUIREMENT": "量化要求",
                "EXCEPTION": "例外",
                "STEP": "步骤",
                "SUPPLEMENT": "补充说明",
                "EXAMPLE": "示例",
                "CALCULATION_ELEMENT": "计算要素",
                "DEFINITION": "定义",
                "METHOD": "方法",
                "PROHIBITION": "禁止事项",
                "RESPONSIBILITY": "责任",
            }
            self.element_type_name = legacy_names.get(self.element_type, "")
        return self


class KUStructured(BaseModel):
    temp_ku_id: str
    title: str
    main_question: str
    knowledge_object: str
    core_conclusion: str
    knowledge_type: KnowledgeType
    knowledge_type_name: str = ""
    content_elements: list[ContentElement] = Field(default_factory=list)


class ContentElementSplitEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temp_ku_id: str
    element_id: str
    evidence: str = Field(min_length=1)


class Stage2Evidence(BaseModel):
    content_element_split: list[ContentElementSplitEvidence]


class Stage2LLMResult(BaseModel):
    knowledge_units: list[KUStructured]
    evidence: Stage2Evidence


class FinalKU(BaseModel):
    ku_id: str
    kp_id: str
    order_index: int
    title: str
    main_question: str
    section_path: list[str] = Field(default_factory=list)
    knowledge_object: str
    core_conclusion: str
    knowledge_type: KnowledgeType
    knowledge_type_name: str = ""
    page_start: int | None = None
    page_end: int | None = None
    start_offset: int
    end_offset: int
    start_block_id: str
    end_block_id: str
    source_text: str
    content_elements: list[ContentElement] = Field(default_factory=list)


class FinalKUSplitEvidence(BaseModel):
    ku_id: str
    evidence: str


class FinalContentElementSplitEvidence(BaseModel):
    ku_id: str
    element_id: str
    evidence: str


class FinalEvidence(BaseModel):
    ku_split: list[FinalKUSplitEvidence] = Field(default_factory=list)
    content_element_split: list[FinalContentElementSplitEvidence] = Field(default_factory=list)


class FinalExtraction(BaseModel):
    kp: KnowledgePointInput
    knowledge_units: list[FinalKU]
    stage1_validation: Stage1Validation
    evidence: FinalEvidence = Field(default_factory=FinalEvidence)
