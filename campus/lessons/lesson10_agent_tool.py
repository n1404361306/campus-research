"""Real LangGraph tool execution with scripted model replies; no external API.

Tool choice, arguments, correction and final reply are predefined teaching data.
Schema validation, tool execution, ToolMessage and graph iteration are real.
The real tool is also registered in the campus production configuration.
"""

import argparse
import json
from pathlib import Path
import sys

import yaml
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from deerflow.reflection import resolve_variable  # noqa: E402


class ScriptedToolModel(FakeMessagesListChatModel):
    """Only the model is substituted; create_agent and tool execution stay real."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        names = [convert_to_openai_tool(item)["function"]["name"] for item in tools]
        if "estimate_project_schedule" not in names:
            raise ValueError("The schedule tool was not supplied to the agent")
        return self


def run_demo(invalid_first=False):
    # Use the same registered import path and resolver as production tool loading.
    profile = yaml.safe_load(
        (ROOT / "campus/config.example.yaml").read_text(encoding="utf-8")
    )
    entry = next(
        item for item in profile["tools"] if item["name"] == "estimate_project_schedule"
    )
    schedule_tool = resolve_variable(entry["use"], BaseTool)
    arguments = {
        "features": [
            {"name": "登录", "estimated_hours": 8},
            {"name": "发布失物", "estimated_hours": 12},
            {"name": "搜索", "estimated_hours": 10},
        ],
        "hours_per_week": 10,
        "deadline_weeks": 4,
    }
    replies = []
    if invalid_first:
        replies.append(
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": schedule_tool.name,
                        "args": {**arguments, "hours_per_week": 0},
                        "id": "schedule-invalid",
                        "type": "tool_call",
                    }
                ],
            )
        )
    replies.extend(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": schedule_tool.name,
                        "args": arguments,
                        "id": "schedule-valid",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content="这是预设的教学结束语。程序已接收工具结果；具体计算值请查看上一条 ToolMessage。"
            ),
        ]
    )
    agent = create_agent(
        model=ScriptedToolModel(responses=replies), tools=[schedule_tool]
    )
    state = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content="我想做校园失物招领：登录8小时、发布12小时、搜索10小时，每周投入10小时，四周后截止，额外预留20%。请计算工期。"
                )
            ]
        },
        config={"recursion_limit": 12},
    )
    messages = []
    results = []
    for message in state["messages"]:
        item = {"type": message.type, "content": message.content}
        if isinstance(message, AIMessage):
            item["tool_calls"] = message.tool_calls
        if isinstance(message, ToolMessage):
            result = (
                json.loads(message.content)
                if message.status == "success"
                else message.content
            )
            item.update(
                name=message.name,
                tool_call_id=message.tool_call_id,
                status=message.status,
            )
            results.append(
                {
                    "status": message.status,
                    "tool_call_id": message.tool_call_id,
                    "result": result,
                }
            )
        messages.append(item)
    return {
        "uses_external_model": False,
        "model_replies": "scripted teaching data, including any correction",
        "agent_runtime": "real langchain.create_agent / LangGraph",
        "registered_use": entry["use"],
        "schema": convert_to_openai_tool(schedule_tool),
        "messages": messages,
        "tool_results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--invalid-first",
        action="store_true",
        help="先预设一条参数错误的请求，再预设修正请求",
    )
    args = parser.parse_args()
    evidence = run_demo(invalid_first=args.invalid_first)
    output = Path(__file__).parent / "outputs"
    output.mkdir(exist_ok=True)
    destination = output / (
        "lesson10-invalid-first.json" if args.invalid_first else "lesson10-success.json"
    )
    destination.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "模型回复为预设数据；参数校验、工具计算与 LangGraph 消息回传真实执行。无网络或 API 费用。"
    )
    for message in evidence["messages"]:
        print(json.dumps(message, ensure_ascii=False))
    for result in evidence["tool_results"]:
        if result["status"] == "success":
            print(
                "真实工具计算结果：", json.dumps(result["result"], ensure_ascii=False)
            )
    print("证据保存到：", destination)


if __name__ == "__main__":
    main()
