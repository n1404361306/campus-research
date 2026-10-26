# 第十课：新增一个真正的 Agent 工具

本课实现 `estimate_project_schedule`：根据输入的功能预计工时、每周投入、截止周数和预留比例，计算单人项目工期。代码位于 `campus/tools.py`，通过既有 YAML 工具配置接入，不修改 DeerFlow 的 Agent 核心循环。

先明确验证边界：生产工具代码和正式配置已经修改；教学脚本使用真实 `langchain.create_agent` / LangGraph 执行工具，但模型回复、参数选择、纠错和最后回答均为预设。没有请求 DeepSeek，没有外部 MCP，没有 API 费用。完整 Gateway 与其广泛回归仍受上游扫描器缺失阻塞。

## 1. 输入和计算约定

例子：登录8小时、发布失物12小时、搜索10小时；每周投入10小时，四周后截止；默认额外预留20%。

| 名称 | 意义 | 例子 |
| --- | --- | --- |
| `features` | 功能列表，每项有名称和预计工时 | 登录8小时等 |
| `hours_per_week` | 每周投入小时数 | 10 |
| `deadline_weeks` | 截止前剩余周数 | 4 |
| `buffer_percent` | 额外预留工时百分比 | 默认20 |

计算：基础30小时，预留6小时，总计36小时。36除以10为3.6，按完整周向上取整为4周。四周容量40小时，因此按输入估算可容纳；三周容量30小时则缺6小时。

输入工时本身是估计。程序只能保证按既定规则算出结果，不能保证估计准确或项目一定按时完成。模型应先询问缺失信息，不将自己猜测的工时冒充用户提供的数据。

## 2. 定义参数：用 Pydantic 写一张输入表

`BaseModel` 是 Pydantic 提供的基类。继承它来描述有哪些字段、每个字段是什么类型、允许哪些值。

```python
class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: list[FeatureEstimate] = Field(min_length=1, max_length=30, ...)
    hours_per_week: int = Field(strict=True, ge=1, le=80, ...)
    deadline_weeks: int = Field(strict=True, ge=1, le=104, ...)
    buffer_percent: int = Field(default=20, strict=True, ge=0, le=100, ...)
```

这段省略了说明文字，完整可运行代码以 `campus/tools.py` 为准：

- `class` 定义一种数据结构；`ScheduleInput` 是我们起的名字。
- `int` 是整数；`list[FeatureEstimate]` 是由多个功能估算组成的列表。
- `Field` 提供规则与说明。`ge` 表示大于等于，`le` 表示小于等于。
- `strict=True` 拒绝把字符串 `"10"` 或布尔值 `True` 当成整数。
- `default=20` 表示省略该参数时用20。
- `extra="forbid"` 拒绝拼错或多余参数，而非静默忽略。
- `description` 会成为工具 schema 的一部分，帮助模型理解参数。

每个功能由另一种输入结构 `FeatureEstimate` 描述：名称去除首尾空白后长1到80字符，预计工时为1到2000的整数。功能列表最多30项，避免无限输入。

约束有两种不同作用：参数说明提示模型如何填写；程序校验决定填错时是否允许执行。说明文字本身不能强制模型诚实，也不能发现用户的工时估计不合理。

## 3. 写工具函数

```python
@tool("estimate_project_schedule", args_schema=ScheduleInput)
def estimate_project_schedule(
    features: list[FeatureEstimate],
    hours_per_week: int,
    deadline_weeks: int,
    buffer_percent: int = 20,
) -> dict:
```

- `def` 定义函数；括号内列出输入参数。
- `: int` 等是类型标注；`-> dict` 表示返回一个字典。
- `@tool` 是装饰器，在函数定义后将其包装成 LangChain 工具对象。
- 显式工具名供模型请求和程序路由使用。
- `args_schema=ScheduleInput` 指定运行前用哪一张输入表验证参数。
- 函数的三引号说明会用作工具描述：什么时候使用、需要什么输入、有什么限制。

