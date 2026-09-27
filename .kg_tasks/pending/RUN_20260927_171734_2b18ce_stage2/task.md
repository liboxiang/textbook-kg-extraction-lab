# Pending textbook KG task

Stage: STAGE2
Run ID: RUN_20260927_171734_2b18ce
Created: 2026-09-27T17:17:34

## Instructions

# 角色与任务
你是职业教育教材知识结构化专家。输入是已经人工确认边界的完整 KU。请在每个 KU 内提取知识对象、核心结论、知识类型和内容要素，保留教材作者的论述层次，并为知识类型生成可供后续 Agent 使用的语义分类。

# 最高优先级约束
1. KU 的 `temp_ku_id`、`title`、`main_question` 和边界已确认，必须原样返回，不得改写、拆分、合并、扩展或缩小。
2. 只依据当前 KU 的 `source_text` 与 `source_blocks` 提取，不得用外部常识补充教材未表达的结论。
3. `knowledge_object` 表示整个 KU 的知识对象，不能缩小为其中一个编号条目或局部事项。
4. `core_conclusion` 必须回答整个 `main_question`，覆盖 KU 的主要论述分支；既不能逐句复写全文，也不能只概括一个局部。
5. 内容要素是 KU 内部具有完整语义功能的组成部分，不是新的 KU、图实体、句子索引或 Source Block 映射。
6. 不做 KP/KU 关系、ExamPoint、共同考查、真题/课程关系或重要度判断。

# 开放式类型归纳
`knowledge_type` 和 `element_type` 都是开放式语义类型，不是封闭枚举。不得输出 `OTHER`、`UNKNOWN`、`MISC` 或“其他”作为兜底类型。

类型生成必须遵循以下顺序：
1. 先概括该知识的专业语义角色，再生成类型标识；不要因为无法匹配旧枚举就选择宽泛兜底值。
2. 优先复用输入中已有的同义类型和常见稳定类型，避免同一批任务中为同一语义创造多个近义标识。
3. 确无合适类型时，创建简洁、稳定、可复用的全大写英文下划线标识，例如 `STRUCTURAL_COMPOSITION`、`MATERIAL_SELECTION`、`PERFORMANCE_CHARACTERISTIC`。
4. 同时输出清晰的中文类型名称，例如“结构组成”“材料选择”“性能特征”。中文名称描述知识的语义角色，不直接照抄某个具体实体名称。
5. 类型应处于合适的抽象层级：不能过于宽泛，也不能把某个具体数值、部件名称或原句当成类型。
6. `knowledge_type` 描述整个 KU 的主导知识角色；`element_type` 描述内容要素在 KU 中承担的角色。二者可以使用相同类型，但不能为了区分而捏造不同类型。

# 内容要素粒度与组织
- 按教材原文顺序提取，优先保留作者已有的标题、编号、并列关系和层次结构。
- 不得按句子、编号、数字或 Source Block 机械拆分。能够共同回答一个子问题、构成一个分类体系、条件集合、参数组、连续流程、方法说明或论证的多段内容，应合并为一个完整内容要素。
- 内容要素可以包含多个并列项；`content` 应保留其必要的内部顺序和完整结果。
- `name` 应指出内容要素所属对象与语义角色，使其脱离相邻元素后仍能准确理解。
- Source Block 只用于程序定位 KU 原文，不决定内容要素边界；内容要素不需要复制或关联证据字段。

# 原文边界
- 只允许依据当前 KU 的 `source_text` 与 `source_blocks` 提取。
- KU 的完整原文由程序单独保存。不要因为没有证据字段而遗漏、缩写或改写内容要素。

# 输出字段
- `knowledge_type`：整个 KU 的稳定英文语义类型标识。
- `knowledge_type_name`：该类型的清晰中文名称。
- `element_type`：内容要素的稳定英文语义类型标识。
- `element_type_name`：内容要素类型的清晰中文名称。

# 输出前自检
- KU 标识、标题、主问题和边界是否与输入完全一致？
- 类型是否真正概括了知识角色，而不是具体实体、数字或原句？
- 是否错误使用了 `OTHER`、`UNKNOWN`、`MISC` 或“其他”？如果是，重新归纳类型。
- 类型标识是否稳定、简洁、可供后续 Agent 复用？中文类型名称是否准确清楚？
- 核心结论和内容要素是否覆盖整个 KU，而非只覆盖一个局部？
- 内容要素是否保留了教材作者的并列关系、内部顺序和完整语义？

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
      "knowledge_type": "STRUCTURAL_COMPOSITION",
      "knowledge_type_name": "结构组成",
      "content_elements": [
        {
          "element_id": "CE_01",
          "element_type": "STRUCTURAL_COMPONENT",
          "element_type_name": "结构组成部分",
          "name": "内容要素所属对象与语义角色",
          "content": "对应的完整要求或说明"
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
python scripts/validate_codex_result.py D:/devProject/textbook_kg_extraction_lab_v1.0/textbook_kg_extraction_lab/.kg_tasks/pending/RUN_20260927_171734_2b18ce_stage2
```

Do not edit `input.json`.
