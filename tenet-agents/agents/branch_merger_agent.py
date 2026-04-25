from uagents import Agent, Context
from protocols.merge_protocol import (
    MergeRequest, MergeResponse, MergeConflict, merge_protocol, MergeStrategy
)
from config.agent_config import AgentConfig
import uuid
from utils.local_runtime import dag_store

class TenetBranchMerger:
    """Merges branches intelligently"""
    
    def __init__(self):
        self.config = AgentConfig()
        self.agent = Agent(
            name="tenet-branch-merger",
            seed="tenet_branch_merger_seed_2024_secure",
            port=8007
        )
        self.setup_handlers()

    def setup_handlers(self):
        """Setup merge handlers"""
        @merge_protocol.on_message(model=MergeRequest)
        async def handle_merge_request(ctx: Context, sender: str, msg: MergeRequest):
            """Handle merge requests"""
            try:
                if msg.preview_only:
                    response = await self.preview_merge(msg)
                else:
                    response = await self.execute_merge(msg)
                await ctx.send(sender, MergeResponse(**response))
            except Exception as e:
                error_response = {
                    "success": False,
                    "merged_branch_id": None,
                    "conflicts": [],
                    "merge_summary": "",
                    "nodes_merged": 0,
                    "message": f"Merge failed: {str(e)}"
                }
                await ctx.send(sender, MergeResponse(**error_response))

    async def preview_merge(self, msg: MergeRequest) -> dict:
        """Preview merge without executing"""
        try:
            source_branch = await self.get_branch(msg.source_branch_id)
            target_branch = await self.get_branch(msg.target_branch_id)
            
            conflicts = await self.detect_conflicts(source_branch, target_branch)
            summary = self.generate_merge_preview_summary(source_branch, target_branch, conflicts)
            
            return {
                "success": True,
                "merged_branch_id": None,
                "conflicts": conflicts,
                "merge_summary": summary,
                "nodes_merged": len(source_branch.get("nodes", [])),
                "message": "Merge preview generated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "merged_branch_id": None,
                "conflicts": [],
                "merge_summary": "",
                "nodes_merged": 0,
                "message": f"Preview failed: {str(e)}"
            }

    async def execute_merge(self, msg: MergeRequest) -> dict:
        """Execute the merge operation"""
        try:
            source_branch = await self.get_branch(msg.source_branch_id)
            target_branch = await self.get_branch(msg.target_branch_id)
            
            conflicts = await self.detect_conflicts(source_branch, target_branch)
            
            resolved_nodes = await self.resolve_conflicts(
                source_branch, target_branch, conflicts, msg.merge_strategy, msg.conflict_resolution
            )
            
            merged_branch_id = await self.create_merged_branch(
                msg.conversation_id, source_branch, target_branch, resolved_nodes, msg.user_id
            )
            
            summary = self.generate_merge_summary(source_branch, target_branch, conflicts)
            
            return {
                "success": True,
                "merged_branch_id": merged_branch_id,
                "conflicts": conflicts,
                "merge_summary": summary,
                "nodes_merged": len(resolved_nodes),
                "message": f"Branches merged successfully into {merged_branch_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "merged_branch_id": None,
                "conflicts": [],
                "merge_summary": "",
                "nodes_merged": 0,
                "message": f"Merge execution failed: {str(e)}"
            }

    async def get_branch(self, branch_id: str) -> dict:
        """Get branch data from backend"""
        return dag_store.get_branch(branch_id) or {}

    async def detect_conflicts(self, source_branch: dict, target_branch: dict) -> list:
        """Detect conflicts between branches"""
        conflicts = []
        source_nodes = {node["node_id"]: node for node in source_branch.get("nodes", [])}
        target_nodes = {node["node_id"]: node for node in target_branch.get("nodes", [])}
        
        common_node_ids = set(source_nodes.keys()) & set(target_nodes.keys())
        
        for node_id in common_node_ids:
            source_node = source_nodes[node_id]
            target_node = target_nodes[node_id]
            
            if (source_node.get("prompt") != target_node.get("prompt") or
                source_node.get("response") != target_node.get("response")):
                conflicts.append(MergeConflict(
                    conflict_id=str(uuid.uuid4()),
                    node_id=node_id,
                    conflict_type="content_divergence",
                    source_content=f"Prompt: {source_node.get('prompt', '')}\nResponse: {source_node.get('response', '')}",
                    target_content=f"Prompt: {target_node.get('prompt', '')}\nResponse: {target_node.get('response', '')}",
                    suggested_resolution=self.suggest_conflict_resolution(source_node, target_node)
                ))
        return conflicts

    async def resolve_conflicts(self, source_branch: dict, target_branch: dict,
                               conflicts: list, strategy: MergeStrategy, resolution: str) -> list:
        """Resolve conflicts based on strategy"""
        source_nodes = {node["node_id"]: node for node in source_branch.get("nodes", [])}
        target_nodes = {node["node_id"]: node for node in target_branch.get("nodes", [])}
        resolved_nodes = list(target_nodes.values())
        
        for conflict in conflicts:
            if resolution == "keep_source":
                resolved_nodes.append(source_nodes[conflict.node_id])
            elif resolution == "keep_target":
                continue
            elif resolution == "keep_both":
                source_node = source_nodes[conflict.node_id].copy()
                source_node["node_id"] = str(uuid.uuid4())
                source_node["conflict_info"] = {"original_node_id": conflict.node_id, "source": "merge_conflict"}
                resolved_nodes.append(source_node)
            elif resolution == "merge_content":
                merged_node = await self.merge_node_content(
                    source_nodes[conflict.node_id], target_nodes[conflict.node_id]
                )
                resolved_nodes.append(merged_node)
                
        for node_id, node in source_nodes.items():
            if node_id not in [c.node_id for c in conflicts]:
                resolved_nodes.append(node)
                
        return resolved_nodes

    async def merge_node_content(self, source_node: dict, target_node: dict) -> dict:
        """Intelligently merge content from two nodes"""
        merged_node = target_node.copy()
        merged_node["response"] = (
            "Merged local-only response:\n"
            f"Target: {target_node.get('response', '')}\n"
            f"Source: {source_node.get('response', '')}"
        )
        merged_node["merge_info"] = {"merged_from": [source_node["node_id"], target_node["node_id"]]}
        return merged_node

    def suggest_conflict_resolution(self, source_node: dict, target_node: dict) -> str:
        """Suggest how to resolve a conflict"""
        source_len = len(source_node.get("response", ""))
        target_len = len(target_node.get("response", ""))
        
        if source_len > target_len * 1.5:
            return "Source response is significantly longer and more detailed"
        elif target_len > source_len * 1.5:
            return "Target response is significantly longer and more detailed"
        else:
            return "Responses are similar in length - manual review recommended"

    async def create_merged_branch(self, conversation_id: str, source_branch: dict, target_branch: dict,
                                  nodes: list, user_id: str) -> str:
        """Create the merged branch"""
        merged = dag_store.merge_branches(
            conversation_id=conversation_id,
            source_branch_id=source_branch.get("branch_id"),
            target_branch_id=target_branch.get("branch_id"),
        )
        return merged["branch_id"]

    def generate_merge_summary(self, source_branch: dict, target_branch: dict, conflicts: list) -> str:
        """Generate summary of merge operation"""
        source_name = source_branch.get("branch_name", "Unknown")
        target_name = target_branch.get("branch_name", "Unknown")
        source_nodes = len(source_branch.get("nodes", []))
        target_nodes = len(target_branch.get("nodes", []))
        
        summary = f"Merged '{source_name}' ({source_nodes} nodes) into '{target_name}' ({target_nodes} nodes). "
        if conflicts:
            summary += f"Found {len(conflicts)} conflict(s) during merge. "
        else:
            summary += "No conflicts found during merge. "
        summary += "Merge completed successfully."
        return summary

    def generate_merge_preview_summary(self, source_branch: dict, target_branch: dict, conflicts: list) -> str:
        """Generate preview summary"""
        source_name = source_branch.get("branch_name", "Unknown")
        target_name = target_branch.get("branch_name", "Unknown")
        
        summary = f"Preview: Merging '{source_name}' into '{target_name}'. "
        if conflicts:
            summary += f"⚠️ {len(conflicts)} conflict(s) detected that need resolution. "
        else:
            summary += "✅ No conflicts detected. "
        summary += "Ready to merge."
        return summary

    def run(self):
        """Start the branch merger agent"""
        self.agent.include(merge_protocol)
        print("🔀 Tenet Branch Merger Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Merge Protocol: Enabled")
        print("🎯 Merge strategies: auto, manual, semantic, chronological")
        self.agent.run()

if __name__ == "__main__":
    merger = TenetBranchMerger()
    merger.run()