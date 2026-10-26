"""Live MCP smoke test. Saves metadata only, never source-page contents."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    config = json.loads(
        (ROOT / "extensions_config.json").read_text(encoding="utf-8-sig")
    )
    server = config["mcpServers"]["parallel-search"]
    if not server.get("enabled"):
        raise RuntimeError("parallel-search 未启用")
    async with streamablehttp_client(
        server["url"],
        headers=server.get("headers", {}),
        timeout=20,
        sse_read_timeout=45,
    ) as (read, write, _):
        async with ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=45)
        ) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            if not {"web_search", "web_fetch"} <= names:
                raise RuntimeError("服务缺少预期工具，请检查远程 schema 是否改变")
            session_id = str(uuid4())
            search = await session.call_tool(
                "web_search",
                {
                    "objective": "Find the official LangGraph overview documentation for a student comparing agent frameworks.",
                    "search_queries": ["LangGraph official overview documentation"],
                    "session_id": session_id,
                },
            )
            fetch = await session.call_tool(
                "web_fetch",
                {
                    "urls": [
                        "https://docs.langchain.com/oss/python/langgraph/overview"
                    ],
                    "objective": "Read the official LangGraph capabilities overview.",
                    "session_id": session_id,
                },
            )
            if search.isError or fetch.isError:
                raise RuntimeError("MCP 检索或原文读取返回错误")
            report = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "endpoint": server["url"],
                "server": initialized.serverInfo.name,
                "tools": sorted(names),
                "search_ok": not search.isError,
                "fetch_ok": not fetch.isError,
                "authentication": "anonymous (no API key)",
                "scope": "MCP SDK calls only; does not validate model-driven report generation",
            }
            (ROOT / "campus/local-verification.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
