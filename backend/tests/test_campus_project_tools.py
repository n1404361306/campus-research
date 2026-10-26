"""Campus tool regression; run with unittest without loading Gateway fixtures."""

import copy
import sys
import unittest
from pathlib import Path

import yaml
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from campus.tools import estimate_project_schedule  # noqa: E402


class ScheduleToolTests(unittest.TestCase):
    def setUp(self):
        self.args = {
            "features": [
                {"name": "登录", "estimated_hours": 8},
                {"name": "发布失物", "estimated_hours": 12},
                {"name": "搜索", "estimated_hours": 10},
            ],
            "hours_per_week": 10,
            "deadline_weeks": 4,
        }

    def test_default_buffer_and_feasible_deadline(self):
        result = estimate_project_schedule.invoke(self.args)
        self.assertEqual(result["base_hours"], 30)
        self.assertEqual(result["buffer_hours"], 6)
        self.assertEqual(result["total_hours"], 36)
        self.assertEqual(result["estimated_weeks"], 4)
        self.assertTrue(result["fits_deadline"])
        self.assertEqual(result["shortfall_hours"], 0)

    def test_tight_deadline_reports_shortfall(self):
        result = estimate_project_schedule.invoke({**self.args, "deadline_weeks": 3})
        self.assertFalse(result["fits_deadline"])
        self.assertEqual(result["capacity_hours"], 30)
        self.assertEqual(result["shortfall_hours"], 6)

    def test_buffer_rounds_up_and_can_be_disabled(self):
        result = estimate_project_schedule.invoke({**self.args, "buffer_percent": 1})
        self.assertEqual(result["buffer_hours"], 1)
        result = estimate_project_schedule.invoke({**self.args, "buffer_percent": 0})
        self.assertEqual(result["estimated_weeks"], 3)
        self.assertEqual(result["buffer_hours"], 0)

    def test_exact_boundary_fits(self):
        result = estimate_project_schedule.invoke({**self.args, "hours_per_week": 12, "deadline_weeks": 3})
        self.assertTrue(result["fits_deadline"])
        self.assertEqual(result["estimated_weeks"], 3)

    def test_week_count_rounds_up(self):
        result = estimate_project_schedule.invoke({**self.args, "hours_per_week": 7})
        self.assertEqual(result["estimated_weeks"], 6)

    def test_invalid_inputs_are_rejected(self):
        for update in [
            {"hours_per_week": 0},
            {"hours_per_week": True},
            {"hours_per_week": "10"},
            {"deadline_weeks": -1},
            {"buffer_percent": 101},
            {"features": []},
            {"features": [{"name": " ", "estimated_hours": 1}]},
            {"features": [{"name": "登录", "estimated_hours": -2}]},
            {"features": [{"name": "登录", "estimated_hours": True}]},
            {"features": [{"name": "登录", "estimated_hours": 1}] * 31},
            {"unexpected": "do not silently ignore misspelled parameters"},
        ]:
            with self.subTest(update=update), self.assertRaises(ValidationError):
                estimate_project_schedule.invoke({**self.args, **update})

    def test_missing_required_argument_is_rejected(self):
        with self.assertRaises(ValidationError):
            estimate_project_schedule.invoke({"features": self.args["features"]})

    def test_does_not_mutate_inputs_and_states_assumptions(self):
        before = copy.deepcopy(self.args)
        result = estimate_project_schedule.invoke(self.args)
        self.assertEqual(self.args, before)
        self.assertIn("输入工时", result["assumptions"])
        self.assertIn("保证", result["assumptions"])

    def test_tool_schema_is_available_to_the_model(self):
        function = convert_to_openai_tool(estimate_project_schedule)["function"]
        self.assertEqual(function["name"], "estimate_project_schedule")
        schema = function["parameters"]
        self.assertEqual(set(schema["required"]), {"features", "hours_per_week", "deadline_weeks"})
        self.assertEqual(schema["properties"]["buffer_percent"]["default"], 20)
        self.assertEqual(schema["properties"]["hours_per_week"]["minimum"], 1)

    def test_template_registration_resolves_real_tool(self):
        from deerflow.reflection import resolve_variable

        config = yaml.safe_load((ROOT / "campus/config.example.yaml").read_text(encoding="utf-8"))
        entry = next(item for item in config["tools"] if item["name"] == "estimate_project_schedule")
        self.assertIn(entry["group"], [group["name"] for group in config["tool_groups"]])
        self.assertIs(resolve_variable(entry["use"], BaseTool), estimate_project_schedule)

    def test_real_agent_graph_executes_and_returns_tool_message(self):
        from campus.lessons.lesson10_agent_tool import run_demo

        evidence = run_demo()
        results = evidence["tool_results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "success")
        self.assertEqual(results[0]["tool_call_id"], "schedule-valid")
        self.assertEqual(results[0]["result"]["total_hours"], 36)
        self.assertFalse(evidence["uses_external_model"])

    def test_graph_returns_validation_error_then_runs_corrected_call(self):
        from campus.lessons.lesson10_agent_tool import run_demo

        evidence = run_demo(invalid_first=True)
        results = evidence["tool_results"]
        self.assertEqual([item["status"] for item in results], ["error", "success"])
        self.assertEqual(results[0]["tool_call_id"], "schedule-invalid")
        self.assertEqual(results[1]["result"]["estimated_weeks"], 4)


if __name__ == "__main__":
    unittest.main()
