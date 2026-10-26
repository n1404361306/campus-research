# CampusResearch 验证记录

日期：2026-10-21。本机 Windows，Python 3.12.10，Node.js 24.19.0。上游基线：`8b68832f32a0bb724e1ca39983ae0c43284a0c40`。

## 已验证

| 项目 | 结果与边界 |
| --- | --- |
| DeerFlow 配置解析 | 校园 YAML 与 MCP JSON 通过原生配置解析器，版本 61，`parallel-search` 已启用 |
| Parallel MCP 真实连接 | 初始化、工具发现、网页检索、读取官方文档通过；匿名连接，无搜索 API Key |
| DeerFlow 原生 MCP 加载器 | 实际发现 `parallel-search_web_search`、`parallel-search_web_fetch` |
| 后端启动 | Gateway、LangGraph runtime、SQLite 初始化成功 |
| 后端接口 | `/health`、`/api/models`、`/api/features`、`/api/mcp/config`、`/api/v1/auth/me` 返回 200 |
| 前后端连接 | 从 3000 端口访问 `/api/models`、`/api/mcp/config` 返回 200；预览状态接口明确返回未配置模型 |
| 前端静态检查 | `pnpm check`，ESLint 与 TypeScript 通过 |
| 生产构建 | `pnpm exec next build --webpack` 通过，保留完整原有路由及文档页面 |
| 语言相关回归 | 原有 i18n 3 项测试通过 |
| 原有 prompt overlay 回归 | `backend/tests/test_prompt_overlays.py` 8 项通过 |
| 启动器回归 | 配置保留、缺失模型时本地失败、环境变量覆盖共 3 项通过 |
| 页面交互 | 校园首页的桌面/手机布局、上游署名、工作台入口；中文需求示例填入和预览提示检查通过 |

MCP 的非敏感原始状态位于本机忽略文件 `campus/local-verification.json`；可运行 `campus/verify_mcp.py` 重新联网验证。构建与静态检查日志分别在 `logs/campus-build.log`、`logs/campus-check.log`。

浏览器交互测试对工作台使用了上游已有的后端请求 mock，以独立验证界面行为；上表后端接口与 MCP 检查使用真实服务。两类证据分别记录，不将 mock 响应当成模型实测。

## 真实 Agent 全流程验收

使用用户本地 DeepSeek 密钥、`deepseek-flash`、上游 `PatchedChatDeepSeek` 和真实 Parallel MCP，未使用模型或搜索 mock。测试选题为校园失物招领系统：单人八周，会 Python 与基础 Web，每月预算不超过100元。

会话：`f2f242ed-5bde-4bea-91b0-393fd85f203f`，可在本机打开 `http://127.0.0.1:3000/workspace/chats/f2f242ed-5bde-4bea-91b0-393fd85f203f`。

| 检查 | 实测证据 |
| --- | --- |
| 多 Agent | 两个 general-purpose 子任务同时启动，分别核实开源项目和官方技术文档；收到两个 `task_completed`，界面显示两个子任务已完成 |
| Plan | 实际调用 `write_todos`；最终五个条目全部为 completed |
| 工具按需加载 | 实际调用 `tool_search` 后使用 `parallel-search_web_search`、`parallel-search_web_fetch` |
| 自动压缩 | SSE 中出现 `summary_text`，消息条数曾由 13 减至 10，继续交付时也观察到压缩；不是手工调用 compact API 冒充自动触发 |
| 报告生成 | 实际调用 `write_file`，输出七个章节、三条技术路线、八周交付与验收计划、六个来源 URL |
| 产物登记 | `present_files` 将 `/mnt/user-data/outputs/campus-research-report.md` 写入线程 artifacts |
| 接口下载 | HTTP 200，Content-Disposition 为 attachment，文件 11423 字节 |
| 浏览器流程 | 无 mock 打开会话、点击报告展开 Markdown 预览、点击下载控件，浏览器保存成功 |
| 文件一致性 | 浏览器与 API 下载 SHA-256 均为 `88840c0fd81ff77926a1a694d668a4af87e100083523468172c508ce26df1eb6` |

原始非敏感证据保存在本机忽略目录 `campus/live-results/`：`acceptance.json`、`campus-research-report.md`、`browser-download.md`、`report-browser.png`。脚本为 `campus/live_acceptance.py`、`campus/browser_acceptance.mjs`。证据不保存密钥或模型思考内容。

这次不是一次无故障运行：最初的匿名搜索触发免费额度限流，子任务与主任务随后耗尽累计 Token 预算。限制检索轮数、提高有界累计预算并提前压缩后，第二次运行完成了搜索、两个子任务和报告写入，但 LangGraph 的 100 步限制在登记下载前中断。已将默认执行步数上限设为 250，并在**同一会话续跑**补齐产物登记与计划状态，最终运行状态 success；续跑没有重复检索。没有宣称新的上限已在另一个全新检索会话中重复验证。

本轮相关回归：上游 DeepSeek 适配、summary_text、tool_search 共 48 项通过；前端模型推理与本地设置共 15 项通过；启动器 3 项通过；Python 新验收脚本 Ruff 检查通过。前端静态检查、Webpack 生产构建、校园界面 2 项 E2E 均通过。生产服务已重启，真实浏览器再次验证新会话默认 Ultra，以及报告预览和下载。新浏览器默认 Ultra + low，旧浏览器保留原有设置，需自行切换到 Ultra。

质量边界：报告的章节和来源数量已自动检查，实际约 2629 个汉字，未达到测试输入中 1200–1800 字的长度目标。第二个参考项目仅取得搜索摘要，报告已明确标为待验证。尚未逐句独立核实所有结论，也未证明多次生成稳定性、性能或成本；多轮改变选题范围的质量仍未验证。单次流程通过不等于所有报告事实均正确。

## 环境问题及处理

- 本机全局 Node.js 18 过旧，启动器使用本机现有的 Node.js 24；没有修改全局 Node 设置。
- 生产构建使用 Webpack。初次在沙箱中的默认构建长时间未完成，随后改用正常本机权限和 Webpack 构建成功。
- 火绒曾隔离上游技能扫描器源码，记录为 `HEUR:Trojan/Python.ReverseShell.f`。用户处理拦截后，从原提交恢复该文件；保留全部扫描逻辑，未改动 Agent 核心代码。
- Python 测试在沙箱临时目录遇到权限错误，正常本机权限下通过；pytest 缓存写入警告不影响测试断言。

没有运行上游全部测试，也没有测量并发、吞吐量、回答准确率或成本指标。
