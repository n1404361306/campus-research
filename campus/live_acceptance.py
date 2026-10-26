"""Explicit live acceptance: calls the real local Agent and model providers.

Saves only public test inputs, actions, final output and acceptance metadata.
Does not save model reasoning or credentials. Run after starting CampusResearch.
"""

from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path
import re
import time
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "campus/live-results"
BASE = "http://127.0.0.1:8001"
PROMPT = """请实际完成一次校园选题调研，不是给我操作指南。
我是计算机专业学生，会 Python 和基础 Web，单人开发，周期八周，预算每月不超过100元。
选题是校园失物招领系统，必须支持发布、检索和认领，不接真实支付，不要求企业账号。
这次要验证计划和多 Agent：先用 write_todos 列出计划，再通过两个 general-purpose 子任务分别完成互不重复的资料核实：
A：搜索真实公开的类似产品或开源实现，读取至少一个原始网页，返回2条来源、部署条件和限制。
B：读取官方技术资料，对比 Django、FastAPI 和 Spring Boot 对这个学生项目的适用性，返回2条官方来源。
每个子任务都应实际调用外部 Parallel Search MCP；工具按需加载时先用 tool_search 找到实际工具 schema。
控制成本：每个子任务只发起一次搜索（至多两个查询），再按需读取一个网页；搜索目标明确要求短摘要。来源足够立即返回，不做宽泛反复搜索。遇限流立即停止外部调用并说明缺口。
主 Agent 综合子任务结果，不要重复全部搜索，不要再分派第三个子任务。
请写一份约1200至1800字的中文报告，包含：选题背景与目标用户、类似产品及开源项目、可选技术路线对比、建议实现的功能、开发计划、风险与尚需验证的问题、参考来源。
比较三条路线，功能分必做/可选/暂缓，按八周列交付物与验收标准，至少引用4个真实来源链接并标核实日期。
明确区分已核实事实与建议，不虚构价格、星数、测试或性能结论。信息不足之处注明待验证，无需再向我提问。
用文件工具将报告保存至 /mnt/user-data/outputs/campus-research-report.md，随后调用 present_files 提供下载。
最后更新 todos 为完成，简短说明报告已生成。"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Finish the existing acceptance conversation without repeating research",
    )
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    thread_id = str(uuid4())
    evidence = {
        "thread_id": thread_id,
        "chat_url": f"http://127.0.0.1:3000/workspace/chats/{thread_id}",
        "prompt": PROMPT,
        "tool_names": [],
        "task_events": [],
        "summary_observed": False,
        "message_count_drops": [],
    }
    manifest = OUT / "acceptance.json"
    if args.resume:
        evidence = json.loads(manifest.read_text(encoding="utf-8"))
        thread_id = evidence["thread_id"]
        evidence.setdefault("previous_runs", []).append(
            {"run_id": evidence.get("run_id"), "error": evidence.pop("error", None)}
        )
    manifest.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tools = set(evidence["tool_names"])
    seen_tasks = set()
    latest = {}
    previous_count = 0
    started = time.monotonic()

    def scan(value):
        if isinstance(value, dict):
            for call in value.get("tool_calls", []) or []:
                if isinstance(call, dict) and call.get("name"):
                    name = call["name"]
                    if name not in tools:
                        tools.add(name)
                        print(f"ACTION {name}", flush=True)
            kind = value.get("type")
            if isinstance(kind, str) and kind.startswith("task_"):
                key = (kind, str(value.get("task_id", value.get("id", ""))))
                if key not in seen_tasks and kind != "task_running":
                    seen_tasks.add(key)
                    evidence["task_events"].append({"type": kind, "task_id": key[1]})
                    print(f"SUBAGENT {kind} {key[1]}", flush=True)
            for key, child in value.items():
                if key not in {"reasoning_content", "reasoning", "additional_kwargs"}:
                    scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    def consume(event, raw):
        nonlocal latest, previous_count
        if not raw:
            return
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return
        if event == "error":
            evidence["error"] = "Gateway run error; see local log"
            evidence["tool_names"] = sorted(tools)
            manifest.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            raise RuntimeError("Gateway emitted a run error; inspect local Gateway log")
        if event == "metadata" and isinstance(value, dict):
            evidence["run_id"] = value.get("run_id")
        scan(value)
        if event == "values" and isinstance(value, dict):
            latest = value
            count = len(value.get("messages", []))
            if count < previous_count:
                evidence["message_count_drops"].append([previous_count, count])
            previous_count = count
            if value.get("summary_text"):
                evidence["summary_observed"] = True
        evidence["tool_names"] = sorted(tools)
        manifest.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    with httpx.Client(timeout=httpx.Timeout(45, connect=10), trust_env=False) as client:
        me = client.get(BASE + "/api/v1/auth/me")
        me.raise_for_status()
        pref = client.patch(
            BASE + "/api/v1/auth/preferences",
            headers={"X-Expected-User-Id": me.json()["id"]},
            json={
                "model_name": "campus-model",
                "mode": "ultra",
                "reasoning_effort": "low",
                "locale": "zh-CN",
            },
        )
        if pref.status_code == 403:
            # Anonymous local mode intentionally has no session-backed preferences.
            # This run explicitly requests Ultra in its normal public context.
            evidence["preference_persistence"] = "not_applicable_in_auth_disabled_mode"
        else:
            pref.raise_for_status()
        payload = {
            "assistant_id": "lead_agent",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "继续完成已有任务：报告已经 write_file 成功，不要重新搜索或重派子任务。请调用 present_files 注册已有 /mnt/user-data/outputs/campus-research-report.md 供下载，将 todos 全部更新为 completed，然后简短结束。"
                            if args.resume
                            else PROMPT
                        ),
                    }
                ]
            },
            "config": {
                "configurable": {"thread_id": thread_id},
                "recursion_limit": 250,
            },
            "context": {
                "model_name": "campus-model",
                "mode": "ultra",
                "thinking_enabled": True,
                "reasoning_effort": "low",
                "is_plan_mode": True,
                "subagent_enabled": True,
                "max_concurrent_subagents": 2,
            },
            "stream_mode": ["updates", "custom", "values"],
            "on_disconnect": "continue",
        }
        print(f"START {thread_id}", flush=True)
        event, lines = "message", []
        with client.stream("POST", BASE + "/api/runs/stream", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if time.monotonic() - started > 900:
                    raise TimeoutError(
                        "Live run exceeded 15 minutes; original run may still continue"
                    )
                if not line:
                    consume(event, "\n".join(lines))
                    event, lines = "message", []
                elif line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    lines.append(line[5:].lstrip())
        state = client.get(BASE + f"/api/threads/{thread_id}/state")
        state.raise_for_status()
        latest = state.json().get("values", latest)
        evidence["summary_observed"] |= bool(latest.get("summary_text"))
        evidence["tool_names"] = sorted(tools)
        evidence["todos"] = latest.get("todos")
        evidence["artifacts"] = latest.get("artifacts", [])
        evidence["last_run_elapsed_seconds"] = round(time.monotonic() - started, 1)
        manifest.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths = [
            p for p in evidence["artifacts"] if p.endswith("campus-research-report.md")
        ]
        if not paths:
            raise RuntimeError("Agent did not register the expected report artifact")
        path = paths[-1]
        url = BASE + f"/api/threads/{thread_id}/artifacts/" + path.lstrip("/")
        download = client.get(url, params={"download": "true"})
        download.raise_for_status()
        report = download.content.decode("utf-8-sig")
        (OUT / "campus-research-report.md").write_bytes(download.content)
        sections = [
            "选题背景与目标用户",
            "类似产品及开源项目",
            "可选技术路线对比",
            "建议实现的功能",
            "开发计划",
            "风险与尚需验证的问题",
            "参考来源",
        ]
        evidence["report_sections_present"] = all(s in report for s in sections)
        evidence["source_link_count"] = len(
            set(re.findall(r"https?://[^\s)>\]]+", report))
        )
        evidence["download_bytes"] = len(download.content)
        evidence["download_sha256"] = hashlib.sha256(download.content).hexdigest()
        evidence["download_url"] = (
            url.replace(BASE, "http://127.0.0.1:3000") + "?download=true"
        )
        evidence["content_disposition"] = download.headers.get(
            "content-disposition", ""
        )
        manifest.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert {"task", "write_todos", "present_files"} <= tools, (
            "Missing expected plan/delegation/artifact actions"
        )
        assert (
            evidence["report_sections_present"] and evidence["source_link_count"] >= 4
        )
        assert download.content and "attachment" in evidence["content_disposition"]
        assert evidence["summary_observed"], "Automatic compaction not observed"
        assert (
            len([e for e in evidence["task_events"] if e["type"] == "task_completed"])
            == 2
        )
        assert {
            "tool_search",
            "parallel-search_web_search",
            "parallel-search_web_fetch",
        } <= tools
        assert evidence["todos"] and all(
            t["status"] == "completed" for t in evidence["todos"]
        )
        print("REPORT_DOWNLOADED", len(download.content), "bytes", flush=True)
        print("CHAT", evidence["chat_url"], flush=True)


if __name__ == "__main__":
    main()
