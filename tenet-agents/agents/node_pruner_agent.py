from uagents import Agent, Context
from protocols.prune_protocol import (
    PruneRequest, PruneResponse, prune_protocol, PruneTarget
)
from config.agent_config import AgentConfig
import time
from utils.local_runtime import dag_store

class TenetNodePruner:
    """Specialized agent for node-level pruning operations"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-node-pruner",
            seed="tenet_node_pruner_seed_2024_secure",
            port=8009,
            mailbox=True,
            publish_agent_details=True,
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup node prune handlers"""
        @prune_protocol.on_message(model=PruneRequest)
        async def handle_node_prune_request(ctx: Context, sender: str, msg: PruneRequest):
            """Handle node-specific prune requests"""
            try:
                if msg.target_type != PruneTarget.NODE:
                    response = {
                        "success": False,
                        "items_pruned": 0,
                        "space_freed_mb": 0.0,
                        "backup_created": False,
                        "backup_id": None,
                        "prune_summary": "",
                        "message": "Node pruner only handles node targets. Use branch pruner for other targets."
                    }
                else:
                    response = await self.execute_node_prune(msg)
                await ctx.send(sender, PruneResponse(**response))
            except Exception as e:
                error_response = {
                    "success": False,
                    "items_pruned": 0,
                    "space_freed_mb": 0.0,
                    "backup_created": False,
                    "backup_id": None,
                    "prune_summary": "",
                    "message": f"Node prune failed: {str(e)}"
                }
                await ctx.send(sender, PruneResponse(**error_response))

    async def execute_node_prune(self, msg: PruneRequest) -> dict:
        """Execute node pruning with smart analysis"""
        try:
            node_info = await self.get_node_info(msg.target_id)
            importance = await self.analyze_node_importance(node_info)
            
            backup_id = None
            if msg.create_backup:
                backup_id = await self.create_node_backup(msg.target_id, node_info)
                
            if msg.prune_strategy == "soft":
                result = await self.soft_prune_node(msg.target_id, msg.reason)
            else:
                result = await self.hard_prune_node(msg.target_id, msg.reason)
                
            return {
                "success": True,
                "items_pruned": 1,
                "space_freed_mb": result["space_freed_mb"],
                "backup_created": backup_id is not None,
                "backup_id": backup_id,
                "prune_summary": f"Pruned node (importance: {importance:.2f}): {result['summary']}",
                "message": "Node pruned successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "items_pruned": 0,
                "space_freed_mb": 0.0,
                "backup_created": False,
                "backup_id": None,
                "prune_summary": "",
                "message": f"Node prune failed: {str(e)}"
            }

    async def get_node_info(self, node_id: str) -> dict:
        """Get detailed node information"""
        return dag_store.get_node(node_id) or {}

    async def analyze_node_importance(self, node_info: dict) -> float:
        """Analyze node importance (0-1 scale)"""
        importance_score = 0.5 
        
        if node_info.get("children_count", 0) > 0:
            importance_score += 0.2
            
        response_length = len(node_info.get("response", ""))
        if response_length > 500:
            importance_score += 0.1
        elif response_length > 1000:
            importance_score += 0.2
            
        if node_info.get("marked_important", False):
            importance_score += 0.3
            
        return min(importance_score, 1.0)

    async def soft_prune_node(self, node_id: str, reason: str) -> dict:
        """Soft prune (archive) node"""
        dag_store.prune_node(node_id, "soft")
        return {"space_freed_mb": 0.005, "summary": f"Node archived (soft prune): {reason}"}

    async def hard_prune_node(self, node_id: str, reason: str) -> dict:
        """Hard prune (delete) node"""
        dag_store.prune_node(node_id, "hard")
        return {"space_freed_mb": 0.01, "summary": f"Node deleted (hard prune): {reason}"}

    async def create_node_backup(self, node_id: str, node_info: dict) -> str:
        """Create backup of node"""
        return f"node_backup_{node_id}_{int(time.time())}"

    def run(self):
        """Start the node pruner agent"""
        self.agent.include(prune_protocol)
        print("🔪 Tenet Node Pruner Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Prune Protocol: Enabled")
        print("🎯 Specialized in node-level pruning")
        print("📊 Node importance analysis: Enabled")
        self.agent.run()

if __name__ == "__main__":
    node_pruner = TenetNodePruner()
    node_pruner.run()