# Stage 2 V1.2 and Refresh Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 Stage 2 V1.2，并让页面刷新后自动恢复最近一次实验进度。

**Architecture:** 新提示词作为不可变版本文件保存。当前实验状态由独立 JSON 检查点服务持久化，Streamlit 仅在关键状态转换时保存，并在页面启动时恢复。

**Tech Stack:** Python, JSON, Streamlit, unittest

---

### Task 1: 测试 Stage 2 V1.2 约束

- [ ] 新增测试，要求标题和主问题冻结、禁止机械原子化、要求最小充分证据并限制跨章节补全。
- [ ] 运行测试，确认因 V1.2 不存在而失败。
- [ ] 新建 `prompts/ku_extract/v1.2.md` 并使测试通过。

### Task 2: 测试并实现当前实验检查点

- [ ] 新增保存、加载、清除、损坏文件容错测试。
- [ ] 运行测试，确认因检查点服务不存在而失败。
- [ ] 实现 `services/experiment_checkpoint.py` 并使测试通过。

### Task 3: 接入 Streamlit 状态转换

- [ ] 应用启动时恢复检查点。
- [ ] 在 Stage 1/2 各关键转换后保存检查点。
- [ ] 清空当前结果时同步删除检查点。
- [ ] 运行编译、回归测试和 Streamlit AppTest。

