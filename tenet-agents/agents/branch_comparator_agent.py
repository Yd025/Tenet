from typing import List

from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.local_runtime import dag_store


class BranchCompareRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation identifier")
    left_branch_id: str = Field(..., description="First branch")
    right_branch_id: str = Field(..., description="Second branch")


class BranchCompareResponse(BaseModel):
    success: bool
    shared_node_ids: List[str] = Field(default_factory=list)
    left_only_node_ids: List[str] = Field(default_factory=list)
    right_only_node_ids: List[str] = Field(default_factory=list)
    similarity_score: float = 0.0
    summary: str = ""
    message: str


compare_protocol = Protocol("branch-compare", version="1.0")


class TenetBranchComparatorAgent:
    """Compare two branches by overlapping DAG nodes/content."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-branch-comparator",
            seed="tenet_branch_comparator_seed_2024_secure",
            port=8015,
            mailbox=True,
            publish_agent_details=True,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @compare_protocol.on_message(model=BranchCompareRequest)
        async def handle_compare(ctx: Context, sender: str, msg: BranchCompareRequest):
            try:
                await ctx.send(sender, self.compare_branches(msg.left_branch_id, msg.right_branch_id))
            except Exception as exc:
                await ctx.send(
                    sender,
                    BranchCompareResponse(
                        success=False,
                        message=f"Comparison failed: {exc}",
                    ),
                )

    def compare_branches(self, left_branch_id: str, right_branch_id: str) -> BranchCompareResponse:
        left = dag_store.get_branch(left_branch_id)
        right = dag_store.get_branch(right_branch_id)
        if not left or not right:
            return BranchCompareResponse(success=False, message="One or both branches not found")

        left_nodes = {n["node_id"] for n in left.get("nodes", [])}
        right_nodes = {n["node_id"] for n in right.get("nodes", [])}
        shared = sorted(left_nodes & right_nodes)
        left_only = sorted(left_nodes - right_nodes)
        right_only = sorted(right_nodes - left_nodes)
        total_union = len(left_nodes | right_nodes)
        similarity = (len(shared) / total_union) if total_union else 1.0

        summary = (
            f"Shared: {len(shared)}, left-only: {len(left_only)}, "
            f"right-only: {len(right_only)}, similarity: {similarity:.2f}"
        )
        return BranchCompareResponse(
            success=True,
            shared_node_ids=shared,
            left_only_node_ids=left_only,
            right_only_node_ids=right_only,
            similarity_score=similarity,
            summary=summary,
            message="Branch comparison completed",
        )

    def run(self):
        self.agent.include(compare_protocol)
        print("🧮 Tenet Branch Comparator Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Branch Compare Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetBranchComparatorAgent().run()
