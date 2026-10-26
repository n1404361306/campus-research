"""第三课：离线演示消息、状态和磁盘保存，不请求模型或 MCP。

直接运行：模拟一次任务并保存 JSON；加 --load：只从文件读取，不重新执行任务。
所有模型消息、计划和状态更新均为教学代码手写，不是模型自动产生的。
JSON 是教学存储格式；真实项目使用 LangGraph checkpointer 与 SQLite 等机制。
"""

import json
from pathlib import Path
import sys

folder = Path(__file__).resolve().parent / "outputs"
folder.mkdir(exist_ok=True)
checkpoint_path = folder / "lesson03-state.json"

if "--load" in sys.argv:
    # 此分支不生成报告，只读取上一次保存在磁盘中的状态。
    text = checkpoint_path.read_text(encoding="utf-8")
    checkpoint = json.loads(text)
    state = checkpoint["state"]
    print("从磁盘恢复会话：", checkpoint["thread_id"])
else:
    state = {"messages": [], "todos": [], "artifacts": [], "summary_text": ""}

    # 1. messages 是 state 中的一项，用列表按顺序记录对话。
    state["messages"].append(
        {"role": "user", "content": "我会 Python，单人八周，请调研校园失物招领系统。"}
    )

    # 2. todos 独立记录当前任务进度；这里模拟 write_todos 的效果。
    state["todos"] = [
        {"content": "保存报告", "status": "in_progress"},
        {"content": "登记报告产物", "status": "pending"},
    ]
    print("执行前的计划：", state["todos"])

    # 3. 沿用第二课的工具请求结构；这里省略工具查表分发，直接执行本课文件写入。
    report_path = folder / "lesson03-report.md"
    request = {
        "id": "call_001",
        "name": "write_file",
        "args": {
            "path": str(report_path),
            "content": "# 校园失物招领系统\n\n约束：Python 基础，单人八周。\n",
        },
    }
    state["messages"].append(
        {"role": "assistant", "content": "", "tool_calls": [request]}
    )

    # 4. 实际写入文件，再记录工具返回值；失败时不会执行后面的完成状态更新。
    report_path.write_text(request["args"]["content"], encoding="utf-8")
    state["messages"].append(
        {"role": "tool", "tool_call_id": request["id"], "content": "OK"}
    )
    state["todos"][0]["status"] = "completed"
    state["todos"][1]["status"] = "in_progress"
    print("写入后的计划：", state["todos"])

    # 5. 手工模拟 present_files 的登记效果，产物列表保存路径，不保存报告全文。
    state["artifacts"].append(str(report_path))
    state["todos"][1]["status"] = "completed"
    state["messages"].append(
        {"role": "assistant", "content": "教学报告已写入并登记。"}
    )

    # 6. 把内存里的数据编码成 JSON 文本，保存到磁盘。
    checkpoint = {"thread_id": "lesson03-campus", "state": state}
    text = json.dumps(checkpoint, ensure_ascii=False, indent=2)
    checkpoint_path.write_text(text, encoding="utf-8")
    print("状态已保存：", checkpoint_path)

print("消息条数：", len(state["messages"]))
print("用户需求：", state["messages"][0]["content"])
print("最终计划：", state["todos"])
print("报告路径：", state["artifacts"])
print("本例没有调用大模型，也没有压缩消息或自动判断报告质量。")
