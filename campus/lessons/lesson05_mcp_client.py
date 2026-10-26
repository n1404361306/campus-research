"""第五课客户端：真实 MCP 初始化、工具发现、搜索与读取调用，全部离线。

通过 SDK 启动本课本地服务端，不连接 Parallel，也不请求大模型。
模型选择工具和生成参数的环节由手写数据代替；两次 MCP 工具调用是真实的。
"""

import asyncio
from datetime import timedelta
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    lesson_dir = Path(__file__).resolve().parent
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(lesson_dir / "lesson05_mcp_server.py")],
        cwd=str(lesson_dir),
    )

    # SDK 启动独立的本地服务进程，通过标准输入/输出收发 MCP 消息。
    async with stdio_client(server) as (read, write):
        async with ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=20)
        ) as session:
            initialized = await session.initialize()
            discovered = await session.list_tools()
            names = [tool.name for tool in discovered.tools]
            print("1. 真实 MCP 初始化：", initialized.serverInfo.name)
            print("2. 服务端公开的工具：", names)

            search_args = {
                "objective": "为校园失物招领选题寻找 Python Web 资料（离线教学）",
                "search_queries": ["Python Web 框架 官方文档"],
                "session_id": "lesson05-campus",
            }
            search = await session.call_tool("web_search", search_args)
            if search.isError:
                raise RuntimeError("本地教学搜索工具返回错误")
            # 本课服务明确返回一个 TextContent，其中装着 JSON 文本。
            search_data = json.loads(search.content[0].text)
            url = search_data["results"][0]["url"]
            print("3. 真实 tools/call 返回的静态结果：", search_data)

            fetch = await session.call_tool(
                "web_fetch",
                {
                    "urls": [url],
                    "objective": "演示读取搜索结果对应的资料（离线教学）",
                    "session_id": "lesson05-campus",
                },
            )
            if fetch.isError:
                raise RuntimeError("本地教学读取工具返回错误")
            fetch_data = json.loads(fetch.content[0].text)
            print("4. 真实 tools/call 返回的静态文本：", fetch_data)

            evidence = {
                "transport": "stdio",
                "real_mcp_communication": True,
                "external_network_used": False,
                "model_called": False,
                "content_is_fixture": True,
                "protocol_version": initialized.protocolVersion,
                "server_name": initialized.serverInfo.name,
                "tools": [tool.model_dump(mode="json") for tool in discovered.tools],
                "search": search_data,
                "fetch": fetch_data,
            }

    # async with 离开后释放会话和本课子进程相关资源。
    folder = lesson_dir / "outputs"
    folder.mkdir(exist_ok=True)
    path = folder / "lesson05-mcp.json"
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("5. 连接已关闭；证据已保存：", path)
    print("本课确实调用了本地 MCP 服务；搜索内容是静态样例，没有联网或调用模型。")


if __name__ == "__main__":
    asyncio.run(main())
