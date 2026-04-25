from uagents import Agent, Context

from config.agent_config import AgentConfig
from protocols.branch_protocol import BranchAction, BranchRequest, BranchResponse, branch_protocol
from utils.local_runtime import dag_store


class TenetRollbackAgent:
    """Specialized rollback agent for branch head rewinds."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-rollback-agent",
            seed="tenet_rollback_seed_2024_secure",
            port=8013,
            mailbox=True,
            publish_agent_details=True,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @branch_protocol.on_message(model=BranchRequest)
        async def handle_rollback(ctx: Context, sender: str, msg: BranchRequest):
            if msg.action != BranchAction.ROLLBACK:
                await ctx.send(
                    sender,
                    BranchResponse(
                        success=False,
                        action=msg.action,
                        new_branch_id=None,
                        new_node_id=None,
                        branches=None,
                        graph=None,
                        message="Rollback agent only handles rollback action",
                    ),
                )
                return

            try:
                branch = self.execute_rollback(msg.conversation_id, msg.branch_id or "", msg.target_node_id or "")
                await ctx.send(
                    sender,
                    BranchResponse(
                        success=True,
                        action=BranchAction.ROLLBACK,
                        new_branch_id=branch["branch_id"],
                        new_node_id=branch["head_node_id"],
                        branches=None,
                        graph=dag_store.get_graph(msg.conversation_id, include_pruned=msg.include_pruned),
                        message=f"Rolled back branch {branch['branch_id']} to node {branch['head_node_id']}",
                    ),
                )
            except Exception as exc:
                await ctx.send(
                    sender,
                    BranchResponse(
                        success=False,
                        action=BranchAction.ROLLBACK,
                        new_branch_id=msg.branch_id,
                        new_node_id=msg.target_node_id,
                        branches=None,
                        graph=None,
                        message=f"Rollback failed: {exc}",
                    ),
                )

    def execute_rollback(self, conversation_id: str, branch_id: str, target_node_id: str) -> dict:
        return dag_store.rollback(
            conversation_id=conversation_id,
            branch_id=branch_id,
            target_node_id=target_node_id,
        )

    def run(self):
        self.agent.include(branch_protocol)
        print("⏪ Tenet Rollback Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Branch Protocol: Rollback action enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetRollbackAgent().run()
