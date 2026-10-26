"""Offline regression for preserving local credentials/configuration."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "campus_launcher", Path(__file__).resolve().parents[1] / "campus.py"
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class ConfigureTests(unittest.TestCase):
    def test_gateway_working_directory_can_import_campus_tool(self):
        env, _ = launcher.runtime_env()
        child = subprocess.run(
            [
                str(launcher.BACKEND_PYTHON),
                "-c",
                "from campus.tools import estimate_project_schedule; print(estimate_project_schedule.name)",
            ],
            cwd=launcher.ROOT / "backend",
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        self.assertEqual(child.stdout.strip(), "estimate_project_schedule")

    def test_runtime_exposes_campus_package_and_preserves_pythonpath(self):
        with (
            patch.dict(launcher.os.environ, {"PYTHONPATH": "existing-import-path"}),
        ):
            env, _ = launcher.runtime_env()
        self.assertEqual(
            env["PYTHONPATH"],
            str(launcher.ROOT) + launcher.os.pathsep + "existing-import-path",
        )

    def test_preview_fails_locally_when_model_settings_are_incomplete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "CAMPUS_MODEL_BASE_URL=https://example.com/v1\n", encoding="utf-8"
            )
            with (
                patch.object(launcher, "ROOT", root),
                patch.dict(launcher.os.environ, {}, clear=True),
            ):
                env, ready = launcher.runtime_env()
            self.assertFalse(ready)
            self.assertEqual(env["CAMPUS_MODEL_BASE_URL"], "http://127.0.0.1:9/v1")
            self.assertEqual(env["CAMPUS_MODEL_API_KEY"], "campus-not-configured")

    def test_complete_settings_preserve_explicit_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "CAMPUS_MODEL_NAME=file-model\nCAMPUS_MODEL_BASE_URL=https://example.com/v1\nCAMPUS_MODEL_API_KEY=test-key-not-real\n",
                encoding="utf-8",
            )
            with (
                patch.object(launcher, "ROOT", root),
                patch.dict(
                    launcher.os.environ,
                    {"CAMPUS_MODEL_NAME": "environment-model"},
                    clear=True,
                ),
            ):
                env, ready = launcher.runtime_env()
            self.assertTrue(ready)
            self.assertEqual(env["CAMPUS_MODEL_NAME"], "environment-model")
            self.assertEqual(env["CAMPUS_MODEL_API_KEY"], "test-key-not-real")

    def test_reconfigure_preserves_local_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "campus").mkdir()
            for name in (
                "config.example.yaml",
                "extensions_config.example.json",
                ".env.example",
            ):
                (root / "campus" / name).write_text("校园模板", encoding="utf-8")
            (root / ".env").write_text("existing-local-secret", encoding="utf-8")
            self.assertEqual(
                launcher.configure(root), ["config.yaml", "extensions_config.json"]
            )
            self.assertEqual(
                (root / ".env").read_text(encoding="utf-8"), "existing-local-secret"
            )
            self.assertEqual(launcher.configure(root), [])
            self.assertEqual(
                (root / "config.yaml").read_text(encoding="utf-8"), "校园模板"
            )


if __name__ == "__main__":
    unittest.main()
