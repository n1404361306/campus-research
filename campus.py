"""Local CampusResearch launcher; reuses the original DeerFlow services."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
BACKEND_PYTHON = (
    ROOT
    / "backend"
    / ".venv"
    / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
)


def configure(root: Path = ROOT) -> list[str]:
    """Seed local files once, preserving credentials and user configuration."""
    created = []
    for source, destination in (
        ("campus/config.example.yaml", "config.yaml"),
        ("campus/extensions_config.example.json", "extensions_config.json"),
        ("campus/.env.example", ".env"),
    ):
        try:
            with (root / destination).open("x", encoding="utf-8") as target:
                target.write((root / source).read_text(encoding="utf-8-sig"))
            created.append(destination)
        except FileExistsError:
            pass
    return created


def runtime_env() -> tuple[dict[str, str], bool]:
    from dotenv import dotenv_values

    env = os.environ.copy()
    for name, value in dotenv_values(ROOT / ".env").items():
        if value is not None:
            env.setdefault(name, value)
    env.update(
        DEER_FLOW_PROJECT_ROOT=str(ROOT),
        DEER_FLOW_CONFIG_PATH=str(ROOT / "config.yaml"),
        DEER_FLOW_ENV_FILE=str(ROOT / ".env"),
        DEER_FLOW_HOME=str(ROOT / "backend" / ".deer-flow"),
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
    )
    # Gateway starts in backend/, while campus.tools lives at the project root.
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) + (
        os.pathsep + existing_pythonpath if existing_pythonpath else ""
    )
    ready = all(
        env.get(name, "").strip()
        for name in (
            "CAMPUS_MODEL_NAME",
            "CAMPUS_MODEL_BASE_URL",
            "CAMPUS_MODEL_API_KEY",
        )
    )
    if not ready:
        # Fail locally rather than send a dummy key to an external provider.
        env.update(
            CAMPUS_MODEL_NAME="configure-model-first",
            CAMPUS_MODEL_BASE_URL="http://127.0.0.1:9/v1",
            CAMPUS_MODEL_API_KEY="campus-not-configured",
        )
    return env, ready


def find_node() -> str:
    bundled = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    )
    for candidate in (shutil.which("node"), str(bundled)):
        if candidate and Path(candidate).is_file():
            version = subprocess.check_output(
                [candidate, "--version"], text=True
            ).strip()
            if int(version.lstrip("v").split(".")[0]) >= 22:
                return candidate
    raise RuntimeError("需要 Node.js 22 或更新版本。安装后重新打开终端。")


def require_free_port(port: int) -> None:
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"端口 {port} 已被占用，请先停止原来的服务。")


def start(preview: bool, production: bool = False) -> None:
    env, ready = runtime_env()
    if not ready and not preview:
        raise RuntimeError(
            "请在根目录 .env 填写模型名称、接口地址和 API Key；仅看界面可用 start --preview。"
        )
    scanner = (
        ROOT / "backend/packages/harness/deerflow/skills/skillscan/orchestrator.py"
    )
    if not scanner.is_file():
        raise RuntimeError(
            "缺少上游源码 backend/packages/harness/deerflow/skills/skillscan/orchestrator.py。请检查安全软件隔离记录，并恢复经过核实的原文件。"
        )
    node = find_node()
    if not (ROOT / "frontend/node_modules/next").exists():
        raise RuntimeError(
            "前端依赖未安装，请先在 frontend 执行 pnpm install --frozen-lockfile。"
        )
    if production and not (ROOT / "frontend/.next/BUILD_ID").is_file():
        raise RuntimeError(
            "还没有生产构建，请先在 frontend 执行 pnpm exec next build --webpack。"
        )
    frontend_command = (
        [
            node,
            "node_modules/next/dist/bin/next",
            "start",
            "--hostname",
            "127.0.0.1",
            "--port",
            "3000",
        ]
        if production
        else [node, "scripts/dev.mjs", "--hostname", "127.0.0.1"]
    )
    for port in (8001, 3000):
        require_free_port(port)
    env["PATH"] = str(Path(node).parent) + os.pathsep + env.get("PATH", "")
    env["CAMPUS_MODEL_CONFIGURED"] = "1" if ready else "0"
    env["DEER_FLOW_INTERNAL_GATEWAY_BASE_URL"] = "http://127.0.0.1:8001"
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    processes: list[subprocess.Popen] = []
    handles = []
    try:
        for name, command, cwd in (
            (
                "gateway",
                [
                    str(BACKEND_PYTHON),
                    "-m",
                    "uvicorn",
                    "app.gateway.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8001",
                ],
                ROOT / "backend",
            ),
            (
                "frontend",
                frontend_command,
                ROOT / "frontend",
            ),
        ):
            handle = (logs / f"campus-{name}.log").open("w", encoding="utf-8")
            handles.append(handle)
            processes.append(
                subprocess.Popen(
                    command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT
                )
            )
        print(
            "正在启动 CampusResearch；日志：logs/campus-gateway.log、logs/campus-frontend.log",
            flush=True,
        )
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("服务提前退出，请查看 logs/campus-*.log。")
            try:
                with urlopen("http://127.0.0.1:8001/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("后端启动超时，请查看日志。")
        print(
            "工作台地址：http://127.0.0.1:3000（前端首次编译可能需要一点时间）",
            flush=True,
        )
        if not ready:
            print(
                "当前为界面预览：未配置模型，不能生成回答。填写 .env 后停止并重新启动。",
                flush=True,
            )
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        raise RuntimeError("一个服务已退出，请查看日志。")
    except KeyboardInterrupt:
        print("正在停止服务…", flush=True)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                    )
                else:
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for handle in handles:
            handle.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusResearch 本地启动器")
    parser.add_argument("command", choices=["configure", "start"])
    parser.add_argument("--preview", action="store_true", help="不配置模型，仅预览界面")
    parser.add_argument(
        "--production", action="store_true", help="使用已有生产构建启动"
    )
    args = parser.parse_args()
    if args.command == "configure":
        created = configure()
        print("已生成：" + ("、".join(created) or "无；已有配置均保留"))
        return
    if not BACKEND_PYTHON.exists():
        parser.error("后端依赖未安装；请先执行 uv sync --project backend --frozen。")
    if Path(sys.executable).resolve() != BACKEND_PYTHON.resolve():
        raise SystemExit(
            subprocess.call(
                [str(BACKEND_PYTHON), str(Path(__file__)), *sys.argv[1:]], cwd=ROOT
            )
        )
    try:
        start(args.preview, args.production)
    except RuntimeError as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
