import asyncio
import os
import socket
import sys
import threading
import time
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from protocols.branch_protocol import BranchAction, BranchRequest
from protocols.chat_protocol import ChatRequest, ExecutionLocation
from utils.local_runtime import capability_registry, dag_store, memory_store, router


class GatewayRequest(BaseModel):
    request_type: str = Field(..., description="chat, branch, search, memory, storage")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Request payload")
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    source: Optional[str] = Field(None, description="agentverse, local, cli, test")


class GatewayResponse(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    message: str
    source: str = Field(default="tenet-gateway", description="Response source")


gateway_protocol = Protocol("gateway", version="1.0")
app = FastAPI(title="Tenet Gateway")

config = AgentConfig()
GATEWAY_HTTP_PORT = int(os.getenv("TENET_GATEWAY_HTTP_PORT", "9000"))
GATEWAY_UAGENT_PORT = int(os.getenv("TENET_GATEWAY_UAGENT_PORT", "9020"))
GATEWAY_ENDPOINT = os.getenv("TENET_AGENT_ENDPOINT", f"http://127.0.0.1:{GATEWAY_UAGENT_PORT}/submit")
gateway_agent = Agent(
    name="tenet-gateway",
    seed="tenet_gateway_seed_2024_secure",
    port=GATEWAY_UAGENT_PORT,
    endpoint=[GATEWAY_ENDPOINT],
    mailbox=True,
    publish_agent_details=True,
)

LOCAL_AGENTS = {
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
}


def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex((host, port)) == 0


def _resolve_specialist(prompt: str, privacy_level: str) -> Optional[Dict[str, Any]]:
    text = prompt.lower()
    if privacy_level == "sensitive":
        return capability_registry.find_best_agent("secure_routing")
    if any(k in text for k in ("search", "retrieve", "find")):
        return capability_registry.find_best_agent("semantic_search")
    if any(k in text for k in ("branch", "rollback", "merge", "fork", "prune")):
        return capability_registry.find_best_agent("branch_management")
    if any(k in text for k in ("memory", "context", "recall")):
        return capability_registry.find_best_agent("context_management")
    return capability_registry.find_best_agent("model_management")


def process_gateway_request(msg: GatewayRequest) -> GatewayResponse:
    request_type = msg.request_type.lower().strip()
    payload = msg.payload or {}
    source = msg.source or "unknown"
    print(f"📨 Gateway request from={source} type={request_type}")

    if request_type == "chat":
        chat = ChatRequest(**payload)
        privacy = router.analyze_privacy(chat.prompt, chat.privacy_level.value)
        specialist = _resolve_specialist(chat.prompt, privacy["privacy_level"])
        response_text = (
            f"Gateway local response for '{chat.prompt[:80]}'. "
            "Processed through local-only orchestration."
        )
        node = dag_store.add_node(
            conversation_id=chat.conversation_id,
            branch_id=chat.branch_id,
            parent_id=(chat.context or {}).get("parent_id") if chat.context else None,
            prompt=chat.prompt,
            response=response_text,
            model_used=config.DEFAULT_LOCAL_MODEL,
            execution_location=ExecutionLocation.LOCAL.value,
            metadata={
                "privacy_level": privacy["privacy_level"],
                "gateway": True,
                "selected_specialist_agent": specialist.get("agent_name") if specialist else "tenet-orchestrator",
            },
        )
        memory_store.store(node, chat.conversation_id, node.get("branch_id"))
        return GatewayResponse(
            success=True,
            data={
                "response": response_text,
                "node_id": node["node_id"],
                "conversation_id": chat.conversation_id,
                "branch_id": node.get("branch_id"),
                "selected_specialist_agent": node["metadata"]["selected_specialist_agent"],
            },
            message="Chat processed successfully",
            source="tenet-gateway",
        )

    if request_type == "branch":
        branch = BranchRequest(**payload)
        if branch.action in {BranchAction.CREATE, BranchAction.FORK}:
            created = dag_store.create_branch(branch.conversation_id, branch.node_id, branch.branch_name)
            return GatewayResponse(success=True, data=created, message="Branch created", source="tenet-gateway")
        if branch.action == BranchAction.LIST:
            branches = dag_store.list_branches(branch.conversation_id, include_pruned=branch.include_pruned)
            return GatewayResponse(success=True, data={"branches": branches}, message="Branches listed", source="tenet-gateway")
        if branch.action == BranchAction.SWITCH:
            switched = dag_store.switch_branch(branch.conversation_id, branch.branch_id or "")
            return GatewayResponse(success=True, data=switched, message="Branch switched", source="tenet-gateway")
        if branch.action == BranchAction.ROLLBACK:
            rolled = dag_store.rollback(branch.conversation_id, branch.branch_id or "", branch.target_node_id or "")
            return GatewayResponse(success=True, data=rolled, message="Rollback completed", source="tenet-gateway")
        if branch.action == BranchAction.DELETE:
            ok = dag_store.delete_branch(branch.conversation_id, branch.branch_id or "")
            return GatewayResponse(success=ok, data={"deleted": ok}, message="Branch deleted" if ok else "Delete failed", source="tenet-gateway")
        if branch.action == BranchAction.GET_GRAPH:
            graph = dag_store.get_graph(branch.conversation_id, include_pruned=branch.include_pruned)
            return GatewayResponse(success=True, data=graph, message="Graph loaded", source="tenet-gateway")
        return GatewayResponse(success=False, message=f"Unsupported branch action: {branch.action}", source="tenet-gateway")

    if request_type == "search":
        query = str(payload.get("query", "")).lower()
        conv_id = payload.get("conversation_id")
        branch_id = payload.get("branch_id")
        limit = int(payload.get("limit", 10))
        nodes = dag_store.list_nodes(conv_id, branch_id=branch_id, include_pruned=False)
        results = []
        for node in nodes:
            content = f"{node.get('prompt', '')}\n{node.get('response', '')}".lower()
            if query and query in content:
                results.append(
                    {
                        "node_id": node["node_id"],
                        "conversation_id": node["conversation_id"],
                        "branch_id": node.get("branch_id"),
                        "content": f"{node.get('prompt', '')}\n{node.get('response', '')}"[:400],
                    }
                )
            if len(results) >= limit:
                break
        return GatewayResponse(success=True, data={"results": results, "total_results": len(results)}, message="Search completed", source="tenet-gateway")

    return GatewayResponse(success=False, data={}, message=f"Unknown request_type: {msg.request_type}", source="tenet-gateway")


@gateway_protocol.on_message(model=GatewayRequest)
async def handle_gateway_message(ctx: Context, sender: str, msg: GatewayRequest):
    try:
        await ctx.send(sender, process_gateway_request(msg))
    except Exception as exc:
        await ctx.send(sender, GatewayResponse(success=False, message=f"Gateway error: {exc}"))


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "tenet-gateway",
        "timestamp": time.time(),
        "uagent_port": GATEWAY_UAGENT_PORT,
        "http_port": GATEWAY_HTTP_PORT,
    }


