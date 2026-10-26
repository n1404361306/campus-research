"""第五课的真实本地 MCP 服务：通过 stdio 通信，搜索数据为静态教学样例。

不访问互联网、不请求模型。不能把本例返回值当作联网调研证据。
stdio 的 stdout 用于协议通信，请勿在服务端添加普通 print 调试输出。
"""

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Campus Lesson 05 (offline fixtures)")
PAGE_URL = "https://docs.djangoproject.com/"


@mcp.tool()
def web_search(objective: str, search_queries: list[str], session_id: str = "") -> str:
    """返回一条静态教学搜索结果；本工具没有实际联网搜索能力。"""
    data = {
        "fixture": True,
        "notice": "静态教学数据，未联网搜索或验证网页内容。",
        "objective": objective,
        "search_queries": search_queries,
        "session_id": session_id,
        "results": [{"title": "Django 文档入口（教学占位结果）", "url": PAGE_URL}],
    }
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def web_fetch(urls: list[str], objective: str, session_id: str = "") -> str:
    """返回固定 URL 的静态教学文本；不会通过网络读取网页。"""
    if urls != [PAGE_URL]:
        raise ValueError("本课只提供 https://docs.djangoproject.com/ 的静态占位数据")
    data = {
        "fixture": True,
        "notice": "这不是网页抓取结果，仅演示 MCP 工具返回数据。",
        "objective": objective,
        "session_id": session_id,
        "results": [
            {
                "url": PAGE_URL,
                "text": "静态教学段落：这里本应放置服务端取得的网页资料。",
            }
        ],
    }
    return json.dumps(data, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
