import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from run_all_agents import AGENTS


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex((host, port)) == 0


def _resolve_python() -> str:
    """Prefer local venv python when available."""
    local_venv_python = Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
    if local_venv_python.exists():
        return str(local_venv_python)
    return sys.executable


def _read_stderr(process: subprocess.Popen) -> str:
    if process.stderr is None:
        return ""
    try:
        return process.stderr.read().strip()
    except Exception:
        return ""


def start_agent(script_path: str, python_exe: str):
    path = Path(script_path)
    if not path.exists():
        print(f"❌ Script not found: {script_path}")
        return None
    package_root = Path(__file__).resolve().parent
    module_name = script_path.replace("/", ".").removesuffix(".py")
    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{package_root}:{existing_pythonpath}" if existing_pythonpath else str(package_root)
    )
    process = subprocess.Popen(
        [python_exe, "-m", module_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(package_root),
        env=env,
    )
    return process


async def check_health():
    healthy = 0
    for agent in AGENTS:
        running = await asyncio.to_thread(is_port_open, agent["port"])
        if running:
            healthy += 1
            print(f"   ✅ {agent['name']:22} localhost:{agent['port']}")
        else:
            print(f"   ❌ {agent['name']:22} localhost:{agent['port']}")
    print(f"\n📊 Healthy agents: {healthy}/{len(AGENTS)}")
    return healthy


def main():
    print("🚀 Starting Tenet local agents")
    print("=" * 56)
    python_exe = _resolve_python()
    print(f"🐍 Python executable: {python_exe}")
    processes = []
    proc_by_name = {}
    for agent in AGENTS:
        process = start_agent(agent["script"], python_exe)
        if process:
            processes.append(process)
            proc_by_name[agent["name"]] = process
            print(f"✅ Started {agent['name']} on port {agent['port']} (PID {process.pid})")
        time.sleep(0.8)

    print("\n⏳ Waiting for initialization...")
    time.sleep(4)
    print("\n🧾 Checking process exits...")
    crashed = 0
    for agent in AGENTS:
        proc = proc_by_name.get(agent["name"])
        if not proc:
            continue
        exit_code = proc.poll()
        if exit_code is not None:
            crashed += 1
            stderr = _read_stderr(proc)
            print(f"   ❌ {agent['name']:22} exited with code {exit_code}")
            if stderr:
                first_lines = "\n".join(stderr.splitlines()[:5])
                print(f"      stderr: {first_lines}")
        else:
            print(f"   ✅ {agent['name']:22} process alive")

    print("\n🔍 Checking local ports...")
    healthy = asyncio.run(check_health())
    if healthy == 0 and crashed > 0:
        print(
            "\n⚠️  No ports are open and processes crashed. "
            "The stderr snippets above show the root cause."
        )

    print("\n💡 Keep this terminal open. Press Ctrl+C to stop all agents.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping agents...")
        for process in processes:
            process.terminate()
        time.sleep(1)
        print("✅ All agents stopped.")


if __name__ == "__main__":
    main()
