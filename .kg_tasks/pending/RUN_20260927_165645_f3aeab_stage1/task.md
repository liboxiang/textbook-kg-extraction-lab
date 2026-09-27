# Pending textbook KG task

Stage: STAGE1
Run ID: RUN_20260927_165645_f3aeab
Created: 2026-09-27T16:56:45

## Instructions

# 角色与任务
你是职业教育教材知识结构专家。请将一个完整 KnowledgePoint（KP）原文，无损划分为若干连续、有序的 KnowledgeUnit（KU）。本阶段只确定 KU 边界、标题和统领性主问题，不做知识类型、属性、内容要素、关系或考点抽取。

# KU 的含义
KP 是本次输入的整体知识范围。KU 是教材作者围绕一个相对完整的主题、对象或专业任务组织的一段完整论述，是后续整体阅读、检索、归纳、讲解和输出的基本单位。

一个 KU 可以包含组成、分类、条件、参数、步骤、作用、原因、例外、示例和补充说明等多个内部部分。不要把能够单独命题的局部内容自动提升为 KU；`main_question` 应统领整个模块的完整结果。

# 判断边界
1. 先通读 KP，识别作者依次展开的知识对象、专业任务、论述目的和上下位关系。标题、编号、段落和过渡句是理解作者结构的证据，但不是机械边界。
2. 同一主题下的并列分项、组成部分、分类项、条件、指标、做法、解释、例外和示例，默认属于同一候选 KU，除非它们已经转向独立主题或独立专业任务。
3. 只有当相邻内容同时满足以下条件，才建立新 KU：
   - 知识对象、专业任务或论述目的发生实质转换；
   - 前后两部分都能独立形成完整、可整体输出的知识结果；
   - 后一部分不是前一部分的组成、分类、条件、参数、步骤、例外、示例、原因或补充说明。
4. 如果后文省略了主语或对象，必须检查它是否承接前文的上位主题。存在这种语义依赖时，不能因为换了编号、段落或小标题就孤立拆分。
5. 如果边界存在疑问，优先保留教材作者的完整论述和上下文，不以增加 KU 数量为目标。

# 原文覆盖硬约束
- 所有 Source Block 必须且只能属于一个 KU，保持原文顺序，范围首尾连续。
- 按 KU 顺序拼接 Source Block 后，必须精确还原 KP 原文，不得遗漏、重叠、倒序或改写。
- Source Block 只是程序定位地址，不是知识实体，也不决定 KU 边界。
- 不得虚构 Block ID、页码、偏移量或原文没有的知识。

# 标题与主问题
- `title` 概括整个 KU 的知识对象和论述主题，不得只命名其中一个分项。
- `main_question` 用一个完整专业问题统领整个 KU，答案应覆盖该 KU 的主要分支；不要把每个分项分别改写成多个问题。
- 标题和主问题不得提前引入原文没有的类型判断或外部知识。

# 输出前自检
- 每个 KU 是否对应作者的一段可整体阅读和输出的完整论述？
- 是否错误地按标题、编号、句子、段落、长度或可命题性切碎？
- KU 之间是否发生了真正的知识对象或专业任务转换？
- 所有 Source Block 是否连续、无遗漏、无重复地覆盖全文？

# 输出格式
只输出符合下列结构的合法 JSON 对象，不输出 Markdown 或解释：
{
  "knowledge_units": [
    {
      "temp_ku_id": "KU_01",
      "order_index": 1,
      "title": "完整论述模块的主题",
      "main_question": "统领该模块完整结果的专业问题？",
      "start_block_id": "S0001",
      "end_block_id": "S0005"
    }
  ]
}


## Input
Read `input.json` in this directory.

## Required action
Perform the task yourself using the current Codex model and repository instructions. Write only the final JSON object to `result.json`. Then run:

```bash
python scripts/validate_codex_result.py D:/devProject/textbook_kg_extraction_lab_v1.0/textbook_kg_extraction_lab/.kg_tasks/pending/RUN_20260927_165645_f3aeab_stage1
```

Do not edit `input.json`.
