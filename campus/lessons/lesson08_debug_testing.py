"""第八课：离线故障注入、有限重试、模拟预算和交付检查。

全部错误均人为注入，不请求模型、网络或 MCP；预算是教学点数，不是 Token 或钱。
固定每次3点、调用前扣点仅用于演示，真实项目按供应商 usage 等信息统计。
重试示例面向无外部副作用的教学查询；不能直接用于发送消息、下单或追加写入。
交付检查只覆盖本地结构与副本一致性，不证明来源、内容或真实下载正确。
"""

import hashlib
import json
from pathlib import Path
import time


class RateLimitError(Exception):
    pass


class QuotaExhaustedError(Exception):
    pass


class BudgetExceededError(Exception):
    pass


class ToolResultError(Exception):
    pass


def fake_search(query, scenario, tracker):
    tracker["calls"] += 1
    if scenario == "rate_limit_twice" and tracker["calls"] <= 2:
        raise RateLimitError("教学临时限流")
    if scenario == "always_rate_limited":
        raise RateLimitError("教学持续限流")
    if scenario == "timeout_once" and tracker["calls"] == 1:
        raise TimeoutError("教学读取超时；未执行真实网络请求")
    if scenario == "quota_exhausted":
        raise QuotaExhaustedError("教学额度耗尽，不应立即反复重试")
    if scenario == "tool_error":
        return {"isError": True, "content": "教学工具报告执行失败"}
    return {"isError": False, "content": "静态教学查询结果：" + query}


def call_with_retry(tool, args, budget, events, max_attempts=3, pause=time.sleep):
    if not args.get("query"):
        raise ValueError("query 不能为空；先修正参数")
    if max_attempts < 1:
        raise ValueError("至少需要允许一次尝试")
    for attempt in range(1, max_attempts + 1):
        # 教学预留额度；没有足够点数时，不启动下一次查询。
        if budget["used"] + 3 > budget["limit"]:
            events.append({"event": "budget_stop", "attempt": attempt})
            raise BudgetExceededError("教学点数不足，停止后续尝试")
        budget["used"] += 3
        events.append({"event": "call", "attempt": attempt, "used": budget["used"]})
        try:
            result = tool(**args)
            if result.get("isError"):
                raise ToolResultError("工具返回错误标记；需要检查原因，不盲目重试")
            events.append({"event": "success", "attempt": attempt})
            return result
        except (RateLimitError, TimeoutError) as error:
            events.append({"event": type(error).__name__, "attempt": attempt})
            if attempt == max_attempts:
                raise
            delay = 0.02 * 2 ** (attempt - 1)
            events.append({"event": "wait", "seconds": delay})
            pause(delay)


def run_case(scenario, limit=12, pause=time.sleep):
    tracker = {"calls": 0}
    budget = {"limit": limit, "used": 0}
    events = []
    args = {
        "query": "" if scenario == "bad_arguments" else "校园失物招领",
        "scenario": scenario,
        "tracker": tracker,
    }
    try:
        result = call_with_retry(fake_search, args, budget, events, pause=pause)
        outcome = {"status": "success", "result": result}
    except (
        RateLimitError,
        TimeoutError,
        QuotaExhaustedError,
        ToolResultError,
        BudgetExceededError,
        ValueError,
    ) as error:
        outcome = {"status": "stopped", "error_type": type(error).__name__}
    return {
        "scenario": scenario,
        "calls": tracker["calls"],
        "budget": budget,
        "events": events,
        **outcome,
    }


def same_file_content(original, local_copy):
    if not original.is_file() or not local_copy.is_file():
        return False
    a = hashlib.sha256(original.read_bytes()).hexdigest()
    b = hashlib.sha256(local_copy.read_bytes()).hexdigest()
    return a == b


def verify_delivery(path, artifacts, todos, local_copy):
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    checks = {
        "todos_completed": bool(todos)
        and all(t["status"] == "completed" for t in todos),
        "file_exists": path.is_file(),
        "non_empty": bool(text.strip()),
        "sections_present": all(
            s in text for s in ["技术路线", "开发计划", "参考来源"]
        ),
        "artifact_registered": str(path) in artifacts,
        "local_copy_matches": same_file_content(path, local_copy),
    }
    return {"checks": checks, "mechanical_checks_passed": all(checks.values())}


def main():
    cases = []
    for scenario in [
        "rate_limit_twice",
        "timeout_once",
        "quota_exhausted",
        "bad_arguments",
        "tool_error",
        "always_rate_limited",
    ]:
        cases.append(run_case(scenario))
    cases.append(run_case("rate_limit_twice", limit=5))
    for case in cases:
        print(
            case["scenario"],
            case["status"],
            "实际教学查询次数",
            case["calls"],
            case.get("error_type", ""),
        )

    folder = Path(__file__).resolve().parent / "outputs"
    folder.mkdir(exist_ok=True)
    path = folder / "lesson08-report.md"
    local_copy = folder / "lesson08-copy.md"
    todos = [{"content": "交付教学报告", "status": "completed"}]
    path.write_text("# 只有标题的草稿\n", encoding="utf-8")
    local_copy.write_bytes(path.read_bytes())
    draft = verify_delivery(path, [], todos, local_copy)
    print("计划虽已勾选，草稿机械检查是否通过：", draft["mechanical_checks_passed"])

    path.write_text(
        "# 第八课教学报告\n\n## 技术路线\n静态占位，未实际选型。\n"
        "## 开发计划\n静态占位，未评估可行性。\n"
        "## 参考来源\n未联网核实，仅作结构检查练习。\n",
        encoding="utf-8",
    )
    local_copy.write_bytes(path.read_bytes())
    revised = verify_delivery(path, [str(path)], todos, local_copy)
    print("补齐结构与登记后的机械检查：", revised["mechanical_checks_passed"])
    evidence = {
        "simulation": True,
        "model_called": False,
        "network_used": False,
        "budget_unit": "teaching points; not tokens or money",
        "cases": cases,
        "draft_delivery": draft,
        "revised_delivery": revised,
        "not_verified": [
            "source_truth",
            "business_quality",
            "real_http_browser_download",
        ],
    }
    (folder / "lesson08-debug-results.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("本地副本用于演示一致性检查，不代表验证了真实浏览器下载。")


if __name__ == "__main__":
    main()
