# Codex instructions for this repository

This repository is a textbook knowledge-unit extraction lab.

## Primary workflow
When the user asks you to "处理最新任务", "处理待办知识抽取任务", or equivalent:

1. Find the newest directory under `.kg_tasks/pending/` that contains `task.md` and does not yet contain a valid `result.json`.
2. Read `task.md` and `input.json` completely.
3. Follow the task instructions and any later user revisions. For semantic decisions on new tasks, apply `skills/textbook-kg-extractor/SKILL.md` and `references/知识单元拆分规范V2.1.md`.
4. Write ONLY the final JSON object to `<task_dir>/result.json`. Do not wrap JSON in Markdown fences.
5. Run `python scripts/validate_codex_result.py <task_dir>`.
6. If validation fails, fix `result.json` and validate again.
7. Do not modify the KP source text. Do not invent source pages, offsets, or source blocks.

## Stage 1 constraints
- Stage 1 only partitions the entire KP into ordered KUs.
- Every source block must belong to exactly one KU.
- No gaps, no overlaps, no reordered blocks.
- A KU is an authorial explanation module that can be read and output as a complete result.
- Headings and numbering reveal the author's structure but are not automatic boundaries; a separately testable item is not by itself a new KU.
- Each KU has one overarching `main_question`; associated subquestions, conditions, numbers, examples, and exceptions remain inside it for Stage 2 extraction.

## Stage 2 constraints
- Stage 2 does not change KU boundaries.
- Extract structured attributes/content elements only from each confirmed KU source text.
- The complete KU source text is preserved by the program; content elements do not output or associate evidence fields.
- Use open semantic `knowledge_type` and `element_type` values with clear Chinese type names; do not generate `OTHER` as a new-result fallback.
- Do not extract cross-KP relationships, ExamPoint, co-exam relations, or course/question relations.
