from utils.local_dag_store import LocalDagStore
from utils.local_memory_store import LocalMemoryStore
from utils.local_model_registry import LocalModelRegistry
from utils.local_router import LocalRouter
from utils.capability_registry import CapabilityRegistry
from config.agent_config import AgentConfig


_config = AgentConfig()
dag_store = LocalDagStore()
memory_store = LocalMemoryStore()
model_registry = LocalModelRegistry()
router = LocalRouter(_config.SENSITIVE_KEYWORDS)
capability_registry = CapabilityRegistry()

# Seed default capabilities for local orchestration routing.
capability_registry.register_agent(
    "tenet-privacy-router",
    capabilities=["privacy_analysis", "secure_routing"],
    protocols=["chat"],
)
capability_registry.register_agent(
    "tenet-branch-manager",
    capabilities=["branch_creation", "branch_management", "rollback"],
    protocols=["branch"],
)
capability_registry.register_agent(
    "tenet-model-coordinator",
    capabilities=["model_management", "resource_optimization"],
    protocols=["storage"],
)
capability_registry.register_agent(
    "tenet-context-keeper",
    capabilities=["context_management", "memory_retention", "semantic_retrieval"],
    protocols=["memory"],
)
capability_registry.register_agent(
    "tenet-semantic-search",
    capabilities=["semantic_search", "keyword_search"],
    protocols=["search"],
)

