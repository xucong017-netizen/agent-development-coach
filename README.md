# 零基础智能体开发教练 · agent-development-coach

适用于 WorkBuddy 的中文 Skill。逐步帮助没有开发经验的学员设计 LangChain / LangGraph 智能体，展示实际文件、代码、逐段解释和结构图。内置本地 HTML 工作台，调用 Skill 时沿用自动启动方式，项目文件双向同步。

## 下载与调用

下载 [v1.4.0 技能包](https://github.com/xucong017-netizen/agent-development-coach/releases/download/v1.4.0/agent-development-coach.zip)，在 WorkBuddy 的技能管理中安装 ZIP；不同宿主版本若使用目录导入，解压后选择含 SKILL.md 的 agent-development-coach 目录。

首次：“使用 agent-development-coach，带我做一个课程咨询智能体。我没有开发经验。”

继续：“使用 agent-development-coach，继续当前项目，先读取网页改动和实际文件。”

普通学员只安装技能包，工作台已在里面。可选 local-agent-workbench.zip 是独立调试包。agent-workbench.html 是离线成果副本，不能实时写回项目。启动脚本保持 v1.3.0 机制，第 8 项 WorkBuddy 真机安装、权限和启动集成由使用者测试。

## v1.4.0 的七项改进

1. 可执行设计验收：查结构决定、实际文件和内容、字段来源、入口出口、循环上限、分支、理解记录与阻断项；不允许空图被标完成。
2. 唯一结构化设计：课堂决定与架构图保存到 design，自动生成摘要、契约、JSON 和 Mermaid 图。显示设计同步与代码待应用状态。
3. 四阶段教学：定义任务 → 最小闭环 → 扩展能力 → 验收交付；保留全部 15 个结构，代码模式在早期运行实际框架。
4. 固定工作流与动态智能体对比：同一业务任务的两种决策方式、图和示例；动态案例包含模型/工具循环及匹配的 ToolMessage ID。
5. 生成、展示、理解、执行分别记录。学生答错会收到反馈，概念题正确后还要由教练核对对自己项目的解释。
6. 按依赖精确复核：移动节点不重置进度，文字改动复核讲解，业务契约/连线/代码变化复核相关结构。保留旧答案与原因。
7. 三种运行证据：设计模拟、真实 LangGraph+模拟模型、真实框架+真实模型。逐节点回放输入、更新、完整前后状态、输出、错误、耗时和实际代码位置。

## 环境与数据

本地设计工作台只需 Python 3.10+，标准库即可运行。代码实践使用项目 Python 环境安装 templates/requirements-runtime.txt，工作台也用该 Python 启动。已验证版本为 LangGraph 1.2.14、langchain-openai 1.7.0；LangChain 标准 create_agent 路线由教练按实际场景生成，附带动态对比使用自定义 LangGraph 和 LangChain 消息类型。

真实模型在运行时环境配置 OPENAI_API_KEY 和可选 OPENAI_MODEL。没有密钥可用框架模式；不得把模拟回答称为真实模型效果。不把密钥写进 Skill、网页和项目进度。

网页每 2.5 秒检查文件更新；有草稿时保留草稿，写入有备份和版本冲突检查。生成的设计文件只读，修改课堂决定、架构地图或契约再同步。图修改不自动改业务代码，执行成功也不自动标学生理解通过。

旧项目会保留进度和代码。旧手写文档作为历史记录，教练迁移到唯一规范后更新实际成果讲解；同名手写文件冲突时拒绝覆盖。

## 验证范围

已用实际 LangGraph 测试正常、缺参、无资料、工具失败、越界和类型错误；测试动态工具循环、源代码与状态轨迹、布局不复核、业务变更精确依赖、理解错题、文档同步、验收拒绝、冲突与路径边界。真实模型效果未调用验证；WorkBuddy 真机测试由使用者完成。

技能入口：[SKILL.md](SKILL.md)。完整教学与操作协议：[learning-protocol.md](references/learning-protocol.md)。下载包在 [Releases](https://github.com/xucong017-netizen/agent-development-coach/releases)。

## 搜索关键词

`agent-development-coach`、`xucong017-netizen agent-development-coach`、`WorkBuddy LangGraph 零基础 智能体 教学 Skill`、`LangChain LangGraph 可视化 开发 工作台`。
