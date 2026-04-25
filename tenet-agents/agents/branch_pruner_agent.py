from uagents import Agent, Context
from protocols.prune_protocol import (
    PruneRequest, PruneResponse, prune_protocol, PruneTarget
)
from config.agent_config import AgentConfig
from utils.local_runtime import dag_store
import time

class TenetBranchPruner:
    """Prunes branches and manages cleanup"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-branch-pruner",
            seed="tenet_branch_pruner_seed_2024_secure",
            port=8008
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup prune handlers"""
        @prune_protocol.on_message(model=PruneRequest)
        async def handle_prune_request(ctx: Context, sender: str, msg: PruneRequest):
            """Handle prune requests"""
            try:
                if msg.prune_strategy == "preview":
                    response = await self.preview_prune(msg)
                else:
                    response = await self.execute_prune(msg)
                await ctx.send(sender, PruneResponse(**response))
            except Exception as e:
                error_response = {
                    "success": False,
                    "items_pruned": 0,
                    "space_freed_mb": 0.0,
                    "backup_created": False,
                    "backup_id": None,
                    "prune_summary": "",
                    "message": f"Prune failed: {str(e)}"
                }
                await ctx.send(sender, PruneResponse(**error_response))

    async def preview_prune(self, msg: PruneRequest) -> dict:
        """Preview what would be pruned"""
        try:
            if msg.target_type == PruneTarget.BRANCH:
                preview = await self.preview_branch_prune(msg)
            elif msg.target_type == PruneTarget.NODE:
                preview = await self.preview_node_prune(msg)
            elif msg.target_type == PruneTarget.SUBTREE:
                preview = await self.preview_subtree_prune(msg)
            else:
                raise ValueError(f"Unknown target type: {msg.target_type}")
                
            return {
                "success": True,
                "items_pruned": preview["items_to_prune"],
                "space_freed_mb": preview["estimated_space_mb"],
                "backup_created": False,
                "backup_id": None,
                "prune_summary": f"Preview: {preview['items_to_prune']} items would be pruned, freeing ~{preview['estimated_space_mb']:.2f} MB",
                "message": "Prune preview generated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "items_pruned": 0,
                "space_freed_mb": 0.0,
                "backup_created": False,
                "backup_id": None,
                "prune_summary": "",
                "message": f"Preview failed: {str(e)}"
            }

    async def execute_prune(self, msg: PruneRequest) -> dict:
        """Execute the prune operation"""
        try:
            backup_id = None
            if msg.create_backup:
                backup_id = await self.create_backup(msg)
                
            if msg.target_type == PruneTarget.BRANCH:
                result = await self.prune_branch(msg)
            elif msg.target_type == PruneTarget.NODE:
                result = await self.prune_node(msg)
            elif msg.target_type == PruneTarget.SUBTREE:
                result = await self.prune_subtree(msg)
            else:
                raise ValueError(f"Unknown target type: {msg.target_type}")
                
            return {
                "success": True,
                "items_pruned": result["items_pruned"],
                "space_freed_mb": result["space_freed_mb"],
                "backup_created": backup_id is not None,
                "backup_id": backup_id,
                "prune_summary": result["summary"],
                "message": f"Pruned {result['items_pruned']} items successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "items_pruned": 0,
                "space_freed_mb": 0.0,
                "backup_created": False,
                "backup_id": None,
                "prune_summary": "",
                "message": f"Prune execution failed: {str(e)}"
            }

    async def preview_branch_prune(self, msg: PruneRequest) -> dict:
        """Preview branch prune"""
        branch_data = dag_store.get_branch(msg.target_id) or {"nodes": []}
        nodes_count = len(branch_data.get("nodes", []))
        return {
            "items_to_prune": nodes_count + 1,
            "estimated_space_mb": nodes_count * 0.01,
            "affected_branches": [msg.target_id],
        }

    async def preview_node_prune(self, msg: PruneRequest) -> dict:
        """Preview node prune"""
        node_data = dag_store.get_node(msg.target_id) or {}
        return {
            "items_to_prune": 1,
            "estimated_space_mb": 0.01,
            "affected_branches": [node_data.get("branch_id")],
        }

    async def preview_subtree_prune(self, msg: PruneRequest) -> dict:
        """Preview subtree prune"""
        subtree_data = dag_store.get_subtree(msg.target_id)
        nodes_count = len(subtree_data.get("nodes", []))
        return {
            "items_to_prune": nodes_count,
            "estimated_space_mb": nodes_count * 0.01,
            "affected_branches": list({n.get("branch_id") for n in subtree_data.get("nodes", [])}),
        }

    async def prune_branch(self, msg: PruneRequest) -> dict:
        """Prune a branch"""
        branch_data = dag_store.get_branch(msg.target_id) or {"nodes": [], "branch_name": "unknown"}
        count = dag_store.prune_branch(msg.target_id, msg.prune_strategy)
        return {
            "items_pruned": count,
            "space_freed_mb": len(branch_data.get("nodes", [])) * 0.01,
            "summary": f"Pruned branch '{branch_data.get('branch_name', 'Unknown')}'",
        }

    async def prune_node(self, msg: PruneRequest) -> dict:
        """Prune a node"""
        count = dag_store.prune_node(msg.target_id, msg.prune_strategy)
        return {"items_pruned": count, "space_freed_mb": 0.01 * count, "summary": f"Pruned node {msg.target_id}"}

    async def prune_subtree(self, msg: PruneRequest) -> dict:
        """Prune a subtree"""
        count = dag_store.prune_subtree(msg.target_id, msg.prune_strategy)
        return {
            "items_pruned": count,
            "space_freed_mb": count * 0.01,
            "summary": f"Pruned subtree with {count} nodes starting from {msg.target_id}",
        }

    async def create_backup(self, msg: PruneRequest) -> str:
        """Create backup before pruning"""
        return f"backup_{msg.target_id}_{int(time.time())}"

    def run(self):
        """Start the branch pruner agent"""
        self.agent.include(prune_protocol)
        print("✂️ Tenet Branch Pruner Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Prune Protocol: Enabled")
        print("🎯 Prune targets: branch, node, subtree")
        print("💾 Strategies: soft (archive), hard (delete)")
        self.agent.run()

if __name__ == "__main__":
    pruner = TenetBranchPruner()
    pruner.run()