"""
Resource Monitor Agent — merges GPU telemetry from the webapp's /telemetry
endpoint (pynvml) with Ollama model-load data for a unified resource snapshot.
"""
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field
from uagents import Agent, Context
from uagents.protocol import Protocol

from config.agent_config import AgentConfig

WEBAPP_API = os.getenv("WEBAPP_API_URL", "http://127.0.0.1:8000/api")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
_TIMEOUT = 10.0


class ResourceStatusRequest(BaseModel):
    include_thermal: bool = Field(default=True, description="Include thermal data")


class ResourceStatusResponse(BaseModel):
    success: bool
    # GPU (from webapp pynvml telemetry)
    temp_c: Optional[float] = None
    vram_gb: Optional[float] = None
    gpu_utilization_pct: Optional[float] = None
    gpu_clock_mhz: Optional[int] = None
    # System
    active_nodes: Optional[int] = None
    # Ollama
    loaded_models: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    message: str


resource_monitor_protocol = Protocol("resource-monitor", version="1.0")


def _fetch_webapp_telemetry() -> dict:
    try:
        r = httpx.get(f"{WEBAPP_API}/telemetry", timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _fetch_ollama_models() -> list[str]:
    """Return names of currently loaded Ollama models."""
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=_TIMEOUT)
        r.raise_for_status()
        models = r.json().get("models", [])
        return [m.get("name", "") for m in models if m.get("name")]
    except Exception:
        return []


class TenetResourceMonitorAgent:
    """Unified resource monitor: GPU telemetry + Ollama model state."""

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
        telemetry = _fetch_webapp_telemetry()
        loaded_models = _fetch_ollama_models()

        alerts: list[str] = []

        temp_c = telemetry.get("temp_c")
        vram_gb = telemetry.get("vram_gb")
        utilization = telemetry.get("utilization")
        gpu_clock_mhz = telemetry.get("gpu_clock_mhz")
        active_nodes = telemetry.get("active_nodes")

        if temp_c is not None and include_thermal and temp_c > 85:
            alerts.append(f"GPU temperature critical: {temp_c}°C")
        if vram_gb is not None and vram_gb > 20:
            alerts.append(f"VRAM usage high: {vram_gb} GB")
        if utilization is not None and utilization > 95:
            alerts.append(f"GPU utilization maxed: {utilization}%")

        return ResourceStatusResponse(
            success=True,
            temp_c=temp_c if include_thermal else None,
            vram_gb=vram_gb,
            gpu_utilization_pct=utilization,
            gpu_clock_mhz=gpu_clock_mhz,
            active_nodes=active_nodes,
            loaded_models=loaded_models,
            alerts=alerts,
            message="Resource snapshot from webapp telemetry + Ollama",
        )

    def run(self):
        self.agent.include(resource_monitor_protocol)
        print("📊 Tenet Resource Monitor Agent starting (webapp-backed)...")
        print(f"📍 Agent Address: {self.agent.address}")
        print("🔗 Resource Monitor Protocol: Enabled")
        self.agent.run()


if __name__ == "__main__":
    TenetResourceMonitorAgent().run()
