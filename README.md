# 教材知识单元 AI 抽取实验台

一个面向教材知识图谱前期实验的小型工具，核心只做两阶段：

1. **Stage 1：KP → KU 完整划分**
2. **Stage 2：KU → 属性与内容要素结构化抽取**

暂不做 KP/KU 关系、ExamPoint、共同考查、Neo4j/Milvus 入库。

当前版本仍处于实验阶段，但已经支持 Prompt 版本管理、实验状态恢复、结构化结果校验和完整 HTML 图谱报告导出。

## 设计共识

- 输入 KP 只有：`kp_id`、`kp_name`、完整原文、起止页码。
- KU 是对 KP 原文的**有序完整分区**，不是重点摘要。
- 所有 KU 原文按顺序组合后必须精确还原 KP 原文。
- Source Block 只是技术定位地址，不是业务实体，也不是 KU。
- Stage 1 边界人工确认后才允许进入 Stage 2。
- 模型负责语义判断；代码负责 Coverage、Gap、Overlap、顺序和 Schema 等确定性校验。
- Stage 1 只负责 KU 边界、标题和统领性主问题；当前默认 Prompt 为 `ku_split/v1.4`。
- Stage 2 在已确认的 KU 内抽取属性和内容要素；当前默认使用最新的 `ku_extract/v1.3`。
- `knowledge_type`、`element_type` 是开放式语义类型，同时输出清晰的中文类型名称，不使用 `OTHER` 作为新结果兜底。
- 内容要素不关联证据字段；KU 完整原文由程序单独保存。

## 两种运行模式

### 模式 A：Codex Workspace（适合初期）

模式 A 不要求 API Key。Streamlit 应用生成一个待办目录：

```text
.kg_tasks/pending/<run>_stage1/
  task.md
  input.json
```

然后在**当前 Codex 项目会话**中输入：

> 处理最新任务

Codex 会依据仓库根目录 `AGENTS.md` 和 `skills/textbook-kg-extractor/SKILL.md` 执行任务，并写回：

```text
result.json
```

回到 Streamlit 点击“加载 Codex 结果”即可。

> 说明：Streamlit 按钮本身不能“自动借用”当前 Codex/ChatGPT 账号额度发起一次隐藏模型调用。模式 A 是一个 workspace handoff：由 Codex 当前会话完成语义任务，因此使用当前 Codex 会话的用量。

### 模式 B：API 自动调用（适合稳定后的批量实验）

复制环境变量：

```bash
cp .env.example .env
```

填写 OpenAI-compatible API：

```env
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=...
LLM_MODEL=...
```

应用会直接调用 `/chat/completions`。也可配置兼容该接口的其他模型服务。

## 启动

建议 Python 3.11+。

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

也可以直接使用：

```bash
# Windows
start.bat

# macOS/Linux
./start.sh
```

默认访问地址：<http://localhost:8501/>

首次启动后，应用会自动从 `.kg_tasks/pending/` 中载入最近任务的 KP 示例。项目当前包含本地实验数据库、检查点和任务样例，便于开箱查看运行结果。

如果你在 Codex 中打开本仓库，可以直接让 Codex执行上述安装和启动命令。

## Mode A 推荐操作

1. 启动 Streamlit。
2. 输入 KP ID、名称、页码、完整原文。
3. 选择“模式A｜Codex Workspace”。
4. 点击“开始 KU 划分”。
5. 回 Codex 输入“处理最新任务”。
6. 回页面点击“加载 Codex Stage 1 结果”。
7. Coverage PASS 后检查/修改 KU，点击“确认 KU 划分”。
8. 点击“开始属性抽取”。
9. 再回 Codex输入“处理最新任务”。
10. 加载 Stage 2 结果，导出 JSON / HTML。

刷新页面后，应用会自动恢复最近一次实验状态。点击“清空当前结果”可以删除当前检查点并重新开始。

## 结果与报告

最终结果可以导出为：

- JSON：包含 KP、KU、原文范围、完整 KU 原文、知识类型和内容要素。
- HTML：包含 KP → KU → 内容要素的交互式实体—关系—属性图。点击图中节点可以查看属性，每个 KU 还会显示完整原文和内容要素表。

## 目录

```text
app.py
AGENTS.md
prompts/
  ku_split/v1.0.md ... v1.4.md
  ku_extract/v1.0.md ... v1.3.md
schemas/
services/
repositories/
skills/textbook-kg-extractor/SKILL.md
references/知识单元拆分规范V2.1.md
.kg_tasks/pending/
data/
tests/
```

## 当前 V1.0 有意保持简单

- 人工修改 KU 暂时通过 JSON 编辑器完成；后续可增加“拆分/合并/拖拽边界”可视化操作。
- Source Block 采用确定性标点/换行切分，仅用于定位，未来可优化但不能影响 100% 原文重构。
- SQLite 只保存运行历史。
- Prompt 以文件版本管理，便于 A/B；历史版本保留，运行时默认选择当前最新稳定版本。
- `data/app.db` 和 `data/active_experiment.json` 是项目随附的本地实验示例，不代表生产数据库。

## GitHub 上传注意事项

- 不要上传 `.env`、API Key、个人教材或未脱敏的运行记录。
- 本示例仓库保留当前 `data/` 和 `.kg_tasks/pending/` 内容，是为了展示历史运行和任务格式；如果替换为真实教材，请先脱敏。
- `.gitignore` 只忽略密钥、虚拟环境、Python 缓存和日志，不会忽略当前示例实验数据。
