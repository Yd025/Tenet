# Core configuration for all Tenet agents
import os

class AgentConfig:
    """Central configuration for all Tenet agents"""
    
    # Agentverse Configuration
    AGENTVERSE_API_KEY = os.getenv("AGENTVERSE_API_KEY", "your_api_key_here")
    AGENTVERSE_URL = "https://agentverse.fetch.ai/api/v1"
    
    # Server Configuration
    BASE_HOST = "localhost"
    BASE_PORT = 8000
    
    # Agent Ports
    ORCHESTRATOR_PORT = 8001
    PRIVACY_ROUTER_PORT = 8002
    BRANCH_MANAGER_PORT = 8003
    MODEL_COORDINATOR_PORT = 8004
    CONTEXT_KEEPER_PORT = 8005
    
    # Local Hardware API (Person 2)
    HARDWARE_API_URL = os.getenv("HARDWARE_API_URL", "http://localhost:9000")
    
    # Backend API (Person 4)
    BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:5000")
    
    # Cloud API Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_key")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_key")
    
    # Agent Seed Phrases (In production, use proper secrets management)
    ORCHESTRATOR_SEED = "tenet_orchestrator_seed_2024_secure"
    PRIVACY_ROUTER_SEED = "tenet_privacy_router_seed_2024_secure"
    BRANCH_MANAGER_SEED = "tenet_branch_manager_seed_2024_secure"
    MODEL_COORDINATOR_SEED = "tenet_model_coordinator_seed_2024_secure"
    CONTEXT_KEEPER_SEED = "tenet_context_keeper_seed_2024_secure"
    
    # Privacy Configuration
    SENSITIVE_KEYWORDS = [
        "password", "ssn", "social security", "credit card", "medical",
        "confidential", "secret", "private key", "api key", "token",
        "bank account", "health record", "personal information"
    ]
    
    # Model Configuration
    DEFAULT_LOCAL_MODEL = "llama2-7b-4bit"
    DEFAULT_CLOUD_MODEL = "gpt-4"
    FALLBACK_MODEL = "gpt-3.5-turbo"
    
    # Performance Configuration
    DEFAULT_TIMEOUT = 30.0
    LOCAL_TIMEOUT = 45.0
    CLOUD_TIMEOUT = 30.0
    
    # Memory Configuration
    MAX_CONTEXT_LENGTH = 10000
    CONTEXT_RETENTION_DAYS = 30

# Agent Metadata for Agentverse Registration
AGENT_METADATA = {
    "orchestrator": {
        "name": "tenet-orchestrator",
        "description": "Main routing and coordination agent for Tenet AI conversation management",
        "capabilities": ["routing", "coordination", "multi-agent orchestration"],
        "protocols": ["chat", "branch", "storage", "memory"],
        "category": "orchestration"
    },
    "privacy_router": {
        "name": "tenet-privacy-router",
        "description": "Analyzes content and determines privacy routing for conversations",
        "capabilities": ["privacy_analysis", "content_classification", "secure_routing"],
        "protocols": ["chat"],
        "category": "security"
    },
    "branch_manager": {
        "name": "tenet-branch-manager",
        "description": "Manages conversation branching operations for Git-style AI workflows",
        "capabilities": ["branch_creation", "branch_management", "version_control"],
        "protocols": ["branch"],
        "category": "workflow"
    },
    "model_coordinator": {
        "name": "tenet-model-coordinator",
        "description": "Coordinates AI model loading and optimization on local hardware",
        "capabilities": ["model_management", "hardware_integration", "performance_optimization"],
        "protocols": ["storage"],
        "category": "infrastructure"
    },
    "context_keeper": {
        "name": "tenet-context-keeper",
        "description": "Maintains conversation context and memory across branches",
        "capabilities": ["context_management", "memory_retention", "conversation_history"],
        "protocols": ["memory"],
        "category": "memory"
    }
}
