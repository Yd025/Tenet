import time
from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig
from utils.local_runtime import model_registry


class ResourceStatusRequest(BaseModel):
    include_thermal: bool = Field(default=True, description="Include thermal estimate")


class ResourceStatusResponse(BaseModel):
    success: bool
    ram_usage_mb: float = 0.0
    vram_usage_mb: float = 0.0
    cpu_load_pct: float = 0.0
    thermal_celsius: float = 0.0
    loaded_models: int = 0
    alerts: list[str] = Field(default_factory=list)
    message: str


resource_monitor_protocol = Protocol("resource-monitor", version="1.0")


class TenetResourceMonitorAgent:
    """Provide local runtime resource estimates and thermal alerts."""

    def __init__(self):
        config = AgentConfig()
        self.agent = Agent(
            name="tenet-resource-monitor",
            seed="tenet_resource_monitor_seed_2024_secure",
            port=8017,
            mailbox=True,
            publish_agent_details=True,
        )
        self.config = config
        self.setup_handlers()

    def setup_handlers(self):
        @resource_monitor_protocol.on_message(model=ResourceStatusRequest)
        async def handle_status(ctx: Context, sender: str, msg: ResourceStatusRequest):
            try:
                await ctx.send(sender, self.get_status(msg.include_thermal))
            except Exception as exc:
                await ctx.send(
                    sender,
                    ResourceStatusResponse(success=False, message=f"Resource monitoring failed: {exc}"),
                )

    def get_status(self, include_thermal: bool = True) -> ResourceStatusResponse:
        models = model_registry.list_models()
        loaded = [m for m in models if m.get("status") == "loaded"]
        vram_usage = sum(float(m.get("hardware_requirements", {}).get("vram_gb", 0)) * 1024 for m in loaded)
        ram_usage = sum(float(m.get("hardware_requirements", {}).get("ram_gb", 0)) * 1024 for m in loaded)

        # Synthetic load/thermal estimate for local-only dev mode.
        cpu_load = min(95.0, 10.0 + len(loaded) * 12.5 + (time.time() % 5))
        thermal = 42.0 + len(loaded) * 6.0 if include_thermal else 0.0

        alerts: list[str] = []
        if vram_usage > 12 * 1024:
            alerts.append("VRAM pressure is high")
        if thermal > 78:
            alerts.append("Thermal threshold exceeded")

        return ResourceStatusResponse(
            success=True,
            ram_usage_mb=ram_usage,
            vram_usage_mb=vram_usage,
            cpu_load_pct=cpu_load,
            thermal_celsius=thermal,
            loaded_models=len(loaded),
            alerts=alerts,
            message="Resource snapshot generated",
        )

    def run(self):
        self.agent.include(resource_monitor_protocol)
        print("📊 Tenet Resource Monitor Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Resource Monitor Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetResourceMonitorAgent().run()
