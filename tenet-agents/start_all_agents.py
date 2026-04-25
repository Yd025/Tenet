import asyncio
import os
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from run_all_agents import AGENTS


STABILIZATION_WAIT_SECONDS = 8


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


INSPECTOR_RE = re.compile(r"https://agentverse\.ai/inspect/\?uri=\S+")


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


def print_process_status(proc_by_name: dict, logs_buffer: dict[str, list[str]]) -> int:
    print("\n🧾 Checking process exits...")
    crashed = 0
    for agent in AGENTS:
        proc = proc_by_name.get(agent["name"])
        if not proc:
            continue
        exit_code = proc.poll()
        if exit_code is not None:
            crashed += 1
            stderr = "\n".join(logs_buffer.get(agent["name"], [])[-5:])
            print(f"   ❌ {agent['name']:22} exited with code {exit_code}")
            if stderr:
                print(f"      recent logs:\n{stderr}")
        else:
            print(f"   ✅ {agent['name']:22} process alive")
    return crashed


def _stream_pipe(
    pipe,
    agent_name: str,
    stream_name: str,
    logs_buffer: dict[str, list[str]],
    inspector_links: set[str],
    lock: threading.Lock,
):
    if pipe is None:
        return
    try:
        for line in pipe:
            line = line.rstrip("\n")
            if not line:
                continue
            with lock:
                logs_buffer.setdefault(agent_name, []).append(line)
                # Keep only the most recent lines per agent to bound memory.
                if len(logs_buffer[agent_name]) > 200:
                    logs_buffer[agent_name] = logs_buffer[agent_name][-200:]
                for match in INSPECTOR_RE.findall(line):
                    inspector_links.add(match)
            print(f"[{agent_name}][{stream_name}] {line}")
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def main():
    print("🚀 Starting Tenet local agents")
    print("=" * 56)
    python_exe = _resolve_python()
    print(f"🐍 Python executable: {python_exe}")
    processes = []
    proc_by_name = {}
    logs_buffer: dict[str, list[str]] = {}
    inspector_links: set[str] = set()
    lock = threading.Lock()
    for agent in AGENTS:
        process = start_agent(agent["script"], python_exe)
        if process:
            processes.append(process)
            proc_by_name[agent["name"]] = process
            print(f"✅ Started {agent['name']} on port {agent['port']} (PID {process.pid})")
            threading.Thread(
                target=_stream_pipe,
                args=(process.stdout, agent["name"], "stdout", logs_buffer, inspector_links, lock),
                daemon=True,
            ).start()
            threading.Thread(
                target=_stream_pipe,
                args=(process.stderr, agent["name"], "stderr", logs_buffer, inspector_links, lock),
                daemon=True,
            ).start()
        time.sleep(0.8)

    print("\n⏳ Waiting for initialization...")
    time.sleep(4)
    crashed = print_process_status(proc_by_name, logs_buffer)
    print("\n🔍 Checking local ports...")
    healthy = asyncio.run(check_health())
    if healthy < len(AGENTS):
        print(
            f"\n⏱️  Waiting {STABILIZATION_WAIT_SECONDS}s for late-starting agents..."
        )
        time.sleep(STABILIZATION_WAIT_SECONDS)
        print("\n🧾 Re-checking process exits after stabilization...")
        crashed = print_process_status(proc_by_name, logs_buffer)
        print("\n🔍 Re-checking local ports after stabilization...")
        healthy = asyncio.run(check_health())
    if healthy == 0 and crashed > 0:
        print(
            "\n⚠️  No ports are open and processes crashed. "
            "The stderr snippets above show the root cause."
        )
    if inspector_links:
        print("\n🔗 Inspector links discovered:")
        for link in sorted(inspector_links):
            print(f"   {link}")
    else:
        print("\n🔗 No inspector links discovered yet. They may appear a few seconds after startup.")

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
