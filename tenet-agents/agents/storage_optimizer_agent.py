from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.local_runtime import dag_store, model_registry


class StorageOptimizeRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation to optimize")
    prune_soft_deleted: bool = Field(default=True, description="Permanently remove soft-pruned nodes")
    unload_unused_models: bool = Field(default=True, description="Unload models not recently used")


class StorageOptimizeResponse(BaseModel):
    success: bool
    nodes_removed: int = 0
    models_unloaded: int = 0
    estimated_space_freed_mb: float = 0.0
    message: str


storage_optimizer_protocol = Protocol("storage-optimize", version="1.0")


class TenetStorageOptimizerAgent:
    """Optimize local storage by compacting pruned data and unloading idle models."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-storage-optimizer",
            seed="tenet_storage_optimizer_seed_2024_secure",
            port=8016,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @storage_optimizer_protocol.on_message(model=StorageOptimizeRequest)
        async def handle_optimize(ctx: Context, sender: str, msg: StorageOptimizeRequest):
            try:
                response = self.optimize(msg)
                await ctx.send(sender, response)
            except Exception as exc:
                await ctx.send(
                    sender,
                    StorageOptimizeResponse(success=False, message=f"Storage optimization failed: {exc}"),
                )

    def optimize(self, msg: StorageOptimizeRequest) -> StorageOptimizeResponse:
        nodes_removed = 0
        if msg.prune_soft_deleted:
            nodes = dag_store.list_nodes(msg.conversation_id, include_pruned=True)
            for node in nodes:
                if node.get("pruned"):
                    nodes_removed += dag_store.prune_node(node["node_id"], "hard")

        models_unloaded = 0
        if msg.unload_unused_models:
            for model in model_registry.list_models():
                if model.get("status") == "loaded" and model.get("name") != self.config.DEFAULT_LOCAL_MODEL:
                    ok, _ = model_registry.unload(model["name"])
                    if ok:
                        models_unloaded += 1

        # Conservative local estimate for demo purposes.
        estimated = nodes_removed * 0.01 + models_unloaded * 128.0
        return StorageOptimizeResponse(
            success=True,
            nodes_removed=nodes_removed,
            models_unloaded=models_unloaded,
            estimated_space_freed_mb=estimated,
            message="Storage optimization completed",
        )

    def run(self):
        self.agent.include(storage_optimizer_protocol)
        print("🧹 Tenet Storage Optimizer Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Storage Optimizer Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetStorageOptimizerAgent().run()
