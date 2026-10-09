# 零基础智能体开发教练 · Agent Development Coach

在 **WorkBuddy** 中一步步讲解、展示并辅助设计 **LangChain / LangGraph 智能体**的教学 Skill，适合没有编程和开发经验的学员，也适合教师课堂演示。

**A Chinese beginner-friendly WorkBuddy skill for step-by-step LangChain and LangGraph agent design, component diagrams, classroom demonstrations, and optional Python implementation.**

每一步都遵循：**说明作用 → 拆解结构 → 图示 → 自然语言填写 → 展示实际文件与内容 → 逐段讲解 → 输入输出检查 → 保存进度**。完成后导出完整智能体设计与实施交接材料。

## v1.1.0：看得见每一步写了什么

本版修复“步骤做了却没有展示具体内容”的教学缺口。每步必须读回实际文件，在聊天中展示本次正文或代码；说明各文件用途与调用关系；逐块解释输入、动作、输出、设计理由及改错后影响；给检查命令和实际或预期结果，再进入下一步。

开发教学在当前结构确定后立即实现并讲解，不把代码全部推迟到课程最后。仅设计模式也展示实际任务说明、提示词、字段表和契约正文。看板增加文件地图、完整内容、代码分块讲解和执行证据；“已写入”与“已展示”分别记录。

附带可独立运行的模拟目录查询示例，包含 tools.py、课程 JSON 和 15 模块的示例设计正文。函数查询已本地验证，真实模型与 LangGraph 尚未接通。

### 更新旧项目

下载新 ZIP，在 WorkBuddy 的技能管理中更新原技能，或用当前版本提供的替换/重新导入入口。避免同时启用两个同名版本。保留原学员项目及进度，回到原对话使用：

```text
使用 agent-development-coach 1.1.0。
不要重置我的项目，先读取之前已生成的文件。
从当前步骤开始补讲：展示实际内容、文件职责、每段代码的输入输出和调用关系。
之前只标记完成但没有展示的步骤也请补讲，再继续开发。
```

可以直接说“展示这一步写了什么”“解释每段代码”“列出全部文件和作用”或“补讲前面内容”。旧进度保持兼容；不存在的文件会明确说明，不从完成状态推断已经生成。

## 下载与安装

