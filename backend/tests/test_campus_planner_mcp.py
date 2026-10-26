"""Real local stdio MCP and adapter/graph tests; never calls an external model."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from campus.mcp_server import estimate_schedule  # noqa: E402
from campus.tools import ScheduleInput, estimate_project_schedule  # noqa: E402
from campus.lessons.lesson11_mcp_tool import (  # noqa: E402
    SERVER_NAME,
    load_connection,
    run_agent_demo,
    run_protocol_demo,
)

PROFILE = ROOT / "campus/extensions_config.example.json"
ARGUMENTS = {
    "features": [
        {"name": "登录", "estimated_hours": 8},
        {"name": "发布失物", "estimated_hours": 12},
        {"name": "搜索", "estimated_hours": 10},
    ],
    "hours_per_week": 10,
    "deadline_weeks": 4,
}


class PlannerMcpTests(unittest.TestCase):
    def test_wrapper_reuses_local_tool_result(self):
        self.assertEqual(
            estimate_schedule(ScheduleInput.model_validate(ARGUMENTS)),
            estimate_project_schedule.invoke(ARGUMENTS),
        )

    def test_project_config_resolves_executable_and_server_file(self):
        connection = load_connection(PROFILE)
        self.assertEqual(connection["transport"], "stdio")
        self.assertEqual(Path(connection["command"]), Path(sys.executable))
        self.assertEqual(connection["args"], [str(ROOT / "campus/mcp_server.py")])
        self.assertEqual(connection["env"]["PYTHONIOENCODING"], "utf-8")

    def test_disabled_server_is_not_started(self):
        config = json.loads(PROFILE.read_text(encoding="utf-8"))
        config["mcpServers"][SERVER_NAME]["enabled"] = False
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "extensions.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "未启用"):
                load_connection(path)

    def test_reserved_environment_is_restored_after_config_resolution(self):
        with patch.dict("os.environ", {"CAMPUS_MCP_PYTHON": "previous-value"}):
            load_connection(PROFILE)
            import os

            self.assertEqual(os.environ["CAMPUS_MCP_PYTHON"], "previous-value")


class PlannerMcpProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_protocol_discovery_and_calculation(self):
        result = await run_protocol_demo(load_connection(PROFILE))
        self.assertTrue(result["real_mcp_communication"])
        self.assertEqual(result["tool_names"], ["estimate_project_schedule"])
        tool = result["tools"][0]
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        self.assertIn("request", tool["inputSchema"]["required"])
        self.assertEqual(result["success"]["total_hours"], 36)
        self.assertEqual(result["success"]["estimated_weeks"], 4)
        self.assertFalse(result["tight_deadline"]["fits_deadline"])
        self.assertEqual(result["tight_deadline"]["shortfall_hours"], 6)

    async def test_invalid_mcp_arguments_are_errors_and_session_stays_usable(self):
        result = await run_protocol_demo(load_connection(PROFILE))
        self.assertEqual(len(result["invalid_calls"]), 3)
        self.assertTrue(all(item["is_error"] for item in result["invalid_calls"]))
        self.assertEqual(result["success_after_error"]["total_hours"], 36)

    async def test_adapter_and_real_agent_graph_return_correlated_result(self):
        result = await run_agent_demo(load_connection(PROFILE))
        self.assertEqual(result["tool_name"], "campus-planner_estimate_project_schedule")
        self.assertFalse(result["uses_external_model"])
        self.assertEqual(result["tool_call_id"], "mcp-schedule-valid")
        self.assertEqual(result["result"], estimate_project_schedule.invoke(ARGUMENTS))
        self.assertTrue(result["adapter_error_is_tool_exception"])
        self.assertIn("tool", [item["type"] for item in result["messages"]])


if __name__ == "__main__":
    unittest.main()
