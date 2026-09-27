---
name: textbook-kg-extractor
description: Partition a complete textbook knowledge point into ordered, lossless knowledge units, then extract structured KU attributes and content elements. Use for pending tasks in this repository.
---

# Textbook KG Extractor

Use this skill for the two-stage textbook extraction workflow in this repository.

## Stage 1: KP -> KU partition
- Treat the full KP source text as the complete material that must be partitioned, not summarized.
- Every source block must be assigned to exactly one KU, preserving original order.
- Use headings and numbering to understand the author's thought structure, then set boundaries by complete explanation modules rather than by formatting alone.
- A KU should be independently understandable and useful for whole-unit output. Being independently testable is not sufficient reason to split an item from its parent module.
- Keep related classifications, materials, conditions, quantitative requirements, examples, continuous steps, and exceptions inside the KU; use one overarching `main_question`.
- Output only the Stage 1 schema requested by the task.

## Stage 2: KU -> structured knowledge
- Boundaries are frozen. Never merge, split, add, or remove source blocks.
- Extract `knowledge_object`, `core_conclusion`, `knowledge_type`, and `content_elements`.
- Make `core_conclusion` a source-grounded synthesis of the whole KU; preserve the author's internal items as ordered content elements.
- Preserve source grounding using only the KU's block IDs.
- Do not add knowledge absent from the source.

## Required reference
Read `references/知识单元拆分规范V2.1.md` when boundary decisions are difficult.
