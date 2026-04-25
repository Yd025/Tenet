from utils.local_dag_store import LocalDagStore
from utils.local_memory_store import LocalMemoryStore
from utils.local_model_registry import LocalModelRegistry
from utils.local_router import LocalRouter
from config.agent_config import AgentConfig


_config = AgentConfig()
dag_store = LocalDagStore()
memory_store = LocalMemoryStore()
model_registry = LocalModelRegistry()
router = LocalRouter(_config.SENSITIVE_KEYWORDS)

