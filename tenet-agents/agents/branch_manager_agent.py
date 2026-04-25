from uagents import Agent, Context
from protocols.branch_protocol import (
    BranchRequest, BranchResponse, branch_protocol, BranchAction
)
from config.agent_config import AgentConfig
from utils.local_runtime import dag_store

class TenetBranchManager:
    """Manages conversation branching operations"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the branch manager agent
        self.agent = Agent(
            name="tenet-branch-manager",
            seed=self.config.BRANCH_MANAGER_SEED,
            port=self.config.BRANCH_MANAGER_PORT,
            mailbox=True,
            publish_agent_details=True,
        )
        
        # Setup protocol handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup branch management handlers"""
        
        @branch_protocol.on_message(model=BranchRequest)
        async def handle_branch_request(ctx: Context, sender: str, msg: BranchRequest):
            """Handle branch operations"""
            
            try:
                if msg.action in {BranchAction.CREATE, BranchAction.FORK}:
                    response = await self.create_branch(msg)
                elif msg.action == BranchAction.DELETE:
                    response = await self.delete_branch(msg)
                elif msg.action == BranchAction.MERGE:
                    response = await self.merge_branches(msg)
                elif msg.action == BranchAction.SWITCH:
                    response = await self.switch_branch(msg)
                elif msg.action == BranchAction.LIST:
                    response = await self.list_branches(msg)
                elif msg.action == BranchAction.ROLLBACK:
                    response = await self.rollback_branch(msg)
                elif msg.action == BranchAction.GET_GRAPH:
                    response = await self.get_graph(msg)
                else:
                    response = {
                        "success": False,
                        "action": msg.action,
                        "new_branch_id": None,
                        "new_node_id": None,
                        "branches": None,
                        "graph": None,
                        "message": f"Unknown action: {msg.action}"
                    }
                
                await ctx.send(sender, BranchResponse(**response))
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "action": msg.action,
                    "new_branch_id": None,
                    "new_node_id": None,
                    "branches": None,
                    "graph": None,
                    "message": f"Branch operation failed: {str(e)}"
                }
                await ctx.send(sender, BranchResponse(**error_response))
    
    async def create_branch(self, msg: BranchRequest) -> dict:
        """Create a new conversation branch"""
        
        try:
            branch = dag_store.create_branch(msg.conversation_id, msg.node_id, msg.branch_name)
            return {
                "success": True,
                "action": BranchAction.CREATE,
                "new_branch_id": branch["branch_id"],
                "new_node_id": branch["head_node_id"],
                "branches": None,
                "graph": None,
                "message": f"Branch '{branch['branch_name']}' created"
            }
        except Exception as e:
            return {"success": False, "action": BranchAction.CREATE, "new_branch_id": None, "new_node_id": None, "branches": None, "graph": None, "message": str(e)}
    
    async def delete_branch(self, msg: BranchRequest) -> dict:
        """Delete a conversation branch"""
        
        try:
            success = dag_store.delete_branch(msg.conversation_id, msg.branch_id or "")
            return {
                "success": success,
                "action": BranchAction.DELETE,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "graph": None,
                "message": "Branch deleted successfully" if success else "Failed to delete branch"
            }
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.DELETE,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "graph": None,
                "message": f"Failed to delete branch: {str(e)}"
            }
    
    async def merge_branches(self, msg: BranchRequest) -> dict:
        """Merge two branches"""
        
        try:
            merged = dag_store.merge_branches(msg.conversation_id, msg.source_branch_id or "", msg.target_branch_id or "")
            return {
                "success": True,
                "action": BranchAction.MERGE,
                "new_branch_id": merged["branch_id"],
                "new_node_id": merged.get("head_node_id"),
                "branches": None,
                "graph": None,
                "message": "Branches merged successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.MERGE,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "graph": None,
                "message": f"Failed to merge branches: {str(e)}"
            }
    
    async def switch_branch(self, msg: BranchRequest) -> dict:
        """Switch to a different branch"""
        
        try:
            dag_store.switch_branch(msg.conversation_id, msg.branch_id or "")
            return {
                "success": True,
                "action": BranchAction.SWITCH,
                "new_branch_id": msg.branch_id,
                "new_node_id": None,
                "branches": None,
                "graph": None,
                "message": f"Switched to branch {msg.branch_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.SWITCH,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "graph": None,
                "message": f"Failed to switch branch: {str(e)}"
            }
    
    async def list_branches(self, msg: BranchRequest) -> dict:
        """List all branches for a conversation"""
        
        try:
            branches = dag_store.list_branches(msg.conversation_id, include_pruned=msg.include_pruned)
            return {
                "success": True,
                "action": BranchAction.LIST,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": branches,
                "graph": None,
                "message": f"Found {len(branches)} branches"
            }
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.LIST,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": [],
                "graph": None,
                "message": f"Failed to list branches: {str(e)}"
            }

    async def rollback_branch(self, msg: BranchRequest) -> dict:
        branch = dag_store.rollback(msg.conversation_id, msg.branch_id or "", msg.target_node_id or "")
        return {
            "success": True,
            "action": BranchAction.ROLLBACK,
            "new_branch_id": branch["branch_id"],
            "new_node_id": branch["head_node_id"],
            "branches": None,
            "graph": None,
            "message": "Rollback completed",
        }

    async def get_graph(self, msg: BranchRequest) -> dict:
        graph = dag_store.get_graph(msg.conversation_id, include_pruned=msg.include_pruned)
        return {
            "success": True,
            "action": BranchAction.GET_GRAPH,
            "new_branch_id": None,
            "new_node_id": None,
            "branches": None,
            "graph": graph,
            "message": "Graph fetched",
        }
    
    def run(self):
        """Start the branch manager agent"""
        self.agent.include(branch_protocol)
        print("🌳 Tenet Branch Manager Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Branch Protocol: Enabled")
        print("✅ Branch operations: create, delete, merge, switch, list")
        self.agent.run()

# Run the branch manager
if __name__ == "__main__":
    branch_manager = TenetBranchManager()
    branch_manager.run()
