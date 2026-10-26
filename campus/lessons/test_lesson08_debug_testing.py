"""离线验证故障处理策略及交付检查，不依赖模型或外部服务。"""

from pathlib import Path
import tempfile
import unittest

from lesson08_debug_testing import run_case, verify_delivery


class RetryPolicyTests(unittest.TestCase):
    def test_temporary_limit_recovers_with_bounded_backoff(self):
        waits = []
        case = run_case("rate_limit_twice", pause=waits.append)
        self.assertEqual(case["status"], "success")
        self.assertEqual(case["calls"], 3)
        self.assertEqual(waits, [0.02, 0.04])

    def test_timeout_retries_a_read_only_query(self):
        case = run_case("timeout_once", pause=lambda _: None)
        self.assertEqual(case["status"], "success")
        self.assertEqual(case["calls"], 2)

    def test_persistent_limit_stops_at_three_attempts(self):
        case = run_case("always_rate_limited", pause=lambda _: None)
        self.assertEqual(case["calls"], 3)
        self.assertEqual(case["status"], "stopped")

    def test_exhausted_quota_is_not_retried(self):
        case = run_case("quota_exhausted", pause=lambda _: None)
        self.assertEqual(case["calls"], 1)
        self.assertEqual(case["error_type"], "QuotaExhaustedError")

    def test_bad_arguments_do_not_start_a_query(self):
        case = run_case("bad_arguments", pause=lambda _: None)
        self.assertEqual(case["calls"], 0)
        self.assertEqual(case["budget"]["used"], 0)

    def test_tool_error_flag_is_not_treated_as_success(self):
        case = run_case("tool_error", pause=lambda _: None)
        self.assertEqual(case["calls"], 1)
        self.assertEqual(case["error_type"], "ToolResultError")

    def test_budget_blocks_the_next_attempt(self):
        case = run_case("rate_limit_twice", limit=5, pause=lambda _: None)
        self.assertEqual(case["calls"], 1)
        self.assertEqual(case["error_type"], "BudgetExceededError")


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "report.md"
        self.copy = Path(self.directory.name) / "copy.md"
        self.todos = [{"content": "交付报告", "status": "completed"}]

    def verify(self):
        return verify_delivery(self.path, [str(self.path)], self.todos, self.copy)

    def test_completed_todos_cannot_hide_a_missing_file(self):
        result = self.verify()
        self.assertTrue(result["checks"]["todos_completed"])
        self.assertFalse(result["mechanical_checks_passed"])

    def test_partial_report_is_rejected(self):
        self.path.write_text("# 只有标题", encoding="utf-8")
        self.copy.write_bytes(self.path.read_bytes())
        self.assertFalse(self.verify()["mechanical_checks_passed"])

    def test_changed_copy_is_rejected(self):
        self.path.write_text("技术路线\n开发计划\n参考来源", encoding="utf-8")
        self.copy.write_text("文件内容被改变", encoding="utf-8")
        self.assertFalse(self.verify()["checks"]["local_copy_matches"])

    def test_complete_local_fixture_passes_only_mechanical_checks(self):
        self.path.write_text("技术路线\n开发计划\n参考来源", encoding="utf-8")
        self.copy.write_bytes(self.path.read_bytes())
        self.assertTrue(self.verify()["mechanical_checks_passed"])


if __name__ == "__main__":
    unittest.main()
