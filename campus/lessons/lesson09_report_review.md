# 第九课：给真实工作台增加“报告复核”入口

这次修改真实前端。入口准备一条可以编辑的用户请求；点击按钮不会启动模型，也不会自动验证报告。

## 1. 明确需求

新对话增加“报告复核”，点击后填入来源、方案适配、功能与计划、交付证据的复核要求。没有可读取报告时，要求模型先索取；缺少证据的检查标为待验证。用户补充报告或上传文件，确认后自行发送。电脑、手机及中英文界面都应可用。

## 2. 定位代码

在项目根目录搜索：

```powershell
rg -n '选题调研|suggestions.map|handleSuggestionClick' frontend/src
```

顺着结果读三个位置：

1. `frontend/src/core/i18n/locales/zh-CN.ts`：按钮名称、需求文本、图标。
2. `frontend/src/components/workspace/input-box.tsx` 的 `SuggestionList`：列表渲染与点击回调。
3. `frontend/src/components/ai-elements/prompt-input.tsx`：输入框状态管理。

`.ts` 是 TypeScript 文件，`.tsx` 还可以包含描述界面的 JSX。

`inputBox.suggestions` 是数组（有顺序的列表）；每个 `{ ... }` 是一个对象。`suggestion` 是按钮文字，`prompt` 是预填文本，`icon` 是图标组件。本次给中英文列表各加一项，并从现有 `lucide-react` 依赖导入 `ClipboardCheckIcon`，没有安装新依赖。

`locales/types.ts` 中 `Translations` 规定了字段类型。类型检查能发现把数字当文本等错误，但不能判断提示词内容是否合理。

## 3. 看懂原有渲染

```tsx
{t.inputBox.suggestions.map((suggestion) => (
  <Suggestion
    key={suggestion.suggestion}
    icon={suggestion.icon}
    suggestion={suggestion.suggestion}
    onClick={() => handleSuggestionClick(suggestion.prompt)}
  />
))}
```

- `t` 是当前语言文案；`.` 读取对象字段。
- `.map(...)` 逐项读取数组，将每项变成一个按钮。
- `<Suggestion ... />` 是 React 组件，传入的字段叫 props。
- `key` 帮 React 识别各项，当前列表使用不同的按钮名称。
- `() => ...` 定义稍后执行的函数，点击时才执行。
- `suggestion.prompt` 取出被点击项的完整请求。

## 4. 看懂原有点击回调

```tsx
const handleSuggestionClick = useCallback(
  (prompt: string | undefined) => {
    if (!prompt) return;
    textInput.setInput(prompt);
    onSelectPlaceholder(prompt);
  },
  [textInput, onSelectPlaceholder],
);
```

- `const` 声明不重新赋值的名字。
- `prompt: string | undefined` 表示参数为字符串或没有值。
- `if (!prompt) return` 表示没有文本就提前结束。
- `textInput.setInput(prompt)` 更新输入框状态，React 随后刷新界面。
- `onSelectPlaceholder` 处理已有模板中可替换占位内容的选中；本次文本没有这种占位内容。
- `useCallback` 按依赖缓存回调，末尾数组列出使用的外部依赖。

这些代码均为复用，没有修改。真正发送走 `PromptInput` 的 `onSubmit={handleSubmit}`，再进入原有聊天发送流程。输入框草稿属于前端状态，不等于后端 Agent 的消息历史；确认发送后才进入后端运行。

## 5. 实际改动与检查

本次修改两个语言文件、增加一个浏览器测试，并补充使用与维护文档。未修改 Agent 循环、MCP 或后端。

在 `frontend` 中，使用 Node.js 22+ 和项目 pnpm：

```powershell
pnpm check
pnpm exec rstest run tests/unit/core/i18n
pnpm exec next build --webpack
```

生产模式需重新构建并重启才能看到修改；开发模式通常自动刷新。启动本地服务后，在 `frontend` 执行：

```powershell
$env:PLAYWRIGHT_SKIP_WEB_SERVER='1'
$env:PLAYWRIGHT_BASE_URL='http://127.0.0.1:3000'
$env:PLAYWRIGHT_BROWSERS_PATH=(Resolve-Path ../.tools/playwright).Path
pnpm exec playwright test tests/e2e/campus.spec.ts --reporter=line
```

本机 pnpm 不在命令路径时，将命令开头的 `pnpm` 替换为 `node ../.tools/node/node_modules/pnpm/bin/pnpm.cjs`。Node.js 也需要使用项目已安装的 22+ 版本。

浏览器测试用模拟后端，实际操作页面，检查填充、编辑、电脑/手机无横向溢出及没有启动运行。它不调用模型，不证明模型一定遵守提示词。

```ts
await page.getByRole("button", { name: "报告复核", exact: true }).click();
await expect(composer).toHaveValue(/若没有可读取的报告/);
expect(runRequests).toEqual([]);
```

`await` 等待异步操作；`getByRole` 按控件角色与名称查找元素；`expect` 声明期望；`/文本/` 是正则匹配；`[]` 表示没有记录到运行请求。测试前面的监听器负责收集 POST `/runs` 请求。

## 6. 手动使用

本课已完成：语言模块3项单元测试、前端代码规范与类型检查、生产构建、3项浏览器回归（新增一项覆盖电脑和手机）。还直接检查了无模拟接口的前端预览，确认按钮可见且能填入需求，未发送。完整服务启动时，上游 `skills/skillscan/orchestrator.py` 再次无法读取并消失；恢复仓库原文件后仍立即消失，需核对安全软件隔离记录。当前仅启动了明确标注预览的前端，模型复核尚未验收。

打开新对话，点击“报告复核”，确认只填入需求。添加个人基础、周期和预算，再粘贴或上传报告。新对话不会自动获得旧对话中的文件。用户自行发送后才启动真实模型并消耗 API 额度。复核回答的事实正确性还需要对照原文、工具记录和文件结果验证。

## 7. 面试介绍

“项目基于 DeerFlow 完整产品改造。我新增了报告复核快捷入口，让用户对照个人约束和交付证据复核报告。我沿语言配置、列表渲染、点击回调和输入框状态定位代码，复用了原有发送流程。入口先填入可编辑请求，确认后发送。我补充了电脑和手机浏览器测试，验证填充、编辑和不自动启动运行。这是我实现的交互与任务要求改造，不是自研 Agent 框架或事实核查算法；模型复核质量还需要专门的样本和评测。”

练习：只在中文 `prompt` 末尾增加一项输出要求，重新构建并检查界面。思考：为什么只修改按钮名称无法改变复核要求？为什么“没有运行请求”也是一项正确结果？
