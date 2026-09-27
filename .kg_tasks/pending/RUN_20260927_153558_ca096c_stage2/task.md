# Pending textbook KG task

Stage: STAGE2
Run ID: RUN_20260927_153558_ca096c
Created: 2026-09-27T15:35:58

## Instructions

# 角色与任务
你是职业教育教材知识结构化专家。输入是已经人工确认边界的完整 KU。请在每个 KU 内提取结构化属性和内容要素，保留教材作者的论述层次。

# 最高优先级约束
1. KU 的 `temp_ku_id`、`title`、`main_question` 和 Source Block 边界均已确认，必须原样返回，不得改写、拆分、合并、扩展或缩小。
2. 只依据当前 KU 提供的 `source_text` 与 `source_blocks` 提取，不得使用外部常识补充教材未表达的结论。
3. `knowledge_object` 表示整个 KU 的知识对象，不能缩小为其中某个编号条目或局部事项。
4. `core_conclusion` 必须回答整个 `main_question`，覆盖 KU 的主要论述分支，并由原文直接支持；既不能逐句复写全文，也不能只概括其中一个局部主题。
5. 内容要素是 KU 内部具有完整语义功能的组成部分，不是新的 KU、图实体、句子索引或 Source Block 映射。
6. 不做 KP/KU 关系、ExamPoint、共同考查、真题/课程关系或重要度判断。

# 内容要素粒度与组织
- 按教材原文顺序提取内容要素，优先保留作者已有的标题、编号、并列关系和层次结构。
- 不得按句子、编号、数字或 Source Block 机械拆分。某段可以单独命题，也不代表它必须成为独立内容要素。
- 多段内容如果共同完成一个子问题、分类体系、条件集合、参数组、连续流程、方法说明或论证，应合并为一个完整内容要素，并在 `content` 中保留必要的内部顺序和细项。
- 一个 Source Block 可以参与支持一个完整内容要素；多个连续 Source Block 也可以共同支持一个内容要素。Source Block 只用于证据定位，不决定内容要素边界。
- `name` 应指出内容要素在整个 KU 中承担的语义角色和所属对象，使其脱离相邻元素后仍能准确定位。
- 没有专用枚举类型的组成、分类、材料、性能或构造类内容使用 `OTHER`，并通过 `name` 准确表达其含义，不得强行误归类。

# 证据规则
- 每个内容要素的 `evidence_block_ids` 必须位于当前 KU 范围内，并按原文顺序排列。
- 证据应覆盖该内容要素全部核心内容所需的最小充分证据范围：不得只引用不能独立支持结论的标题，也不得把整个 KU 的全部 Block 无差别挂到每个内容要素上。
- 如果结论跨多个 Block 才完整成立，应保留全部必要 Block；如果单个 Block 已足够支持，则不要扩大证据范围。
- 对“参见其他章节、图表、规范或资料”的表述，只提取当前 KU 原文明示的内容，不得自行补入被引用位置的知识内容。

# 字段与类型
`knowledge_type` 选择最能概括整个 KU 的类型；如果模块同时包含多种知识且没有单一主类型，使用 `OTHER`，不得为了贴合某个类型而删减内容。可选值：
DEFINITION, PRINCIPLE, CLASSIFICATION, REQUIREMENT, CONDITION, PROCEDURE, METHOD, PARAMETER, CALCULATION, COMPARISON, CAUSE, EFFECT, RESPONSIBILITY, PROHIBITION, EXCEPTION, RULE, OTHER。

`content_elements.element_type` 可选值：
APPLICABLE_CONDITION, QUANTITATIVE_REQUIREMENT, EXCEPTION, STEP, SUPPLEMENT, EXAMPLE, CALCULATION_ELEMENT, DEFINITION, METHOD, PROHIBITION, RESPONSIBILITY, OTHER。

# 输出前自检
- `temp_ku_id`、`title` 和 `main_question` 是否与输入完全一致？
- `core_conclusion` 是否覆盖整个 KU，而非只覆盖局部条目？
- 内容要素是否表达完整子问题，而非按句子、编号或 Block 机械切碎？
- 内容要素顺序是否与作者论述顺序一致？
- 每项证据是否属于当前 KU，并达到最小充分而非过少或泛滥？
- 是否加入了原文没有的知识，或补写了被引用位置的内容？

# 输出格式
只输出符合下列结构的合法 JSON 对象，不输出 Markdown 或解释：
{
  "knowledge_units": [
    {
      "temp_ku_id": "KU_01",
      "title": "与输入完全一致",
      "main_question": "与输入完全一致",
      "knowledge_object": "整个模块的知识对象",
      "core_conclusion": "由本 KU 原文支持并覆盖主要分支的综合结论",
      "knowledge_type": "OTHER",
      "content_elements": [
        {
          "element_id": "CE_01",
          "element_type": "OTHER",
          "name": "内容要素的所属对象与语义角色",
          "content": "对应的完整要求或说明",
          "evidence_block_ids": ["S0002"]
        }
      ]
    }
  ]
}



## Input
Read `input.json` in this directory.

## Required action
Perform the task yourself using the current Codex model and repository instructions. Write only the final JSON object to `result.json`. Then run:

```bash
python scripts/validate_codex_result.py D:/devProject/textbook_kg_extraction_lab_v1.0/textbook_kg_extraction_lab/.kg_tasks/pending/RUN_20260927_153558_ca096c_stage2
```

Do not edit `input.json`.
