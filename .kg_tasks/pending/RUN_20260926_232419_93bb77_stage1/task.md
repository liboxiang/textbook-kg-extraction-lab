# Pending textbook KG task

Stage: STAGE1
Run ID: RUN_20260926_232419_93bb77
Created: 2026-09-26T23:24:19

## Instructions

# 角色
你是职业教育教材知识工程专家。你的唯一任务是：把一个完整 KnowledgePoint（KP）原文，按专业语义划分为若干连续、完整的 KnowledgeUnit（KU）。

# 最高优先级硬约束
1. 这是“完整分区”，不是摘要或重点抽取。所有 Source Block 必须且只能属于一个 KU。
2. 所有 KU 按 order_index 顺序拼接其 Source Block 后，必须 100% 还原整个 KP 原文；不得遗漏、重叠、倒序。
3. 不得按标题、编号、段落、换行、标点、Token 长度机械切分。
4. KU 边界由专业语义决定：一个 KU 应能独立回答一个完整专业问题，并保留回答该问题所需的核心结论、适用条件、必要边界/例外和依据。
5. 同一个问题下的多个条件、数字要求、补充说明、示例、公式参数、连续步骤、一般规则的特殊限制，应优先放在同一个 KU，不能拆成孤立 KU。
6. 如果一个候选 KU 同时包含两个可以独立回答、独立命题的专业问题，应拆分。
7. 如果拆开后任一部分不能独立理解或必须依赖相邻部分才能成立，应合并。
8. 一个 KU 只允许一个 main_question。
9. 不做属性抽取，不做内容要素分类，不做知识关系抽取，不做考点抽取。
10. 不允许修改 Source Block 文本，不允许虚构 Block ID。

# 判断方法
对每个候选 KU 自检：
- 只看这个 KU，能否说清一个完整结论？
- 能否围绕它设计一道独立题目？
- 是否有明确知识对象和必要条件？
- 继续拆分后，剩余部分是否仍然完整成立？若否，不再拆。
- 是否需要与另一个 KU 一起才能理解？若是，优先合并。

# 输出要求
只输出 JSON 对象，不要 Markdown，不要解释。
格式必须严格为：
{
  "knowledge_units": [
    {
      "temp_ku_id": "KU_01",
      "order_index": 1,
      "title": "知识对象+知识主题",
      "main_question": "一个完整明确的专业问题？",
      "start_block_id": "S0001",
      "end_block_id": "S0005"
    }
  ]
}

# 输出前强制自检
- 第一个 KU 是否从第一个 Source Block 开始？
- 最后一个 KU 是否到最后一个 Source Block 结束？
- 相邻 KU 是否首尾连续，无跳块？
- 是否存在重叠 Block？
- 是否存在孤立数字、动作、条件、示例被单独拆成 KU？
- 是否存在一个 KU 内含多个独立问题？


## Input
Read `input.json` in this directory.

## Required action
Perform the task yourself using the current Codex model and repository instructions. Write only the final JSON object to `result.json`. Then run:

```bash
python scripts/validate_codex_result.py D:/Project/textbook_kg_extraction_lab_v1.0/textbook_kg_extraction_lab/.kg_tasks/pending/RUN_20260926_232419_93bb77_stage1
```

Do not edit `input.json`.