装饰后应使用 `.invoke(...)` 或 `.ainvoke(...)` 进入工具校验与执行流程，不把它当成原来的普通函数随意调用。

核心计算：

```python
base_hours = sum(feature.estimated_hours for feature in features)
buffer_hours = ceil(base_hours * buffer_percent / 100)
total_hours = base_hours + buffer_hours
estimated_weeks = ceil(total_hours / hours_per_week)
capacity_hours = hours_per_week * deadline_weeks
```

`=` 将右边结果保存到左边的名字。第一行逐项取工时并相加；`ceil` 从 `math` 导入，表示向上取整。其余行按公式计算。

结果用字典返回，包含原始工时、预留工时、总工时、预计周数、截止前容量、是否容纳、工时缺口与估算假设。其中：

```python
"fits_deadline": total_hours <= capacity_hours,
"shortfall_hours": max(0, total_hours - capacity_hours),
```

`<=` 的结果是 `True` 或 `False`；`max` 取较大值，避免工时缺口出现负数。本工具不联网、不修改 todos、不写报告文件。

## 4. 让 Agent 认识它：名称、说明、参数 schema

模型收到的是工具的名称、描述与参数结构，不是 Python 函数源码。框架可从 Pydantic 结构生成 JSON Schema。

```python
convert_to_openai_tool(estimate_project_schedule)
```

此处是已安装 LangChain 的本地格式转换函数；使用这个函数不代表向 OpenAI 发请求，也不产生费用。

生成的 schema 告诉模型：工具叫什么、适用场景、哪些参数必填、数值范围、默认值等。模型输出工具调用后，程序再验证参数并执行函数。

## 5. 接入本项目的正式工具配置

校园模板和本机 `config.yaml` 已增加：

```yaml
tool_groups:
  - name: campus:planning

tools:
  - name: estimate_project_schedule
    group: campus:planning
    use: campus.tools:estimate_project_schedule
```

这是新增项示意，不是要求删掉原有工具列表。

- `name` 与 `@tool` 的名称保持一致。
- `group` 是分组，便于自定义 Agent 筛选允许使用的工具。
- `use` 冒号左边是 Python 模块路径，右边是模块中的工具对象名称。

已有加载链：

1. `deerflow/tools/tools.py` 的 `get_available_tools` 读取工具配置并按分组等条件筛选。
2. `resolve_variable(cfg.use, BaseTool)` 导入模块，找到对象，检查它是否为工具。
3. 主 Agent 工厂进行后续授权、策略处理，最终把工具交给 `create_agent`。
4. 调用时由框架找到对应工具，并把执行结果写为 `ToolMessage`。

本地 Python 工具不是 MCP 工具，不需要 MCP Server 或 `tools/list` 网络握手，也未加入 deferred MCP 目录。若自定义 Agent 使用工具分组允许列表，需要包含 `campus:planning`；登记配置不代表能绕过原有授权策略。

Gateway 从 `backend/` 工作目录启动，而 `campus/` 在项目根目录。启动器 `campus.py` 已将项目根目录加入子进程 `PYTHONPATH`，保留原值；`campus/__init__.py` 使目录成为可导入包。没有把业务工具放进上游框架目录。其他启动方式需自己提供该导入路径。

本机现有配置已经补上登记项。`configure` 的原有行为仍是不覆盖已有配置；旧安装仅重新执行 `configure` 不会自动获得新工具。新模板与本机配置都要检查，修改后需重启后端。

## 6. 第一种调用：直接测试工具

在项目根目录打开本机虚拟环境 Python：

```powershell
.\backend\.venv\Scripts\python.exe
```

然后输入：

