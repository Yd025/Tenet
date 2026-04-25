from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.local_runtime import dag_store


class GraphIntegrityRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation to validate")
    include_pruned: bool = Field(default=True, description="Validate including pruned nodes")


class GraphIntegrityResponse(BaseModel):
    success: bool
    valid: bool
    cycles_detected: int = 0
    orphan_nodes: int = 0
    parent_child_mismatches: int = 0
    message: str


graph_integrity_protocol = Protocol("graph-integrity", version="1.0")


class TenetGraphIntegrityAgent:
    """Validate DAG integrity and report cycle/orphan/mismatch issues."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-graph-integrity",
            seed="tenet_graph_integrity_seed_2024_secure",
            port=8018,
        )
        self.config = config
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

    def validate_graph(self, conversation_id: str, include_pruned: bool = True) -> GraphIntegrityResponse:
        graph = dag_store.get_graph(conversation_id, include_pruned=include_pruned)
        nodes = {n["node_id"]: n for n in graph.get("nodes", [])}

        orphan_nodes = 0
        mismatches = 0
        for node in nodes.values():
            parent_id = node.get("parent_id")
            if parent_id and parent_id not in nodes:
                orphan_nodes += 1
            for child_id in node.get("children_ids", []):
                child = nodes.get(child_id)
                if not child or child.get("parent_id") != node["node_id"]:
                    mismatches += 1

        # Cycle detection via DFS colors.
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {node_id: WHITE for node_id in nodes}
        cycles = 0

        def dfs(node_id: str):
            nonlocal cycles
            colors[node_id] = GRAY
            for child_id in nodes[node_id].get("children_ids", []):
                if child_id not in nodes:
                    continue
                if colors[child_id] == GRAY:
                    cycles += 1
                elif colors[child_id] == WHITE:
                    dfs(child_id)
            colors[node_id] = BLACK

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
        print("🕸️ Tenet Graph Integrity Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Graph Integrity Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetGraphIntegrityAgent().run()
