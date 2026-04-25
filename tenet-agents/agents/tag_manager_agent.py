from uagents import Agent, Context
from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import List, Optional

from config.agent_config import AgentConfig
from utils.local_runtime import dag_store


class TagAction(str):
    ADD = "add"
    REMOVE = "remove"
    LIST = "list"
    FILTER = "filter"


class TagRequest(BaseModel):
    action: str = Field(..., description="add, remove, list, filter")
    conversation_id: str = Field(..., description="Conversation identifier")
    node_id: Optional[str] = Field(None, description="Node for add/remove/list")
    tags: List[str] = Field(default_factory=list, description="Tags to add/remove/filter")
    branch_id: Optional[str] = Field(None, description="Optional branch filter")
    user_id: Optional[str] = Field(None, description="User identifier")


class TagResponse(BaseModel):
    success: bool
    action: str
    node_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    matched_nodes: List[dict] = Field(default_factory=list)
    message: str


tag_protocol = Protocol("tag", version="1.0")


class TenetTagManager:
    """Manage tags on local DAG nodes."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-tag-manager",
            seed="tenet_tag_manager_seed_2024_secure",
            port=8012,
            mailbox=True,
            publish_agent_details=True,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @tag_protocol.on_message(model=TagRequest)
        async def handle_tag_request(ctx: Context, sender: str, msg: TagRequest):
            try:
                if msg.action == TagAction.ADD:
                    response = self.add_tags(msg)
                elif msg.action == TagAction.REMOVE:
                    response = self.remove_tags(msg)
                elif msg.action == TagAction.LIST:
                    response = self.list_tags(msg)
                elif msg.action == TagAction.FILTER:
                    response = self.filter_nodes(msg)
                else:
                    response = TagResponse(
                        success=False,
                        action=msg.action,
                        message=f"Unknown tag action: {msg.action}",
                    )
                await ctx.send(sender, response)
            except Exception as exc:
                await ctx.send(
                    sender,
                    TagResponse(
                        success=False,
                        action=msg.action,
                        message=f"Tag manager failed: {exc}",
                    ),
                )

    def _get_node_tags(self, node: dict) -> List[str]:
        metadata = node.get("metadata", {})
        return list(metadata.get("tags", []))

    def add_tags(self, msg: TagRequest) -> TagResponse:
        node = dag_store.get_node(msg.node_id or "")
        if not node:
            return TagResponse(success=False, action=msg.action, message="Node not found")
        existing = set(self._get_node_tags(node))
        existing.update(t.strip() for t in msg.tags if t.strip())
        updated = dag_store.update_node_metadata(msg.node_id or "", {"tags": sorted(existing)})
        return TagResponse(
            success=True,
            action=msg.action,
            node_id=msg.node_id,
            tags=updated.get("metadata", {}).get("tags", []) if updated else sorted(existing),
            message=f"Added {len(msg.tags)} tag(s)",
        )

    def remove_tags(self, msg: TagRequest) -> TagResponse:
        node = dag_store.get_node(msg.node_id or "")
        if not node:
            return TagResponse(success=False, action=msg.action, message="Node not found")
        existing = set(self._get_node_tags(node))
        to_remove = {t.strip() for t in msg.tags if t.strip()}
        remaining = sorted(existing - to_remove)
        updated = dag_store.update_node_metadata(msg.node_id or "", {"tags": remaining})
        return TagResponse(
            success=True,
            action=msg.action,
            node_id=msg.node_id,
            tags=updated.get("metadata", {}).get("tags", []) if updated else remaining,
            message=f"Removed {len(to_remove)} tag(s)",
        )

    def list_tags(self, msg: TagRequest) -> TagResponse:
        node = dag_store.get_node(msg.node_id or "")
        if not node:
            return TagResponse(success=False, action=msg.action, message="Node not found")
        tags = self._get_node_tags(node)
        return TagResponse(
            success=True,
            action=msg.action,
            node_id=msg.node_id,
            tags=tags,
            message=f"Found {len(tags)} tag(s)",
        )

    def filter_nodes(self, msg: TagRequest) -> TagResponse:
        desired = {t.strip() for t in msg.tags if t.strip()}
        nodes = dag_store.list_nodes(msg.conversation_id, msg.branch_id)
        matched = []
        for node in nodes:
            tags = set(self._get_node_tags(node))
            if desired.issubset(tags):
                matched.append(
                    {
                        "node_id": node["node_id"],
                        "branch_id": node.get("branch_id"),
                        "tags": sorted(tags),
                        "prompt": node.get("prompt", ""),
                    }
                )
        return TagResponse(
            success=True,
            action=msg.action,
            matched_nodes=matched,
            tags=sorted(desired),
            message=f"Matched {len(matched)} node(s)",
        )

    def run(self):
        self.agent.include(tag_protocol)
        print("🏷️ Tenet Tag Manager Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Tag Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetTagManager().run()