```python
from campus.tools import estimate_project_schedule

result = estimate_project_schedule.invoke({
    "features": [
        {"name": "登录", "estimated_hours": 8},
        {"name": "发布失物", "estimated_hours": 12},
        {"name": "搜索", "estimated_hours": 10},
    ],
    "hours_per_week": 10,
    "deadline_weeks": 4,
})
print(result)
```

这条调用不需要模型。它检验的是参数校验和工具本身。

## 7. 第二种调用：通过真实 Agent 图执行

退出交互 Python 后，在项目根目录运行：

```powershell
.\backend\.venv\Scripts\python.exe campus/lessons/lesson10_agent_tool.py
```

脚本从校园模板读取登记项，用项目真实的 `resolve_variable` 加载工具，再传入：

```python
agent = create_agent(
    model=ScriptedToolModel(responses=replies),
    tools=[schedule_tool],
)
```

这里的模型是预设回复的测试替身。它检查传入工具名称，返回手写的 `AIMessage(tool_calls=...)`；它没有理解用户问题、没有向模型供应商绑定工具、没有自主选择工具。LangGraph 图、工具节点执行、Pydantic 校验、函数计算和 ToolMessage 真实运行。

正常消息顺序：

```text
HumanMessage：用户需求
AIMessage：预设工具名、参数和调用ID
ToolMessage：真实计算结果，同一调用ID
AIMessage：预设结束语
```

`tool_call_id` 用于把结果与对应调用关联起来，尤其在多工具调用时不能混淆。

## 8. 看一次真实的参数错误回传

```powershell
.\backend\.venv\Scripts\python.exe campus/lessons/lesson10_agent_tool.py --invalid-first
```

第一次预设 `hours_per_week=0`。校验拒绝它，框架将异常变成 `status="error"` 的 ToolMessage。随后模型替身返回预设的修正参数10，再次真实执行并成功。

直接 `.invoke` 遇到错误会抛出 `ValidationError`；教学 Agent 图使用框架默认的工具错误处理把参数错误反馈为消息。不要把这种处理误认为任意异常都能自动恢复，也不要声称预设修正是模型自主纠错。

证据保存到忽略目录：

- `campus/lessons/outputs/lesson10-success.json`
- `campus/lessons/outputs/lesson10-invalid-first.json`

可查看 schema、预设调用、真实工具结果与对应ID。没有密钥、模型推理或外部网页内容。

## 9. 回归验证

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p test_campus_project_tools.py -v
.\backend\.venv\Scripts\python.exe -m unittest discover -s campus -p test_launcher.py -v
```

覆盖正常与不足工期、预留与周数取整、边界相等、严格类型、空列表、非法字段、输入不被修改、schema、配置导入路径和真实图中的成功/错误消息。启动器测试还验证 Gateway 工作目录可以导入工具，以及已有配置和导入路径保留。

本课实际结果：12项工具测试、5项启动器测试通过；正常与先错误后修正的两个教学命令均执行通过，Ruff 检查通过。

项目广泛离线 pytest 与 blocking-I/O 检查也已尝试，但收集测试时均因缺少上游 `deerflow.skills.skillscan.orchestrator` 中断，不能声称全套通过或正式 Gateway 已验收。未关闭安全功能、删改扫描逻辑或用替身绕过此导入问题。

## 10. 练习与面试表达

先把直接调用的截止周数从4改成3，预测结果，再执行：预计仍需4周，截止前只能投入30小时，缺6小时。然后把 `hours_per_week` 改成0，观察校验错误。再思考为何工具校验了参数格式，也不能知道用户是否低估了某个功能。

面试介绍：“我通过项目现有 YAML 工具接口新增了本地开发工期估算工具，用 Pydantic 定义严格参数和边界，将确定性计算交给程序。工具输出结构化结果与估算前提；缺失工时要求先询问。我补充了正常、边界、错误参数、配置加载和真实 LangGraph 工具消息回传测试。离线测试采用预设模型回复，不把它当成真实模型选择工具的验收。核心 Agent 框架仍复用 DeerFlow。”
