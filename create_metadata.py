# create_metadata.py
import json

AGENT_METADATA = {
    "name": "tenet-gateway",
    "description": "Gateway agent for Tenet AI conversation management system. Provides unified API access to 19 specialized AI agents including orchestrator, privacy router, branch manager, semantic search, branch merging, conversation summarization, and more. Enables Git-style version control for AI conversations with multi-agent orchestration.",
    "capabilities": [
        "multi-agent orchestration",
        "conversation branching",
        "privacy routing",
        "semantic search",
        "branch merging",
        "conversation summarization",
        "model coordination",
        "context management",
        "node pruning",
        "conversation export",
        "tag management",
        "rollback capabilities",
        "diff viewing",
        "branch comparison",
        "storage optimization",
        "resource monitoring",
        "graph integrity",
        "capability registry",
        "Git-for-AI workflows"
    ],
    "protocols": ["gateway"],
    "category": "orchestration",
    "tags": [
        "AI",
        "conversation",
        "branching",
        "privacy",
        "multi-agent",
        "Git-for-AI",
        "version-control",
        "orchestration",
        "semantic-search",
        "conversation-management"
    ],
    "endpoints": {
        "health": "/health",
        "process": "/process",
        "submit": "/submit"
    },
    "supported_request_types": [
        "chat",
        "branch",
        "search",
        "orchestrator",
        "privacy_router",
        "branch_manager",
        "model_coordinator",
        "context_keeper",
        "branch_summarizer",
        "branch_merger",
        "branch_pruner",
        "node_pruner",
        "semantic_search",
        "conversation_exporter",
        "tag_manager",
        "rollback_agent",
        "diff_viewer",
        "branch_comparator",
        "storage_optimizer",
        "resource_monitor",
        "graph_integrity",
        "capability_registry"
    ],
    "pricing": {
        "free_tier": True,
        "paid_tier": False
    },
    "version": "1.0.0",
    "author": "Adelin Ma",
    "total_agents": 19,
    "architecture": "Gateway-to-Local pattern with 19 specialized agents"
}

# Save as JSON
with open('agent_metadata.json', 'w') as f:
    json.dump(AGENT_METADATA, f, indent=2)

print("✅ Metadata saved to agent_metadata.json")
print(f"\n📋 Agent Details:")
print(f"   Name: {AGENT_METADATA['name']}")
print(f"   Category: {AGENT_METADATA['category']}")
print(f"   Capabilities: {len(AGENT_METADATA['capabilities'])}")
print(f"   Tags: {len(AGENT_METADATA['tags'])}")
print(f"   Supported Request Types: {len(AGENT_METADATA['supported_request_types'])}")
print(f"   Total Agents: {AGENT_METADATA['total_agents']}")