- [下载 v1.1.0 技能 ZIP](https://github.com/xucong017-netizen/agent-development-coach/releases/download/v1.1.0/agent-development-coach.zip)
- [查看发布页](https://github.com/xucong017-netizen/agent-development-coach/releases/tag/v1.1.0)
- [仓库内 ZIP 备份](dist/agent-development-coach.zip)
- [课堂示例看板](examples/classroom-board.html)：下载后用浏览器离线打开，GitHub 文件页不会直接执行 HTML。

1. 在 WorkBuddy 中打开“专家·技能·连接器 → 技能”。
2. 进入“添加技能”，通过当前版本的上传/导入入口选择下载的 ZIP。
3. 安装并启用，在对话中选择该技能，或明确说“使用 agent-development-coach 技能”。

ZIP 根目录直接包含 `SKILL.md`，附带 `references/`、`templates/`、`scripts/`，不需要再次压缩。只上传单个 SKILL.md 会缺少课程资料和看板脚本。

元信息根据 [WorkBuddy 官方技能规范](https://open.workbuddy.cn/docs/skill) 编写。当前仓库不假定具体技能安装路径，也不会自动安装框架、注册账户或部署服务。

## 学员启动语

```text
使用 agent-development-coach 技能。
我没有开发经验，请带我从零设计一个智能体。
每次只讲一个结构，先说明作用和组成，再给图示，
让我用自然语言填写，检查后再进入下一步。
每一步展示实际写入内容、文件用途；有代码时逐段解释并给输入输出例子。
我想做一个课程咨询助手，先只完成设计。
```

替换最后一句即可用于企业知识问答、信息查询或自己的业务场景。还没想好任务时说“先帮我选一个简单场景”。默认第一轮停在任务设计，等待学员回答。

## 教师演示启动语

```text
使用 agent-development-coach 技能，进入教师演示模式。
以课程咨询助手为模拟案例，按 15 个模块展示整个设计过程。
每个模块都要有局部结构图，最后展示业务运行总图，
并演练正常请求、缺信息、查无资料、工具失败和越界请求。
把所有模拟数据与演示假设明确标注出来。
```

## 15 个教学模块

| 步骤 | 结构 | 完成什么 |
| --- | --- | --- |
| 01 | 任务、范围与验收 | 明确服务对象、核心任务和成功标准 |
| 02 | 输入、输出与架构路线 | 定义输入输出样例，选择实现路线 |
| 03 | 模型 | 定义模型职责和所需能力，可先模拟 |
| 04 | 提示词与消息 | 写清角色、规则、上下文和回答方式 |
| 05 | 工具及调用契约 | 定义调用场景、参数、结果与失败处理 |
| 06 | 知识与检索 | 选择可靠资料，设计检索及引用方式 |
| 07 | 记忆 | 区分会话笔记与跨会话长期记忆 |
| 08 | 状态与更新规则 | 定义共享字段和更新方式 |
| 09 | 节点 | 拆分职责，明确每个节点读写什么 |
| 10 | 连线、入口与终点 | 拼接有入口和出口的成功路径 |
| 11 | 条件分支与路由 | 设计缺信息、无资料等不同出口 |
| 12 | 循环、重试与停止 | 为反复执行设置次数和停止条件 |
| 13 | 持久化、人工审核与恢复 | 按需设计存档、暂停、批准和拒绝 |
| 14 | 输出检查、评估与观察 | 对照用例检查路径与可见结果 |
| 15 | 整体设计与实施交接 | 导出完整方案并按需进入代码实践 |

可选能力先讲清作用，再决定采用或不采用。不要求每个项目都加入向量库、长期记忆、人工审核或多智能体。

LangChain 提供模型、消息、工具和标准 agent 构建能力；LangGraph 用状态、节点和边组织自定义流程。标准 `create_agent` 基于 LangGraph，两者不是互斥选项。教学中会讲清框架内部处理的部分，避免让学员维护两套重复实现。

## 支持的模式和指令

- **学员共创**：默认一次推进一个设计问题，学员用自然语言回答。
- **教师演示**：按明确标注的模拟案例展示全过程。
- **代码实践**：当前结构明确后，当场生成、展示和分块讲解对应 Python 代码；需要时带领本地运行，不等待全部设计结束。

| 需求 | 示例指令 |
| --- | --- |
| 恢复进度 | 继续上次的智能体设计 |
| 进入下一步 | 下一步 |
| 换一种讲法 | 我不懂状态，换生活类比再举个例子 |
| 单独讲某结构 | 只看工具这一部分，解释它的输入输出 |
| 修改前面设计 | 修改第 2 步，输出改成表格，检查后续受影响部分 |
| 查看全局 | 看总图，说明哪些结构已经确定 |
| 查看数据流 | 模拟运行一个失败请求，逐节点展示状态变化 |
| 完成设计交付 | 导出完整设计和实施交接说明 |
| 开始实现 | 按已经确定的结构逐步生成 Python 代码 |

## 图示与离线看板

每个模块都有局部结构图，完成填写后逐步形成业务运行总图。支持 Mermaid 和文字箭头图；有 Python 时可以生成自包含 HTML 看板。

看板提供 15 个模块卡片、当前决定、局部图、运行总图及可见轨迹回放。轨迹切换时高亮对应业务节点。看板不依赖 CDN，不调用模型，也不会把进度数据发送到外部服务。

看板同时显示实际文件表、正文与源代码、每块代码的用途和输入输出、检查命令与执行证据。模板尚未填写时显示“成果待展示”；已完成设计不自动算作已完成讲解。

在仓库目录生成课堂示例看板：

```bash
python scripts/render_board.py templates/example-state.json --output classroom-board.html
```

生成空白教学看板：

```bash
python scripts/render_board.py templates/teaching-state.json --output blank-board.html
```

脚本使用 Python 3 标准库，没有第三方依赖。没有 Python 时仍可用聊天中的图示上课。学员进度由 WorkBuddy 保存到项目的 `agent-design/teaching-state.json`；网页只展示已保存的数据，更新 JSON 后需要重新生成看板。

示例看板只保存正常请求与缺主题请求两条**模拟轨迹**。无资料、工具失败、越界请求和完整文件交付仍需继续检查；它不是已经运行或评估通过的真实智能体。

1.1.0 的看板默认展开工具模块，完整展示 tools.py 与 course_catalog.json，并按导入、加载目录、查询函数和运行入口讲解。示例整体设计仍在进行中；只有独立查询函数的结果为真实本地执行，业务图轨迹仍为模拟。

## 最终设计产物

学员项目保存在所选项目目录的 `agent-design/`，与技能安装目录分开。设计完成后交付：

- `agent-design.md`：目标、范围、组件决定、提示词和处理策略。
- `architecture.mmd` 与 `architecture.txt`：完整运行图及文字图。
- `contracts.md`：工具契约、节点契约、状态表与路由表。
- `state-schema.json`：业务状态规范。
- `test-cases.md`：代表性用例与验收条件。
- `walkthrough.md`：正常和异常请求的逐节点演练。
- `handoff.md`：实施顺序、待接入能力和验证说明。
- `teaching-state.json` 与可生成时的 `design-board.html`：学习进度和看板。

设计完成、代码生成、真实运行分别记录。没有执行代码时不会称“运行已验证”。API 密钥通过环境变量配置，不写入设计、进度和图示。

## 仓库结构

```text
.
├── README.md
├── SKILL.md
├── references/
│   ├── curriculum.md
│   ├── project-contract.md
│   ├── visualization.md
│   ├── implementation.md
│   ├── visible-work.md
│   └── classroom-example.md
├── templates/
│   ├── teaching-state.json
│   ├── example-state.json
│   └── course-example/          # 示例设计正文、tools.py 与课程 JSON
├── scripts/
│   └── render_board.py
├── examples/
│   └── classroom-board.html
└── dist/
    └── agent-development-coach.zip
```

安装优先用发行版 ZIP。仓库源码便于维护与修改；仓库中的 README、示例和 dist 目录不是技能 ZIP 内的额外依赖。

## 验证范围

已检查平台元信息、ZIP 根目录结构、相对资料引用、两个进度模板、15 个局部图、示例总图与轨迹节点一致性、图的入口与出口可达性、无效图数据拒绝，以及 HTML 文本转义。已实际运行看板脚本，并在浏览器检查模块展开、轨迹切换、节点高亮和桌面/窄屏布局。

尚未在用户的 WorkBuddy 实例中完成导入和完整教学对话验证，也没有运行真实 LangChain / LangGraph 项目或真实模型接口。建议首次导入后检查：只问当前任务、无 API Key 仍能教学、可恢复进度、上游修改能触发下游复核、教师模式能展示全过程。

## 搜索关键词

**仓库定位**：`agent-development-coach`；`user:xucong017-netizen agent-development-coach`。

**中文关键词**：WorkBuddy 智能体开发教学、零基础智能体开发、LangChain LangGraph 教学 Skill、智能体结构可视化、智能体开发教练。

**English keywords**: WorkBuddy agent skill, LangChain LangGraph beginner tutorial, agent development coach, AI agent education, visual agent design, step-by-step agent development.
