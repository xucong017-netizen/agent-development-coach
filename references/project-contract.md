# 项目进度与交付契约 · 1.6.0

学员数据保存在项目 agent-design/，与 Skill 安装目录分开。复用已有项目，不重置学员回答。详细执行规则见 [学习协议](learning-protocol.md)。

## 状态规范

teaching-state.json 为 UTF-8、schema_version=1。title 为业务项目，mode 为学员共创/教师演示/代码实践，delivery 为仅设计/设计与代码/设计代码与本地运行。current_module 为当前模块 ID，learning_stage 为 define/minimum/expand/deliver，design_status 为进行中/需复核/设计完成。

design.component_decisions 存放 15 个结构决定；design.system 写 kind=workflow/agent/undecided 和 reason。动态智能体额外标 dynamic_node、decision_field。design.graph 是唯一业务图；design.contracts 含 inputs、outputs、state_fields、nodes、tools、routes、loop_limits、tests。学习模块的局部 graph 是教学示意，不能当成业务节点。

decisions、modules[].decision、agent_graph 为兼容视图，由同步器派生。网页可通过课堂决定与图编辑修改兼容视图，保存时合并到唯一规范；同时修改为矛盾值会拒绝。WorkBuddy 每轮修改后调用 --sync，结合 .workbench 中的上一版规范记录精确影响。不要手工修改同步器的历史记录。

modules 保留原 15 个 ID。status 为 pending/active/done/skipped/review；decision 写具体决定，不采用写理由；origin 写学员决定/助手建议/演示假设；check 写实际检查依据。presentation_status 为 pending/shown/review。artifacts 保存实际文件、正文、逐段解释及验证结果，详细格式见 [成果展示](visible-work.md)。旧项目的 mastery、exercise 与 notes 仅保留为历史，不生成、不展示为当前任务，也不作为设计验收条件。

trace 包含 run、step、node、mode、before、input、update、after、output、basis、source、duration_ms、error。runs 保存模式、设计哈希、源文件哈希、状态、输出和错误。实施状态与设计状态分开：implementation.verification 写真实证据和限制。sync.implementation_pending 标新设计尚未应用的结构，reviews 记录实质影响。open_questions 用“阻断：”表示交付阻断，“实施待办：”表示后续选择。

## 文件与同步

局部流程、整体定位与内部教学拆解按 [结构映射协议](structure-views.md) 维护；`design.structure_bindings` 是展示对应关系，不把教学图节点写进业务运行图。

--sync 自动派生四个文件：design-summary.md（全部结构的当前设计）、design-contracts.md（状态/节点/工具/路由/循环/测试契约）、design-spec.json（结构化规范导出）、architecture.mmd（业务图）。所有文件均在 agent-design/。不把这些文件再当成独立编辑来源；旧手写文档保留历史并迁移，不覆盖不带生成标记的同名文件。

按需要再交付 test-cases.md、walkthrough.md、handoff.md、运行依赖和 implementation/ 中的实际代码，内容从规范和真实运行记录整理。最终展示完整文件树、用途、调用关系、所有实际正文及代码解释。导出网页副本；网页副本不等于实时项目。

## 完成检查

实际执行 design_engine.py --project "<项目>" --sync --audit。检查返回 passed，而不是命令退出码。自动验收检查全部结构的决定、检查依据、成果展示记录、真实成果内容、START/END 连通性、可结束路径、循环计数和出口、字段的上游来源、节点函数、分支覆盖、工具失败契约、六类测试、文档同步和阻断问题。

仅设计不要求 Python 绑定或实际模型调用；仍必须有节点读写契约及设计走读。代码模式需要真实函数绑定和源文件；新设计未应用时不能交付。最小闭环不通过完整 15 模块验收是正常状态。

只有 passed=true 才允许标“设计完成”。没有真实执行只能报告设计检查或设计模拟；真实框架+模拟模型不证明真实模型效果。记录业务用例通过与代码完成时，还须实际对照输出，不能仅凭 executed 状态。
