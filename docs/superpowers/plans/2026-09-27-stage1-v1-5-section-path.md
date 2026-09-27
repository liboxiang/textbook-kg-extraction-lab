# Stage 1 V1.5 Section Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Stage 1 splitting so the model preserves authorial topic hierarchy, merges progressive subsections, and returns each KU's `section_path`.

**Architecture:** Add an optional hierarchy field to Stage 1 and final KU models so old results remain readable. Introduce Prompt V1.5 with a mandatory hierarchy-first workflow and adjacent-KU merge audit, then propagate the field through validation, Stage 2 payloads, final extraction, graph attributes, and reports.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, unittest, Markdown prompts.

---

### Task 1: Add failing prompt and model tests

**Files:**
- Modify: `tests/test_stage1_prompt.py`
- Modify: `tests/test_stage2.py`

- [ ] Assert V1.5 is the default prompt and contains hierarchy-first, overarching-question, progressive-discourse, long-table, adjacent-merge-audit, and `section_path` rules.
- [ ] Assert Stage 1 validation and Stage 2 final assembly preserve `section_path`.
- [ ] Run `python -m unittest discover -s tests -v` and confirm the new assertions fail before implementation.

### Task 2: Implement `section_path` propagation

**Files:**
- Modify: `schemas/models.py`
- Modify: `services/coverage_validator.py`
- Modify: `services/stage2_validator.py`
- Modify: `services/report_graph.py`
- Modify: `services/report_renderer.py`

- [ ] Add `section_path: list[str] = Field(default_factory=list)` to split, resolved, structured, and final KU models.
- [ ] Copy the field through Stage 1 resolution and Stage 2 final assembly without changing KU boundaries.
- [ ] Expose the hierarchy in graph attributes and report details.
- [ ] Run focused model and report tests and confirm they pass.

### Task 3: Create and activate Prompt V1.5

**Files:**
- Create: `prompts/ku_split/v1.5.md`
- Modify: `app.py`

- [ ] Base V1.5 on V1.4 without sample-specific terminology.
- [ ] Require an internal section hierarchy before boundary decisions.
- [ ] Require progressive subsections that share one knowledge object to remain together.
- [ ] Add the overarching-question merge test and mandatory adjacent-KU merge audit.
- [ ] State that length, tables, numbering, and information density are not split reasons.
- [ ] Add `section_path` to the output schema and set V1.5 as the Stage 1 default.

### Task 4: Verify the complete change

**Files:**
- Modify: `README.md`

- [ ] Document Stage 1 V1.5 and `section_path`.
- [ ] Run `python -m unittest discover -s tests -v` and Python compilation checks.
- [ ] Restart Streamlit and confirm HTTP 200 so the user can test the new default prompt.
