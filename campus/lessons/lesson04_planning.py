"""第四课：离线演示任务拆分、进度更新和完成检查，不调用模型或 MCP。

计划、模型更新决定与资料都是手写教学样例，不能作为真实调研资料。
write_todos 仅模拟保存整份计划，省略工具消息封装和真实中间件。
报告章节检查是本课额外写的教学规则，不是生产 write_todos 自带能力。
"""

import json
from pathlib import Path


def write_todos(state, todos):
    # 模拟工具的核心效果：用提交的整份计划更新 todos。
    state["todos"] = todos
    print("当前计划：", todos)


def update_status(state, index, status):
    # 构造一份新的完整计划，避免修改时影响旧的任务字典。
    todos = []
    for todo in state["todos"]:
        todos.append(todo.copy())
    todos[index]["status"] = status
    write_todos(state, todos)


def all_tasks_completed(todos):
    # 本次教学目标需要一份计划；空列表不能证明本次目标完成。
    if not todos:
        return False
    for todo in todos:
        if todo["status"] != "completed":
            return False
    return True


def report_is_ready(path):
    # 只检查文件及章节关键词，不能证明资料真实、内容正确或可以下载。
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "技术路线" in text and "参考来源" in text


folder = Path(__file__).resolve().parent / "outputs"
folder.mkdir(exist_ok=True)
report_path = folder / "lesson04-report.md"
state = {"todos": [], "artifacts": []}

# 1. 手写模拟模型拆出的计划。真实项目由模型决定任务内容。
write_todos(
    state,
    [
        {"content": "整理两条教学资料", "status": "in_progress"},
        {"content": "保存包含技术路线和参考来源的教学报告", "status": "pending"},
        {"content": "登记教学报告产物", "status": "pending"},
    ],
)
if not all_tasks_completed(state["todos"]):
    print("结束检查：还有未完成项，请继续执行。这里只模拟提醒一次。")

# 2. 教学资料仅为本地样例；数量检查不代表已联网核实。
sources = ["教学资料A：Python基础（手写样例）", "教学资料B：Web表单（手写样例）"]
if len(sources) >= 2:
    update_status(state, 0, "completed")
    update_status(state, 1, "in_progress")

# 3. 文件写入成功，但草稿不符合本课章节要求，因此不能标记完成。
report_path.write_text("# 校园失物招领教学报告\n\n这是尚未完成的草稿。\n", encoding="utf-8")
first_report_check = report_is_ready(report_path)
if first_report_check:
    update_status(state, 1, "completed")
else:
    print("草稿写入成功，但章节检查失败：保存报告仍为 in_progress。")

# 4. 按手写的教学步骤补齐内容，再次检查。
report_path.write_text(
    "# 校园失物招领教学报告\n\n"
    "## 技术路线\n这是练习计划管理的占位内容，未进行实际技术选型。\n\n"
    "## 参考来源\n仅有手写教学资料A、B，未联网检索或核实。\n",
    encoding="utf-8",
)
second_report_check = report_is_ready(report_path)
if not second_report_check:
    raise RuntimeError("教学报告仍未通过章节检查，停止后续步骤。")
update_status(state, 1, "completed")
update_status(state, 2, "in_progress")

# 5. 手工模拟 present_files 的登记效果，检查文件存在且路径已登记。
state["artifacts"].append(str(report_path))
artifact_ready = report_path.is_file() and str(report_path) in state["artifacts"]
if not artifact_ready:
    raise RuntimeError("产物登记检查失败，不能标记完成。")
update_status(state, 2, "completed")

plan_completed = all_tasks_completed(state["todos"])
print("计划是否全部完成：", plan_completed)
print("本课交付检查是否通过：", second_report_check and artifact_ready)
print("最终交付：", report_path)
print("真实下载、资料真实性与报告质量不在本课检查范围内。")

# 保存公开教学证据，供对照阅读，不涉及真实 Agent 运行数据。
evidence = {
    "simulation": True,
    "state": state,
    "draft_report_check": first_report_check,
    "revised_report_check": second_report_check,
    "artifact_check": artifact_ready,
    "plan_completed": plan_completed,
}
(folder / "lesson04-state.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
)
