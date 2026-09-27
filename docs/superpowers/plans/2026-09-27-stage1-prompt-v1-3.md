# Stage 1 Prompt V1.3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增不含当前教材样本对象的 Stage 1 V1.3 提示词，并将其设为默认版本。

**Architecture:** 保留旧版本文件不变，新建 `prompts/ku_split/v1.3.md`。应用仍通过现有提示词加载器选择版本，只修改默认版本常量；证据链继续由现有校验器和 Stage 2 payload builder 提供。

**Tech Stack:** Markdown prompts, Python, pytest, Streamlit AppTest

---

### Task 1: 添加 V1.3 内容约束测试

**Files:**
- Create: `tests/test_stage1_prompt.py`

- [x] 测试 V1.3 存在、不包含道路样本词、不包含 V1.2 专节标题，并包含通用边界概念。
- [x] 运行测试并确认因 V1.3 尚不存在而失败。

### Task 2: 新建 V1.3 并切换默认版本

**Files:**
- Create: `prompts/ku_split/v1.3.md`
- Modify: `app.py`

- [x] 以 V1.1 为基础新建 V1.3，将过细拆分规则改写为知识对象、统领性问题、内容角色和语义依赖规则。
- [x] 将 `DEFAULT_STAGE1_PROMPT_VERSION` 改为 `v1.3`。
- [x] 运行提示词测试并确认通过。

### Task 3: 回归验证

**Files:**
- Verify: `services/coverage_validator.py`
- Verify: `services/payload_builders.py`

- [x] 运行现有核心测试函数及新增 unittest（环境未安装 pytest）。
- [x] 编译应用和提示词加载模块。
- [x] 使用 Streamlit AppTest 确认 Stage 1 默认选中 V1.3 且应用无异常。

