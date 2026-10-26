"""第七课：离线演示上下文压缩与工具 schema 按需暴露。

历史、摘要和 schema 均为手写教学样例，不调用模型、MCP 或真实摘要器。
压缩函数只适用于本课构造的完整工具消息对，不实现生产消息保护算法。
字符数不是 Token 数；本课不测量模型费用、性能或摘要质量。
"""

import copy
import json
from pathlib import Path


def compact_context(state, summary, trigger=12, keep=4):
    if len(state["messages"]) < trigger:
        return False
    if keep < 2 or keep % 2 != 0:
        raise ValueError("本课按完整工具消息对演示，请保留正偶数条近期消息")
    recent = state["messages"][-keep:]
    user_id = current_user_id(state)
    preserved = []
    for message in state["messages"]:
        if message["id"] == user_id or message in recent:
            preserved.append(message)
    state["messages"] = preserved
    state["summary_text"] = summary
    return True


def current_user_id(state):
    # 从最后一条向前找，取得最新用户请求的编号。
    for message in reversed(state["messages"]):
        if message["role"] == "user":
            return message["id"]
    return None


def visible_schemas(state, catalog):
    # 本例的 write_file/tool_search 直接可用，两个 MCP 工具延迟暴露。
    names = ["write_file", "tool_search"]
    promoted = state["promoted"]
    if promoted["catalog_hash"] == "lesson07-v1" and promoted[
        "turn_id"
    ] == current_user_id(state):
        names = names + promoted["names"]
    return [tool for tool in catalog if tool["name"] in names]


def tool_search(state, catalog, keyword):
    # 用名称子串做最小检索；真实项目还支持关键词排序、正则和精确选择。
    matched = []
    names = []
    for tool in visible_schemas(state, catalog):
        if tool["name"] not in ["write_file", "tool_search"]:
            names.append(tool["name"])
    for tool in catalog:
        if keyword in tool["name"] and tool["name"].startswith("parallel-search_"):
            matched.append(tool)
            if tool["name"] not in names:
                names.append(tool["name"])
    state["promoted"] = {
        "catalog_hash": "lesson07-v1",
        "turn_id": current_user_id(state),
        "names": names,
    }
    return matched


def call_is_allowed(state, catalog, name):
    for tool in visible_schemas(state, catalog):
        if tool["name"] == name:
            return True
    return False


# 工具说明为教学缩略 schema，不是远程服务实际返回的完整 schema。
catalog = [
    {"name": "write_file", "description": "写文件", "parameters": {"type": "object"}},
    {
        "name": "tool_search",
        "description": "查找工具说明",
        "parameters": {"type": "object"},
    },
    {
        "name": "parallel-search_web_search",
        "description": "搜索公开网页",
        "parameters": {"type": "object"},
    },
    {
        "name": "parallel-search_web_fetch",
        "description": "读取网页",
        "parameters": {"type": "object"},
    },
]
state = {
    "messages": [
        {
            "id": "user_001",
            "role": "user",
            "content": "我会 Python、单人八周，请调研校园失物招领系统，不接支付。",
        }
    ],
    "summary_text": "",
    "todos": [{"content": "生成并交付调研报告", "status": "in_progress"}],
    "artifacts": [],
    "promoted": {"catalog_hash": "lesson07-v1", "turn_id": "user_001", "names": []},
}
for index in range(6):
    call_id = "call_" + str(index)
    state["messages"].append(
        {
            "id": "ai_" + str(index),
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": call_id, "name": "read_file", "args": {"path": "教学资料.md"}}
            ],
        }
    )
    state["messages"].append(
        {
            "id": "tool_" + str(index),
            "role": "tool",
            "tool_call_id": call_id,
            "content": "手写的资料读取占位结果，没有实际调用工具。" * 30,
        }
    )

before = copy.deepcopy(state)
summary = "手写教学摘要：用户会 Python，单人八周，调研校园失物招领，不接支付。早期四轮资料读取是模拟记录，尚未完成最终报告。"
compact_context(state, summary)
after_compaction = copy.deepcopy(state)
print("1. 消息条数：", len(before["messages"]), "→", len(state["messages"]))
print("2. 当前请求仍在：", state["messages"][0]["content"])
print("3. 独立计划仍在：", state["todos"])
print("4. 摘要字段：", state["summary_text"])

initial_tools = [tool["name"] for tool in visible_schemas(state, catalog)]
blocked_before = not call_is_allowed(state, catalog, "parallel-search_web_search")
print("5. 最初暴露的完整工具说明：", initial_tools)
print("6. 直接请求未激活工具会被拦截：", blocked_before)
matched = tool_search(state, catalog, "web_search")
loaded_tools = [tool["name"] for tool in visible_schemas(state, catalog)]
allowed_after = call_is_allowed(state, catalog, "parallel-search_web_search")
print("7. 检索返回的 schema：", matched)
print("8. 激活后的工具：", loaded_tools, "；搜索调用可通过发现检查：", allowed_after)
print("本例仅检查是否激活，没有执行任何工具。")

# 新用户轮次不能直接沿用旧轮次的发现状态；这里只演示作用域检查。
state["messages"].append(
    {"id": "user_002", "role": "user", "content": "接下来只解释报告格式。"}
)
new_turn_tools = [tool["name"] for tool in visible_schemas(state, catalog)]
print("9. 新用户轮次的工具：", new_turn_tools)

evidence = {
    "simulation": True,
    "summary_source": "handwritten fixture; no model call",
    "before": before,
    "after_compaction": after_compaction,
    "message_characters_before": len(
        json.dumps(before["messages"], ensure_ascii=False)
    ),
    "message_characters_after": len(
        json.dumps(after_compaction["messages"], ensure_ascii=False)
    )
    + len(summary),
    "catalog_names": [tool["name"] for tool in catalog],
    "initial_tools": initial_tools,
    "blocked_before_discovery": blocked_before,
    "matched_schemas": matched,
    "loaded_tools": loaded_tools,
    "allowed_after_discovery": allowed_after,
    "new_turn_tools": new_turn_tools,
    "final_state": state,
}
folder = Path(__file__).resolve().parent / "outputs"
folder.mkdir(exist_ok=True)
path = folder / "lesson07-context-tools.json"
path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
print("10. 前后对照已保存：", path)
print("历史副本仅为本课对照保存；本例不实现真实检查点、模型摘要或 API 请求。")
