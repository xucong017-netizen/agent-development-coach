# 分阶段教学、同步和验收 · 1.6.0

## 固定 15 主步骤，四阶段归组

1. 定义任务：goal、io。先用同一业务画“固定规则决定下一步”和“模型选择工具”的两张图，用输入到结果的实例展示区别，再按任务选择路线。固定工作流也有价值，不把它误称为动态智能体。
2. 最小闭环：第 03–04 步 model、prompt。状态、节点、连线先作为必要实验预览；第 08–10 步再正式深入设计，不把预览算成新的主步骤。只做设计时，先走读一条“输入 → 处理 → 输出”的路径。代码实践时现在就生成、展示并执行一个真实框架闭环，不等待工具、记忆和知识库全部设计完。
3. 扩展能力：第 05–13 步 tools、knowledge、memory、state、nodes、edges、routing、loops、control。一次添加一种能力，展示加入前后的图、代码差异及失败路径。不采用的能力保留模块，写原因，不生成空文件。
4. 验收交付：evaluation、delivery。完整用例至少包含正常、类型错误、缺参、无资料、工具失败、越界；不用工具时写清失败用例不适用的验证依据。真实模型质量另测。

learning_stage 从当前步骤自动派生，不单独手写。默认按唯一步骤表的 01–15 顺序推进，明确跳转仍使用原编号。学员尚未回答前不注入教师示例答案；浏览其他模块不会自动完成当前模块。

## 唯一设计来源

teaching-state.json 的 design 是规范：component_decisions、system、graph、contracts。contracts 包含 inputs、outputs、state_fields、nodes、tools、routes、loop_limits、tests。modules[].decision、agent_graph、decisions 是同步兼容视图；不要同时写相互矛盾的值。

每轮写入结构化规范后执行：

```text
python "<技能目录>/scripts/design_engine.py" --project "<项目目录>" --sync
```

脚本自动生成 agent-design/design-summary.md、design-contracts.md、design-spec.json、architecture.mmd。这些文件不可直接从网页编辑；改课堂决定、业务图或契约后保存即可同步。文件名被手工文件占用时保留原文件并报告冲突。旧 agent-design.md 等手写文件作为历史记录保存，先迁移规范再更新 artifacts 指向当前生成章节。所有讲解都要读回实际文件，不能只用内存内容。

节点契约示例：

```json
{"respond":{"reads":["question"],"writes":["answer"],"source":"implementation/minimal_nodes.py","function":"respond","preview_update":{"answer":"仅供设计走读的预期回答"}}}
```

分支使用 op=eq / empty / nonempty / default；字段必须存在，每个分支有唯一 default，to 与实际连线一致。循环记录 counter、max、exit；节点真实增加计数，exit 为实际边。动态智能体 system 还需 dynamic_node 与 decision_field；该字段由模型节点写入并决定工具调用或结束。

只做设计使用 delivery="仅设计"，不要求 Python 源文件绑定。代码模式需要每个运行节点绑定实际函数。代码和文档不会因保存图而自动实现；sync.implementation_pending 明确列出尚未应用的变更。布局移动无复核；图示措辞只复核讲解；业务变化按实际依赖复核，保留原学生答案。修改源码后更新 artifacts 的实际内容与讲解，不能把过期检查继续称为通过。

## 成果展示与实际验证

- 实际成果：存在真实文件，artifacts 与当前文件内容对应。
- 展示：presentation_status=shown，已经展示正文、逐段解释与输入输出。
- 验证：runs、trace 和源文件哈希；旧运行只作历史参考。

不安排理解题、理解评分或学习笔记，不以答题阻挡进入下一步。旧项目记录保留，不修改为虚假的通过。业务设计缺少信息时问具体设计问题；学员已经给出的要求直接使用。

每轮按 [设计台交互协议](ui-workflow.md) 读取待处理需求，先完成设计和图的真实修改，再记录应用依据。不能把自然语言需求提交当成图已经修改。

实现变更完成后，教练查看当前代码、重新执行并核对结果，记录具体应用依据：

```text
python "<技能目录>/scripts/design_engine.py" --project "<项目目录>" --applied "prompt,nodes,evaluation" --basis "已修改 answer_courses 的来源约束，实际框架输出对应目录；异常路径保持可结束"
```

代码模式无当前设计实际框架执行证据、或证据源文件已经变化时，脚本拒绝确认应用。该操作是教练判断，运行成功不会自动清空未应用项；未涉及的结构不要顺手标通过。

## 运行模式及真实记录

设计模拟不执行项目函数，仅用 preview_update 走图。框架模式按保存的图构建实际 LangGraph 并调用实际项目函数，模型部分明确标为模拟。真实模式才使用真实模型 API；密钥从环境读取，不进入网页、规范和日志。工作台 Python 必须是已安装框架依赖的那个环境。代码实践由教练在项目虚拟环境安装 templates/requirements-runtime.txt，再用该环境的 Python 调用已有启动脚本；生命周期机制不变。

最小闭环直接复用 templates/minimal_nodes.py 的 respond；只复制这一文件，并把图写成 START → respond → END，定义 question/answer 字段和节点契约。先读代码解释，再执行框架模式。明确这是最小实验，不通过完整项目验收。

完整固定工作流示例使用 templates/example-state.json 与 templates/course-example；动态决策对比使用 templates/agent-comparison-state.json，同一目录的 agent_nodes.py 提供 agent_model/agent_tools。对比案例另建项目，保留原学员项目，不用示例覆盖。动态案例用 LangGraph 自定义模型/工具循环和 LangChain 消息类型；标准 LangChain create_agent 路线由教练按需求生成相应入口，并适配实际 trace，不能冒充已经执行标准 Agent。

```text
python "<技能目录>/scripts/run_design.py" --project "<项目目录>" --mode framework --question "Python"
```

网页“执行并记录轨迹”会保存证据。CLI 输出可供教练检查，但只有保存到当前项目的 runs/trace 才显示为课堂证据。每个步骤包含 before、update、after、输出、错误、耗时、源文件/函数/行号。运行中的等待状态与运行后的逐节点回放分开；不把预录动画伪装成实时执行。

## 最终验收必须实际执行

```text
python "<技能目录>/scripts/design_engine.py" --project "<项目目录>" --sync --audit
```

检查返回 passed，而不是进程是否成功退出（审计命令本身完成不等于设计通过）。验收覆盖结构决定、正文与实际文件、图的连通/退出/循环、字段来源、分支与工具契约、用例和文档同步。仅 passed=true 时才能把 design_status 写为“设计完成”，并再次保存检查。代码执行、真实模型效果、上线可用性仍分别报告。第 8 项 WorkBuddy 真机启动与集成测试由用户进行，此版本不更改启动脚本或代测宿主环境。

框架资料：[LangGraph 图接口](https://docs.langchain.com/oss/python/langgraph/graph-api)、[工作流与智能体](https://docs.langchain.com/oss/python/langgraph/workflows-agents)。
