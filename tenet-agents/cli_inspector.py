import asyncio
import socket
from datetime import datetime


AGENT_PORTS = {
    "orchestrator": 8001,
    "privacy_router": 8002,
    "branch_manager": 8003,
    "model_coordinator": 8004,
    "context_keeper": 8005,
    "branch_summarizer": 8006,
    "branch_merger": 8007,
    "branch_pruner": 8008,
    "node_pruner": 8009,
    "semantic_search": 8010,
    "conversation_exporter": 8011,
    "tag_manager": 8012,
    "rollback_agent": 8013,
    "diff_viewer": 8014,
    "branch_comparator": 8015,
    "storage_optimizer": 8016,
    "resource_monitor": 8017,
    "graph_integrity": 8018,
    "capability_registry": 8019,
    "gateway_http": 9000,
}


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


async def check_agent(name: str, port: int):
    running = await asyncio.to_thread(is_port_open, port)
    if running:
        print(f"\033[92m{name:22} ✅ Running (:{port})\033[0m")
    else:
        print(f"\033[91m{name:22} ❌ Offline (:{port})\033[0m")


async def main():
    print("\n🔍 Tenet Agent Inspector")
    print("=" * 48)
    tasks = [check_agent(name, port) for name, port in AGENT_PORTS.items()]
    await asyncio.gather(*tasks)
    print("=" * 48)
    print("Last check:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    asyncio.run(main())
