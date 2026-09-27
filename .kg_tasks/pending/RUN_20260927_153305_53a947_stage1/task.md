# Pending textbook KG task

Stage: STAGE1
Run ID: RUN_20260927_153305_53a947
Created: 2026-09-27T15:33:05

## Instructions

# 角色与任务
你是职业教育教材知识结构专家。请将一个完整 KnowledgePoint（KP）原文，无损划分为若干连续、有序的 KnowledgeUnit（KU）。本阶段只确定边界和统领性问题，不做属性、内容要素、关系或考点抽取。

# KU 在知识结构中的位置
KP 是本次输入的整体知识范围。KU 是教材作者围绕一个主题组织的完整论述模块，也是后续可以整体阅读、检索、讲解和输出的单位。分类、组成、条件、参数、步骤、例外和示例是 KU 内部的内容要素，留待 Stage 2 抽取。

KU 可以包含若干相互关联的子问题。`main_question` 用一个统领性问题概括模块的完整结果，不要求每个 KU 只表达一条原子结论，也不以能否单独出一道题作为拆分充分条件。

# 边界判断顺序
1. 先通读 KP，识别作者依次论述的主题与层级，找出每个主题的对象、目的和完整说明范围。标题、编号、段落是作者思路的重要证据，但都不是自动边界。
2. 先将同一主题下的结构组成、分类、材料选择、适用条件、技术指标、构造做法、原因、例外和补充说明放入同一候选 KU。它们即使可分别命题，也可能共同构成作者的一个完整结果。
3. 只有以下条件同时成立，才在相邻内容之间新建 KU：
   - 后续内容转向另一项相对独立的论述主题或专业任务；
   - 前后两部分各自能独立形成完整、可整体输出的知识结果；
   - 后一部分不是前一部分的组成、分类、条件、参数、步骤、例外、示例或解释。
4. 如果一个作者标题下确实出现两项互不依赖的专业任务，可以在标题内部拆分；如果跨标题仍在完成同一论述，应合并。边界取决于知识逻辑，不取决于字数、Token 数或标题层级本身。
5. 不确定时，优先保留完整上下文，交给人工审核；不要为了增加 KU 数量强行拆分。

# 特别防止过细拆分
- 先识别各段内容是否共享同一个上位知识对象，并共同回答同一个统领性问题；如果是，应优先视为一个完整候选 KU。
- 并列出现的组成、分类、条件、参数、步骤、作用、原因、例外、示例和补充说明，属于完整论述内部的内容角色，不能仅因编号、段落、小标题或篇幅不同而自动拆分。
- 如果后一部分依赖前文才能确定其对象、条件、范围或结论，说明两者存在语义依赖，不宜把后一部分孤立为 KU。
- 某项内容能够单独命题，不代表它已经形成可脱离上下文整体输出的独立知识结果。
- 只有知识对象、专业任务或论述目的发生实质转换，并且前后内容均能独立形成完整知识结果时，才建立新的 KU。
- 标题、引言、定义、过渡句、例子、补充说明、例外和空白 Source Block 应归入其所服务的完整论述模块，不能孤立成 KU。

# 原文完整覆盖硬约束
1. 所有 Source Block 必须且只能属于一个 KU，保持原文顺序，范围首尾连续。
2. 按 KU 顺序拼接其 Source Block 后，必须精确还原 KP 原文；不得遗漏、重叠或倒序。
3. Source Block 只是定位地址，不是知识实体，也不决定 KU 边界。
4. 不修改 Source Block 文本，不虚构 Block ID、来源页码或原文没有的专业知识。

# 输出前自检
- 每个 KU 是否对应作者的一段完整论述，能作为整体输出？
- 原文的编号条目是否仍留在共同的上位主题内？
- 某个边界是否仅因“能分别出题”或标题、编号、长度而产生？如是，重新判断。
- `title` 是否概括整个模块，`main_question` 是否统领其中的子问题？
- 所有 Source Block 是否连续、无遗漏、无重复地覆盖全文？

# 输出格式
只输出符合下列结构的合法 JSON 对象，不输出 Markdown 或解释：
{
  "knowledge_units": [
    {
      "temp_ku_id": "KU_01",
      "order_index": 1,
      "title": "完整论述模块的主题",
      "main_question": "统领该模块的完整专业问题？",
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
python scripts/validate_codex_result.py D:/devProject/textbook_kg_extraction_lab_v1.0/textbook_kg_extraction_lab/.kg_tasks/pending/RUN_20260927_153305_53a947_stage1
```

Do not edit `input.json`.
