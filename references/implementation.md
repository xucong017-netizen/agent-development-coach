# 从设计到 Python 实现

本版本按 [四阶段学习与同步协议](learning-protocol.md) 执行：唯一 design 规范自动派生文档；展示与实际执行分别记录，当前设计不要求答题或学习笔记。旧版手工文件清单仅作历史示例，以当前规范生成的文件为准。框架示例已有真实 LangGraph 节点，设计模拟与真实运行分开。

当用户需要开发教学、代码或本地运行，或需要讲解已生成代码时读取。教学设计不依赖框架安装和付费 API。

先读 [成果展示规范](visible-work.md)。当前结构明确后立即实现并展示，不必等全部模块完成。已有代码先读回实际文件，不能另造示例替代。项目文件树、每文件职责和调用关系随开发更新。

## 路线选择与版本

标准工具调用 agent 使用 `from langchain.agents import create_agent`；明确的自定义状态、节点、条件路由使用 `from langgraph.graph import StateGraph, START, END`。同一个项目只维护所需实现。`create_agent` 基于 LangGraph；LangGraph 节点可以调用 LangChain 模型或工具，也可以是普通 Python 函数。

这些入口已按 2026-10-09 官方资料核对。具体模型名、集成包、签名和持久化后端随版本变化：生成实际代码前检查用户环境的 Python 和包版本，再查当前官方文档与该版本 API。不要猜测“最新版”或固定本技能中的版本为永远正确。

优先顺序：使用用户现有项目配置；空项目才说明推荐环境和依赖，再按宿主权限安装。没有联网能力时依据现有版本，未确认的部分标注待验证；继续设计和本地模拟。版本确认后生成可复现依赖声明，不默认无上限升级。

## 按结构实现

1. 输入输出：建立入口与输出类型；缺字段先走已定义的追问路径。
2. 工具与资料：实现契约，先用明确标注的课堂目录数据。验证正常、空结果和失败；替换真实数据时保留接口。
3. 模型与提示词：接入已选供应商，模型标识从环境变量读取；配置样例给变量名，不收集或回显真实密钥。确认工具调用和结构化输出是否受支持。
4. 标准 agent：把工具传给 `create_agent`；调用时使用消息输入。不能把所有模型输出当成纯文本，也不能把工具请求直接当作最终回答。
5. 自定义图：依次定义状态、节点函数、边和条件边，`compile()` 后 `invoke()` 或 `stream()`。节点返回局部更新；不要原地改状态后又重复追加消息。消息字段可按对应版本采用 `add_messages` 或 `MessagesState`。业务计数普通字段由程序覆盖更新。
6. 真实工具循环：模型产生 tool_calls；工具执行；返回与调用 ID 匹配的 ToolMessage；模型再处理结果。可用适配版本的 ToolNode，或正确构造工具结果消息。纯确定性检索流程不必伪造工具调用消息。
7. 停止与失败：业务次数、超时和错误结果按契约处理，递归限制只作兜底。每个异常都有对用户可理解的出口。
8. 需要恢复才配置 checkpointer 及稳定的 thread_id；课堂 InMemorySaver 为进程内示例。真实恢复选合适持久化后端。跨会话长期记忆另设计 store，不把它与 checkpoints 混为一谈。
9. 需要人工审核才用对应版本的 interrupt 与 Command(resume=...)。中断所在节点恢复时可能从头执行；不要在可重放位置放不可重复的外部写操作。先验证批准、拒绝和恢复。

每次写入后读回并展示全部本次代码块：路径和实际位置、代码正文、用途、输入/动作/输出、为何这样写、改错后影响、图中节点、运行命令和实际或预期结果。新建小文件完整展示；长文件展示完整改动块及上下文。导入、数据结构、函数和入口都要解释，不能只说“代码见文件”。每次只引入当前结构所需代码；用户要完整脚手架时可集中生成，但仍分文件讲清。

第 05 模块可用 `templates/course-example/implementation/tools.py` 与对应 JSON 演示真实可执行的只读函数。明确它查询模拟目录，尚未接入模型和图。按学员主题改写，随后连接所选框架。不用 `pass`、TODO 或硬编码成功输出冒充已实现模块。

## 执行证据

只有真实执行命令才报告执行结果。生成代码未运行写“已生成未运行”；模拟函数未调用模型写“模拟路径检查通过”。出现错误用一句话说明哪个结构失效，再最小修正并重试。真实模型调用和外部操作遵守宿主权限与用户授权。不要因离线演练通过就宣称业务准确率、生产稳定性或部署完成。

设计阶段至少走正常、缺字段、查无资料、工具失败、越界请求；实现阶段对实际采用的工具、条件、循环、状态更新及恢复进行相应验证。保存检查证据，避免只有与代码文字相同的表面断言。

## 官方资料入口

- [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents)：标准 agent 入口与工具调用循环。
- [Models](https://docs.langchain.com/oss/python/langchain/models)：模型接口与能力。
- [Tools](https://docs.langchain.com/oss/python/langchain/tools)：工具定义、类型和参数。
- [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)：输出类型与校验。
- [Short-term memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)：会话内记忆。
- [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)：状态、节点、边及更新规则。
- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)：检查点和会话组织。
- [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)：暂停与恢复。
- [WorkBuddy Skill 规范](https://open.workbuddy.cn/en/docs/skill)：技能包结构与平台元信息。