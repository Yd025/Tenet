import asyncio
import socket
import threading
import time
from datetime import datetime
from typing import Dict

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


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

app = FastAPI(title="Tenet Local Inspector")


def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


async def collect_status() -> Dict[str, Dict]:
    status = {}
    for name, port in AGENT_PORTS.items():
        running = await asyncio.to_thread(_is_port_open, port)
        status[name] = {
            "port": port,
            "status": "running" if running else "offline",
            "last_check": datetime.now().isoformat(),
        }
    return status


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    data = await collect_status()
    rows = []
    for name, info in data.items():
        emoji = "✅" if info["status"] == "running" else "❌"
        rows.append(
            f"<tr><td>{name}</td><td>{info['port']}</td>"
            f"<td>{emoji} {info['status']}</td><td>{info['last_check']}</td></tr>"
        )
    html = (
        "<html><head><title>Tenet Inspector</title></head><body>"
        "<h1>Tenet Local Agent Inspector</h1>"
        "<p>Refresh to update status.</p>"
        "<table border='1' cellpadding='8' cellspacing='0'>"
        "<tr><th>Agent</th><th>Port</th><th>Status</th><th>Last Check</th></tr>"
        + "".join(rows)
        + "</table></body></html>"
    )
    return HTMLResponse(content=html)


@app.get("/api/status")
async def api_status():
    return await collect_status()


if __name__ == "__main__":
    print("🔍 Tenet Inspector starting at http://localhost:9100")
    uvicorn.run(app, host="0.0.0.0", port=9100)
