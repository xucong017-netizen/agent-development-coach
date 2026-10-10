# 零基础智能体开发教练 · agent-development-coach

面向 WorkBuddy 的中文 Skill，让没有开发经验的使用者用自然语言逐步设计 LangChain / LangGraph 智能体。内置本地「智能体设计台」，调用 Skill 时自动启动，设计、图示和实际项目文件同步更新。

## 下载与使用

下载 [v1.6.0 技能包](https://github.com/xucong017-netizen/agent-development-coach/releases/download/v1.6.0/agent-development-coach.zip)，按 WorkBuddy 当前的技能导入方式安装。使用目录导入时选择包含 SKILL.md 的目录。已有项目继续读取原进度和代码，不用示例覆盖。

首次调用：“使用 agent-development-coach，带我做一个课程咨询智能体。我没有开发经验。”

继续：“使用 agent-development-coach，继续当前项目，读取看板改动和待处理需求。”

普通使用只需技能包，页面和启动器已包含在里面。local-agent-workbench.zip 是可选独立调试包；agent-workbench.html 是离线成果副本，不能实时写回项目。启动脚本沿用 v1.3.0；WorkBuddy 真机安装、权限和启动集成仍由使用者测试。

## v1.6.0：本步局部流程与整体结构定位

- “本步局部 / 整体流程”切换，保持同一个当前步骤。局部图显示真实作用节点与一跳前后衔接；整体图保留全部流程，红色定位本步节点和受控连接。
- 显示“这一步控制什么”“在整体中对应哪里”、本步最近业务修改、逐节点读取/写入字段和实现入口。红色表示作用范围，版本新增/更新/移除使用独立图例。
- 内部教学图可展开，拆解参数检查、函数调用、结果与错误处理，并明确不是额外的业务运行节点。
- 模型、提示词等配置可以共同约束一个真实模型节点；状态、验证和交付注明跨整体作用；未采用结构不虚构节点，缺少对应关系明确提示待补齐。
- 结构映射随项目保存；修改节点、连接或契约后刷新局部与整体图。展示说明更新不改业务代码、不使原运行证据失效。旧项目在原目录继续，由 Skill 补齐 design.structure_bindings。

更新后调用：“使用 agent-development-coach，继续当前项目，补齐每一步的局部流程、控制规则和整体对应关系，更新设计台。”打开自动启动器返回的地址。

![本步局部流程](https://raw.githubusercontent.com/xucong017-netizen/agent-development-coach/main/docs/images/step-local.png)
![整体中的本步定位](https://raw.githubusercontent.com/xucong017-netizen/agent-development-coach/main/docs/images/step-overall.png)

## v1.5.1：统一 15 步与双向进度同步

- 聊天、设计台、教学模板共同使用 templates/step-registry.json 的 15 个编号、名称和顺序。安装、创建文件、调试等是步骤内操作，不另计主步骤。
- 聊天讲解前先同步当前步骤和具体操作；设计台点击结构、阶段或前后步骤会写回同一份项目进度。网页约每 2.5 秒读取更新，WorkBuddy 在下一轮调用时读取网页选择。
- 顶部和任务卡显示“第 XX/15 步 · 统一名称”，阶段由步骤自动派生。切换不自动标完成；未保存草稿阻止在线切换，版本冲突保留原成果。
- 旧项目保留设计、代码和历史，按固定 ID 整理名称与顺序。更新后调用：“使用 agent-development-coach，继续当前项目，迁移到统一 15 步并同步设计台。”打开自动启动器返回的地址，避免继续使用旧服务页面。

## v1.5.0：围绕设计任务重新设计看板

- 主看板呈现当前任务、整体执行图、具体设计决定、节点职责和这次变化，文件、运行和交付分别放到对应视图。
- 15 个结构均说明“接收什么 → 实际做什么 → 产生什么”，配合明确标注的课程例子和实际成果，避免只给抽象名词。
- 执行流程显示真实节点、连线、分支与出口；组成视图显示模型、提示词、工具等全部设计决定。点击节点可查看读写字段、后续步骤和实际源码位置。
- 每次实际设计变化自动保留前后版本，绿色表示新增、金色表示更新、红色表示移除。坐标移动不产生业务变化记录；配置修改在组成卡中体现。
- 可直接编辑设计决定、实际文本文件和结构图。新增环节会重接流程，契约或实现未补齐时明确显示待办，不能冒充已经运行。
- 自然语言设计需求保存到项目，Skill 每轮优先读取、修改实际设计与图，再记录处理结果。页面自动检测并刷新成果。
- 移除理解检查和学习笔记，不以答题作为继续设计或完成设计的门槛；保留对实际成果、业务路径和代码一致性的验证。
- 深绿导航、浅色画布、清晰的卡片层次与响应式布局，图支持完整适配、缩放和前后对照；不依赖外部字体或 CDN。

![智能体设计台的真实界面](https://raw.githubusercontent.com/xucong017-netizen/agent-development-coach/main/docs/images/design-studio.png)

## 设计需求如何改变图

在 WorkBuddy 中直接要求：“给查询之后加一个人工审核步骤，并更新看板。”Skill 按任务修改节点、连线、契约和实际文件，执行同步后，正在打开的看板自动更新图和变化列表。

也可在看板填写“希望这次设计怎样改变？”并提交，再在 WorkBuddy 说“处理看板新需求”。网页没有独立模型或后台唤醒 WorkBuddy 的接口，提交只保存待处理需求；下次 Skill 执行后才显示真实设计成果。提示词等配置变化不虚构额外执行节点，应在组成视图查看。

## 保留的开发能力

四阶段路线：定义任务 → 最小闭环 → 按需要扩展 → 验收交付，保留全部 15 个结构。design 是唯一规范，自动生成摘要、契约、JSON 和 Mermaid 图；实际正文、完整代码、逐段解释、文件职责和调用关系均可查看。

支持固定工作流与模型/工具动态循环对比；运行区分设计模拟、真实 LangGraph 搭配模拟模型、真实框架搭配真实模型。轨迹保存节点前后状态、输入、更新、输出、错误、耗时、源码位置和源文件哈希。

## 本地环境与同步

设计工作台只需 Python 3.10+ 标准库。代码实践由 Skill 在项目 Python 环境安装 templates/requirements-runtime.txt，并使用同一环境启动。真实模型从环境读取 OPENAI_API_KEY 和可选 OPENAI_MODEL；密钥不写入网页、进度或日志。

页面每 2.5 秒检查更新。有网页草稿时保留草稿并提示项目更新；保存有备份和版本冲突检查。自动生成的文档只读，修改对应设计再同步。图保存不自动实现代码；实施待应用项与实际运行证据单独记录。旧项目的笔记和答题数据保留为历史，不参与当前设计验收。

## 验证范围

实际框架测试覆盖正常、类型错误、缺参、无资料、工具失败、越界和动态工具循环；验证文档同步、真实图差异、需求排队与应用、不生成答题字段、旧答题不阻挡验收、文件冲突与路径边界。浏览器检查节点详情、代码跳转、设计决定保存、宿主修改后自动刷新、前后图、直接插入环节和响应式布局。真实模型质量与 WorkBuddy 真机环境仍需使用者测试。

技能入口：[SKILL.md](SKILL.md)。设计台交互：[ui-workflow.md](references/ui-workflow.md)。教学与同步：[learning-protocol.md](references/learning-protocol.md)。全部下载：[Releases](https://github.com/xucong017-netizen/agent-development-coach/releases)。

## 搜索关键词

`agent-development-coach`、`xucong017-netizen agent-development-coach`、`WorkBuddy LangGraph 零基础 智能体 教学 Skill`、`LangChain LangGraph 可视化 开发 工作台`。

## 开发者验证

项目 Python 环境安装 templates/requirements-runtime.txt 后，运行 `python -m unittest discover -s tests -v` 可执行 34 项设计、局部/整体对应、双向步骤同步与真实框架测试。

工作台渲染验证：安装 Node.js 后运行 `node tests/test_studio_views.js examples/agent-workbench.html`，在隔离文档中检查全部 15 个结构、局部/整体作用范围、未采用状态及历史视图分离。
