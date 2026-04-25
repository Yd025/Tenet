from typing import Dict, List, Optional


class CapabilityRegistry:
    """In-memory registry mapping capabilities to agents."""

    def __init__(self):
        self._agents: Dict[str, Dict] = {}

    def register_agent(self, agent_name: str, capabilities: List[str], protocols: Optional[List[str]] = None):
        self._agents[agent_name] = {
            "agent_name": agent_name,
            "capabilities": list(capabilities),
            "protocols": list(protocols or []),
        }

    def list_agents(self) -> List[Dict]:
        return list(self._agents.values())

    def find_best_agent(self, required_capability: str) -> Optional[Dict]:
        for agent in self._agents.values():
            if required_capability in agent["capabilities"]:
                return agent
        return None

