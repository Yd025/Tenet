"""
Graph Integrity Agent — validates the MongoDB-backed conversation DAG
for cycles, orphan nodes, and parent-child mismatches.

Reads live data via WebappDagStore (webapp REST API).
"""
from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.webapp_dag_store import WebappDagStore


class GraphIntegrityRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation (root_id) to validate")
    include_pruned: bool = Field(default=False, description="Include pruned nodes")


class GraphIntegrityResponse(BaseModel):
    success: bool
    valid: bool
    cycles_detected: int = 0
    orphan_nodes: int = 0
    parent_child_mismatches: int = 0
    message: str


graph_integrity_protocol = Protocol("graph-integrity", version="1.0")


class TenetGraphIntegrityAgent:
    """Validate DAG integrity against live MongoDB data via the webapp API."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-graph-integrity",
            seed="tenet_graph_integrity_seed_2024_secure",
            port=8018,
            mailbox=True,
            publish_agent_details=True,
        )
        self.config = config
        self.dag_store = WebappDagStore()
        self.setup_handlers()

    def setup_handlers(self):
        @graph_integrity_protocol.on_message(model=GraphIntegrityRequest)
        async def handle_validate(ctx: Context, sender: str, msg: GraphIntegrityRequest):
            try:
                await ctx.send(sender, self.validate_graph(msg.conversation_id, msg.include_pruned))
            except Exception as exc:
                await ctx.send(
                    sender,
                    GraphIntegrityResponse(
                        success=False,
                        valid=False,
                        message=f"Graph integrity check failed: {exc}",
                    ),
                )

    def validate_graph(self, conversation_id: str, include_pruned: bool = False) -> GraphIntegrityResponse:
        graph = self.dag_store.get_graph(conversation_id, include_pruned=include_pruned)
        raw_nodes = graph.get("nodes", [])

        # Build lookup: node_id -> node
        # Webapp nodes use parent_ids list; normalise to parent_id (first entry)
        nodes: dict[str, dict] = {}
        for n in raw_nodes:
            node_id = n.get("node_id")
            if not node_id:
                continue
            parent_ids = n.get("parent_ids") or []
            nodes[node_id] = {
                **n,
                "parent_id": parent_ids[0] if parent_ids else None,
                "children_ids": n.get("children_ids", []),
            }

        # Reconstruct children_ids from parent_ids (webapp doesn't store them)
        for node in nodes.values():
            for pid in (node.get("parent_ids") or []):
                if pid in nodes:
                    if node["node_id"] not in nodes[pid]["children_ids"]:
                        nodes[pid]["children_ids"].append(node["node_id"])

        orphan_nodes = 0
        mismatches = 0
        for node in nodes.values():
            parent_id = node.get("parent_id")
            if parent_id and parent_id not in nodes:
                orphan_nodes += 1
            for child_id in node.get("children_ids", []):
                child = nodes.get(child_id)
                if not child:
                    mismatches += 1
                elif child.get("parent_id") != node["node_id"]:
                    mismatches += 1

        # Cycle detection via iterative DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {nid: WHITE for nid in nodes}
        cycles = 0

        def dfs(start: str):
            nonlocal cycles
            stack = [(start, False)]
            while stack:
                node_id, returning = stack.pop()
                if returning:
                    colors[node_id] = BLACK
                    continue
                if colors[node_id] == GRAY:
                    continue
                if colors[node_id] == BLACK:
                    continue
                colors[node_id] = GRAY
                stack.append((node_id, True))
                for child_id in nodes[node_id].get("children_ids", []):
                    if child_id not in nodes:
                        continue
                    if colors[child_id] == GRAY:
                        cycles += 1
                    elif colors[child_id] == WHITE:
                        stack.append((child_id, False))

        for node_id in nodes:
            if colors[node_id] == WHITE:
                dfs(node_id)

        valid = cycles == 0 and orphan_nodes == 0 and mismatches == 0
        return GraphIntegrityResponse(
            success=True,
            valid=valid,
            cycles_detected=cycles,
            orphan_nodes=orphan_nodes,
            parent_child_mismatches=mismatches,
            message="Graph integrity validated" if valid else "Graph integrity violations found",
        )

    def run(self):
        self.agent.include(graph_integrity_protocol)
        print("🕸️ Tenet Graph Integrity Agent starting (webapp-backed)...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Graph Integrity Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetGraphIntegrityAgent().run()
