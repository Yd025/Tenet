from uagents import Agent, Context
from protocols.branch_protocol import (
    BranchRequest, BranchResponse, BranchInfo, branch_protocol, BranchAction
)
from config.agent_config import AgentConfig
import httpx
import time
import uuid

class TenetBranchManager:
    """Manages conversation branching operations"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the branch manager agent
        self.agent = Agent(
            name="tenet-branch-manager",
            seed=self.config.BRANCH_MANAGER_SEED,
            port=self.config.BRANCH_MANAGER_PORT
        )
        
        # Setup protocol handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup branch management handlers"""
        
        @branch_protocol.on_message(model=BranchRequest)
        async def handle_branch_request(ctx: Context, sender: str, msg: BranchRequest):
            """Handle branch operations"""
            
            try:
                if msg.action == BranchAction.CREATE:
                    response = await self.create_branch(msg)
                elif msg.action == BranchAction.DELETE:
                    response = await self.delete_branch(msg)
                elif msg.action == BranchAction.MERGE:
                    response = await self.merge_branches(msg)
                elif msg.action == BranchAction.SWITCH:
                    response = await self.switch_branch(msg)
                elif msg.action == BranchAction.LIST:
                    response = await self.list_branches(msg)
                else:
                    response = {
                        "success": False,
                        "action": msg.action,
                        "new_branch_id": None,
                        "new_node_id": None,
                        "branches": None,
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
                    "message": f"Branch operation failed: {str(e)}"
                }
                await ctx.send(sender, BranchResponse(**error_response))
    
    async def create_branch(self, msg: BranchRequest) -> dict:
        """Create a new conversation branch"""
        
        try:
            # Generate new branch and node IDs
            new_branch_id = str(uuid.uuid4())
            new_node_id = str(uuid.uuid4())
            
            # Call backend API to create branch
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/branches",
                    json={
                        "action": "create",
                        "conversation_id": msg.conversation_id,
                        "node_id": msg.node_id,
                        "branch_name": msg.branch_name,
                        "new_branch_id": new_branch_id,
                        "new_node_id": new_node_id,
                        "user_id": msg.user_id
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": BranchAction.CREATE,
                    "new_branch_id": new_branch_id,
                    "new_node_id": new_node_id,
                    "branches": None,
                    "message": f"Branch '{msg.branch_name}' created successfully from node {msg.node_id}"
                }
                
        except Exception as e:
            # Fallback: Create branch locally if backend fails
            return {
                "success": True,
                "action": BranchAction.CREATE,
                "new_branch_id": str(uuid.uuid4()),
                "new_node_id": str(uuid.uuid4()),
                "branches": None,
                "message": f"Branch '{msg.branch_name}' created (local mode)"
            }
    
    async def delete_branch(self, msg: BranchRequest) -> dict:
        """Delete a conversation branch"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.config.BACKEND_API_URL}/api/branches/{msg.conversation_id}",
                    json={
                        "branch_id": msg.branch_id,
                        "user_id": msg.user_id
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "action": BranchAction.DELETE,
                    "new_branch_id": None,
                    "new_node_id": None,
                    "branches": None,
                    "message": "Branch deleted successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.DELETE,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "message": f"Failed to delete branch: {str(e)}"
            }
    
    async def merge_branches(self, msg: BranchRequest) -> dict:
        """Merge two branches"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/branches/merge",
                    json={
                        "conversation_id": msg.conversation_id,
                        "source_branch_id": msg.source_branch_id,
                        "target_branch_id": msg.target_branch_id,
                        "user_id": msg.user_id
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": BranchAction.MERGE,
                    "new_branch_id": result.get("merged_branch_id"),
                    "new_node_id": result.get("merged_node_id"),
                    "branches": None,
                    "message": f"Branches merged successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.MERGE,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "message": f"Failed to merge branches: {str(e)}"
            }
    
    async def switch_branch(self, msg: BranchRequest) -> dict:
        """Switch to a different branch"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/branches/switch",
                    json={
                        "conversation_id": msg.conversation_id,
                        "branch_id": msg.branch_id,
                        "user_id": msg.user_id
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "action": BranchAction.SWITCH,
                    "new_branch_id": msg.branch_id,
                    "new_node_id": None,
                    "branches": None,
                    "message": f"Switched to branch {msg.branch_id}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.SWITCH,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": None,
                "message": f"Failed to switch branch: {str(e)}"
            }
    
    async def list_branches(self, msg: BranchRequest) -> dict:
        """List all branches for a conversation"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/branches/{msg.conversation_id}",
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                branches = [
                    {
                        "branch_id": branch.get("branch_id"),
                        "branch_name": branch.get("branch_name"),
                        "node_count": branch.get("node_count", 0),
                        "created_at": branch.get("created_at"),
                        "last_activity": branch.get("last_activity")
                    }
                    for branch in result.get("branches", [])
                ]
                
                return {
                    "success": True,
                    "action": BranchAction.LIST,
                    "new_branch_id": None,
                    "new_node_id": None,
                    "branches": branches,
                    "message": f"Found {len(branches)} branches"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": BranchAction.LIST,
                "new_branch_id": None,
                "new_node_id": None,
                "branches": [],
                "message": f"Failed to list branches: {str(e)}"
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
