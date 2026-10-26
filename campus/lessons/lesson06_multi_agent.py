"""第六课：用真实异步并发模拟主任务委派与子任务返回，不调用模型或 MCP。

子任务只是异步函数，任务说明和结果都是静态教学数据，不是真正会推理的 Agent。
asyncio.sleep 代表等待模型/网络的时间，不代表实际调用过外部服务。
加 --fail-b 故意让 B 抛错，用于观察保留 A 结果、交付缺口说明的流程。
"""

import asyncio
import json
from pathlib import Path
import sys
import time


async def run_child(task_id, prompt, delay, fail=False):
    # 每次调用创建自己的消息列表，不修改另一个子任务的消息。
    child_messages = [{"role": "user", "content": prompt}]
    started_at = time.perf_counter()
    print(task_id, "开始：", prompt, flush=True)

    await asyncio.sleep(delay)
    if fail:
        raise RuntimeError("B 的教学故障：这是人为触发的异常，不是真实搜索错误")

    summary = task_id + " 的静态教学结论：此处应返回子 Agent 的核实摘要。"
    child_messages.append({"role": "assistant", "content": summary})
    finished_at = time.perf_counter()
    print(task_id, "完成并返回结果", flush=True)
    return {
        "task_id": task_id,
        "summary": summary,
        "sources": ["静态教学资料，未联网核实"],
        "limitations": "本例未调用模型或搜索，不能作为真实调研结论。",
        "started_at": started_at,
        "finished_at": finished_at,
        "child_message_count": len(child_messages),
    }


async def main():
    fail_b = "--fail-b" in sys.argv
    assignments = [
        {
            "task_id": "A",
            "prompt": "学生会 Python、单人八周；只核实失物招领参考项目，返回来源和限制。",
        },
        {
            "task_id": "B",
            "prompt": "学生会 Python、单人八周；只核实后端技术路线，返回官方来源和限制。",
        },
    ]
    started_at = time.perf_counter()

    # create_task 将两个协程提交调度；它们可以在等待期间交错推进。
    child_a = asyncio.create_task(run_child("A", assignments[0]["prompt"], delay=1.2))
    child_b = asyncio.create_task(
        run_child("B", assignments[1]["prompt"], delay=0.8, fail=fail_b)
    )
    # 按传入顺序得到结果；return_exceptions=True 将普通异常也收集为结果。
    results = await asyncio.gather(child_a, child_b, return_exceptions=True)

    successes = []
    failures = []
    for index, result in enumerate(results):
        task_id = assignments[index]["task_id"]
        if isinstance(result, Exception):
            failures.append({"task_id": task_id, "error": str(result)})
            print("主任务收到失败：", task_id, str(result))
        else:
            successes.append(result)
            print("主任务收到成功：", task_id, result["summary"])

    # 本例只把返回数据拼成文档，不使用模型进行真正的综合推理。
    lines = [
        "# 第六课：并发委派教学记录",
        "",
        "所有结论都是静态样例，未进行真实调研。",
        "",
    ]
    for result in successes:
        lines.append("## 子任务 " + result["task_id"])
        lines.append(result["summary"])
        lines.append(result["limitations"])
        lines.append("")
    for failure in failures:
        lines.append("## 尚未完成的子任务 " + failure["task_id"])
        lines.append(failure["error"])
        lines.append("保留其他结果，不声称完整调研已完成。")

    overlap = None
    if len(successes) == 2:
        overlap = max(r["started_at"] for r in successes) < min(
            r["finished_at"] for r in successes
        )
    evidence = {
        "simulation": True,
        "model_called": False,
        "mcp_called": False,
        "assignments": assignments,
        "successes": successes,
        "failures": failures,
        "child_intervals_overlap": overlap,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "outcome": "partial" if failures else "completed",
    }
    folder = Path(__file__).resolve().parent / "outputs"
    folder.mkdir(exist_ok=True)
    suffix = "failure" if fail_b else "success"
    (folder / f"lesson06-{suffix}.md").write_text("\n".join(lines), encoding="utf-8")
    (folder / f"lesson06-{suffix}.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("最终状态：", evidence["outcome"], "；子任务运行区间重叠：", overlap)
    print("本例没有模型推理；真实项目的主 Agent 会读取结果并作出下一步决定。")


if __name__ == "__main__":
    asyncio.run(main())
