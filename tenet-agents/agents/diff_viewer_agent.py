from difflib import unified_diff
from typing import List, Optional

from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.local_runtime import dag_store


class DiffRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation identifier")
    left_node_id: Optional[str] = Field(None, description="Left node for diff")
    right_node_id: Optional[str] = Field(None, description="Right node for diff")
    left_branch_id: Optional[str] = Field(None, description="Left branch if node IDs are not provided")
    right_branch_id: Optional[str] = Field(None, description="Right branch if node IDs are not provided")
    include_prompt: bool = Field(default=True, description="Include prompt text in diff")


class DiffResponse(BaseModel):
    success: bool
    diff_lines: List[str] = Field(default_factory=list)
    left_ref: str = ""
    right_ref: str = ""
    message: str


diff_protocol = Protocol("diff", version="1.0")


class TenetDiffViewerAgent:
    """Shows unified diffs between nodes or branch heads."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-diff-viewer",
            seed="tenet_diff_viewer_seed_2024_secure",
            port=8014,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @diff_protocol.on_message(model=DiffRequest)
        async def handle_diff(ctx: Context, sender: str, msg: DiffRequest):
            try:
                response = self.build_diff(msg)
                if not response.success:
                    await ctx.send(
                        sender,
                        response,
                    )
                    return
                await ctx.send(sender, response)
            except Exception as exc:
                await ctx.send(
                    sender,
                    DiffResponse(success=False, message=f"Diff generation failed: {exc}"),
                )

    def build_diff(self, msg: DiffRequest) -> DiffResponse:
        left_node, right_node, left_ref, right_ref = self._resolve_targets(msg)
        if not left_node or not right_node:
            return DiffResponse(success=False, message="Unable to resolve both diff targets")
        left_text = self._render_node(left_node, include_prompt=msg.include_prompt)
        right_text = self._render_node(right_node, include_prompt=msg.include_prompt)
        diff_lines = list(
            unified_diff(
                left_text.splitlines(),
                right_text.splitlines(),
                fromfile=left_ref,
                tofile=right_ref,
                lineterm="",
            )
        )
        return DiffResponse(
            success=True,
            diff_lines=diff_lines,
            left_ref=left_ref,
            right_ref=right_ref,
            message=f"Generated diff with {len(diff_lines)} line(s)",
        )

    def _resolve_targets(self, msg: DiffRequest):
        left_node = dag_store.get_node(msg.left_node_id) if msg.left_node_id else None
        right_node = dag_store.get_node(msg.right_node_id) if msg.right_node_id else None
        left_ref = msg.left_node_id or ""
        right_ref = msg.right_node_id or ""

        if not left_node and msg.left_branch_id:
            branch = dag_store.get_branch(msg.left_branch_id)
            if branch and branch.get("head_node_id"):
                left_node = dag_store.get_node(branch["head_node_id"])
                left_ref = f"branch:{msg.left_branch_id}"

        if not right_node and msg.right_branch_id:
            branch = dag_store.get_branch(msg.right_branch_id)
            if branch and branch.get("head_node_id"):
                right_node = dag_store.get_node(branch["head_node_id"])
                right_ref = f"branch:{msg.right_branch_id}"

        return left_node, right_node, left_ref, right_ref

    def _render_node(self, node: dict, include_prompt: bool) -> str:
        parts = []
        if include_prompt:
            parts.append(f"Prompt:\n{node.get('prompt', '')}")
        parts.append(f"Response:\n{node.get('response', '')}")
        metadata = node.get("metadata", {})
        if metadata:
            parts.append(f"Metadata:\n{metadata}")
        return "\n\n".join(parts)

    def run(self):
        self.agent.include(diff_protocol)
        print("🧾 Tenet Diff Viewer Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Diff Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetDiffViewerAgent().run()