@app.get("/local-agents")
async def local_agents_status() -> Dict[str, Any]:
    status: Dict[str, Dict[str, Any]] = {}
    for name, port in LOCAL_AGENTS.items():
        running = await asyncio.to_thread(_is_port_open, port)
        status[name] = {"port": port, "running": running}
    return status


@app.post("/process", response_model=GatewayResponse)
async def process_http(request: GatewayRequest) -> GatewayResponse:
    return process_gateway_request(request)


def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=GATEWAY_HTTP_PORT)


def ensure_gateway_ports_available():
    in_use = []
    if _is_port_open(GATEWAY_HTTP_PORT):
        in_use.append(GATEWAY_HTTP_PORT)
    if _is_port_open(GATEWAY_UAGENT_PORT):
        in_use.append(GATEWAY_UAGENT_PORT)
    if in_use:
        print(f"❌ Gateway ports already in use: {', '.join(str(p) for p in in_use)}")
        print("   Stop existing gateway process or pick new ports:")
        print("   export TENET_GATEWAY_HTTP_PORT=9101")
        print("   export TENET_GATEWAY_UAGENT_PORT=9102")
        print("   export TENET_AGENT_ENDPOINT=http://127.0.0.1:9102/submit")
        sys.exit(1)


if __name__ == "__main__":
    ensure_gateway_ports_available()
    threading.Thread(target=run_fastapi, daemon=True).start()
    gateway_agent.include(gateway_protocol)
    print("🌐 Tenet Gateway Agent starting...")
    print(f"📍 Agent Address: {gateway_agent.address}")
    print(f"🔗 uAgent endpoint registered: {GATEWAY_ENDPOINT}")
    print(f"🔗 HTTP endpoint: http://localhost:{GATEWAY_HTTP_PORT}/process")
    print(f"🔗 Local agent ports configured: {len(LOCAL_AGENTS)}")
    print("🔍 Checking local agent ports...")
    for agent_name, port in LOCAL_AGENTS.items():
        icon = "✅" if _is_port_open(port) else "❌"
        print(f"   {icon} {agent_name:20} localhost:{port}")
    gateway_agent.run()
