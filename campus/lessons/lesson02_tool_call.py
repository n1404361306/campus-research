"""第二课：离线模拟一次工具调用，不请求模型或 MCP，不消耗 API 额度。"""

from pathlib import Path


# 工具本质上可以是一个函数。本例只允许在本课目录内写入指定文件。
def write_file(filename, content):
    if filename != "lesson02-report.md":
        raise ValueError("本课只允许写入 lesson02-report.md")
    folder = Path(__file__).resolve().parent / "outputs"
    folder.mkdir(exist_ok=True)
    (folder / filename).write_text(content, encoding="utf-8")
    return "OK"


# 名称与真正执行的函数之间的对应关系。
tools = {"write_file": write_file}

# 为了观察执行流程，这里手写请求，模拟框架整理后的模型工具调用。
# 真实项目中，调用名称和参数由模型生成，框架解析后执行。
request = {
    "id": "call_001",
    "name": "write_file",
    "args": {
        "filename": "lesson02-report.md",
        "content": "# 校园失物招领系统\n\n这是第二课生成的教学报告。\n",
    },
}
print("1. 模拟模型请求：", request)

name = request["name"]
args = request["args"]
if name not in tools:
    raise ValueError("未知工具：" + name)
result = tools[name](**args)
print("2. 程序执行结果：", result)

tool_message = {
    "role": "tool",
    "tool_call_id": request["id"],
    "content": result,
}
print("3. 准备返回给模型的工具消息：", tool_message)
print("本例到此结束；没有向模型发送上述消息。")
