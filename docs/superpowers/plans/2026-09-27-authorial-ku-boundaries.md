# Authorial KU Boundaries Implementation Plan

> **For agentic workers:** Execute the checked tasks in this session. This repository has no Git metadata, so no commit step is available.

**Goal:** Shift Stage 1 from atomizing independently testable facts to preserving textbook authorial explanation modules.

**Architecture:** Version both prompts to preserve previous experiments. Route mode A through an updated repository reference and Skill, then revise the current task result without changing its input blocks.

**Tech Stack:** Markdown prompts and instructions, JSON result, Python validation script.

---

### Task 1: Versioned prompt and reference

**Files:** Create `prompts/ku_split/v1.1.md`, `prompts/ku_extract/v1.1.md`, `references/知识单元拆分规范V2.1.md`.

- [x] Write the new boundary criteria and Stage 2 handling of an integrated `core_conclusion`.
- [x] Check the prompts retain the existing Stage 1 and Stage 2 JSON fields.

### Task 2: Mode A instruction alignment

**Files:** Modify `AGENTS.md`, `skills/textbook-kg-extractor/SKILL.md`.

- [x] Point semantic decisions to the V2.1 reference and define KU as an authorial explanation module.
- [x] Confirm the complete partition and frozen Stage 2 boundaries remain explicit.

### Task 3: Rework the current Stage 1 result

**Files:** Modify `.kg_tasks/pending/RUN_20260927_102727_a05b43_stage1/task.md` and `result.json`.

- [x] Record the user-approved revision without changing `input.json`.
- [x] Partition the 266 source blocks into the five authorial modules identified in the design.
- [x] Run `python scripts/validate_codex_result.py .kg_tasks/pending/RUN_20260927_102727_a05b43_stage1` and confirm `VALIDATION PASS`.
