from typing import List, Optional

from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.local_runtime import capability_registry


class CapabilityRegistryRequest(BaseModel):
    action: str = Field(..., description="register, list, resolve")
    agent_name: Optional[str] = Field(None, description="Agent name for register")
    capabilities: List[str] = Field(default_factory=list, description="Capabilities for register")
    protocols: List[str] = Field(default_factory=list, description="Protocols for register")
    required_capability: Optional[str] = Field(None, description="Capability for resolve")


class CapabilityRegistryResponse(BaseModel):
    success: bool
    action: str
    agents: List[dict] = Field(default_factory=list)
    resolved_agent: Optional[dict] = None
    message: str


capability_registry_protocol = Protocol("capability-registry", version="1.0")


class TenetCapabilityRegistryAgent:
    """Central capability registry for orchestration-aware routing."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-capability-registry",
            seed="tenet_capability_registry_seed_2024_secure",
            port=8019,
            mailbox=True,
            publish_agent_details=True,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @capability_registry_protocol.on_message(model=CapabilityRegistryRequest)
        async def handle_registry(ctx: Context, sender: str, msg: CapabilityRegistryRequest):
            try:
                if msg.action == "register":
                    if not msg.agent_name:
                        await ctx.send(
                            sender,
                            CapabilityRegistryResponse(
                                success=False,
                                action=msg.action,
                                message="agent_name is required for register",
                            ),
                        )
                        return
                    capability_registry.register_agent(msg.agent_name, msg.capabilities, msg.protocols)
                    await ctx.send(
                        sender,
                        CapabilityRegistryResponse(
                            success=True,
                            action=msg.action,
                            agents=capability_registry.list_agents(),
                            message=f"Registered {msg.agent_name}",
                        ),
                    )
                elif msg.action == "list":
                    await ctx.send(
                        sender,
                        CapabilityRegistryResponse(
                            success=True,
                            action=msg.action,
                            agents=capability_registry.list_agents(),
                            message="Listed registry agents",
                        ),
                    )
                elif msg.action == "resolve":
                    resolved = capability_registry.find_best_agent(msg.required_capability or "")
                    await ctx.send(
                        sender,
                        CapabilityRegistryResponse(
                            success=resolved is not None,
                            action=msg.action,
                            resolved_agent=resolved,
                            message="Resolved capability" if resolved else "No matching agent",
                        ),
                    )
                else:
                    await ctx.send(
                        sender,
                        CapabilityRegistryResponse(
                            success=False,
                            action=msg.action,
                            message=f"Unknown action: {msg.action}",
                        ),
                    )
            except Exception as exc:
                await ctx.send(
                    sender,
                    CapabilityRegistryResponse(
                        success=False,
                        action=msg.action,
                        message=f"Capability registry failed: {exc}",
                    ),
                )

    def run(self):
        self.agent.include(capability_registry_protocol)
        print("🗂️ Tenet Capability Registry Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Capability Registry Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetCapabilityRegistryAgent().run()
