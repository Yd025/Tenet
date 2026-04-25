# Tenet: Git for AI

## Project Overview

**Tenet** is a version-controlled, multi-agent orchestration layer that eliminates conversational toil by allowing users to branch, prune, and optimally route AI context. Inspired by Christopher Nolan's film about time inversion, Tenet treats AI conversations not as linear threads but as Directed Acyclic Graphs (DAGs), enabling users to safely explore ideas, fork prompts, and rollback mistakes without losing foundational context.

## Core Philosophy

Current AI interactions are strictly linear. If a conversation goes off the rails or a model hallucinates, users are forced into the frustrating, repetitive toil of copying and pasting context into a brand-new chat. Professional AI users need the same paradigm that software engineers have relied on for decades: version control. Tenet treats conversations as a branching tree, allowing safe exploration, forking, and rollback.

## Key Features

### 1. Branch & Prune

* **Fork conversations** at any exact node to try different prompts
* **Prune useless branches** to keep context windows clean
* **Rollback to any previous state** without losing progress
* **Visual tree interface** for managing conversation branches

### 2. Smart Dispatch

* **Multi-agent orchestration** assigns specific branches to specific models
* **Intelligent routing** evaluates prompt requirements and dispatches to the most capable specialized agent
* **Local vs Cloud routing** automatically chooses between on-device models and external APIs
* **Resource optimization** matches task complexity with appropriate compute

### 3. Secure Local Execution

* **Privacy-first design** routes sensitive branches to local, on-device models
* **Ultra-low latency** for private conversation branches
* **Hybrid execution** - local for sensitive data, cloud for heavy lifting
* **Full data control** - nothing leaves your hardware unless you want it to

## Hardware Infrastructure

### ASUS Ascent GX10 Supercomputer

Tenet is designed to leverage powerful local hardware for private, low-latency AI inference. The system is optimized for deployment on the ASUS Ascent GX10 AI supercomputer, which provides:

* **High-performance computing** for running multiple quantized LLMs simultaneously
* **Ample storage** for housing large model files and conversation history
* **Advanced thermal management** for sustained inference workloads
* **Enterprise-grade reliability** for continuous operation

### Local Inference Capabilities

The hardware enables:

* **Multiple model loading** - Run several models concurrently and switch between them instantly
* **Quantized model execution** - Efficient inference with compressed models (Q4, Q8 precision)
* **Low-latency responses** - Sub-second response times for local models
* **Privacy-preserving computation** - Sensitive data never leaves the device

### Hardware Advantages

* **No network dependency** for core functionality
* **Consistent performance** without cloud API rate limits or downtime
* **Data sovereignty** - Complete control over conversation data
* **Cost efficiency** - No recurring API costs for local inference

## Technical Architecture

### Local-Only Implementation Status

The current `tenet-agents` implementation now supports a local-only runtime mode for end-to-end development without external FastAPI dependencies.

- Internal agent flows are executed via shared in-memory services instead of HTTP calls.
- DAG operations (branch, rollback, prune, merge) are available through local stores.
- Context memory, model registry simulation, semantic search, summarization, and export are wired to local services.
- A smoke test suite is available at `tenet-agents/tests/test_local_smoke.py` to validate core flows.
- Cloud/off-device execution can be reintroduced later as an optional deployment mode.

### Graph Architecture

* **MongoDB Atlas** for storing conversation history as a graph of nodes
* **Parent-child relationships** using `parent_id` and `children_ids` arrays
* **Optimized query structure** for instant rendering of massive conversation trees
* **DAG structure** prevents circular dependencies while enabling branching

### Agentic Routing

* **Fetch.ai & Cognition integration** for intelligent routing layer
* **Orchestration agent** evaluates prompt requirements and dispatches appropriately
* **Specialized agent selection** - local models vs external cloud APIs
* **Seamless switching** between different AI models without manual intervention

### Storage & Memory Management (Tenet System)

* **Model Registry** - Track downloaded models with metadata (size, quantization, hardware requirements)
* **Storage Optimization** - Compression, deduplication, and automated cleanup
* **Cache Management** - Prioritize frequently used models
* **Memory Orchestration** - OpenClaw integration for conversation context
* **Vector Store** - Semantic search and retrieval via Mem0
* **Persistent Storage** - MongoDB integration for DAG structure
* **Resource Monitoring** - Track RAM/VRAM usage, optimize model loading/unloading
* **Thermal Management** - Prevent throttling during sustained inference

### Data Flow

1. User Input
2. Tenet Interface (Branch Selection)
3. Orchestration Agent (Fetch.ai)
4. Routing Decision

   * Sensitive Data → Local Model (ASUS + local inference)
   * Heavy Compute → Cloud API (ChatGPT, etc.)
5. Response Generation
6. DAG Node Creation (MongoDB)
7. Branch Management (User can fork/prune/rollback)

## Implementation Details

### Conversation DAG Structure

```javascript
{
  node_id: "uuid",
  parent_id: "parent_uuid" | null,
  children_ids: ["child1_uuid", "child2_uuid"],
  prompt: "user input",
  response: "ai output",
  model_used: "model_name",
  execution_context: "local|cloud",
  timestamp: "ISO-8601",
  metadata: {
    branch_name: "feature_exploration",
    tags: ["coding", "debugging"],
    pruned: false
  }
}
```

## Competition Track Alignments

### Fetch.ai - Agentverse

How Tenet Fits:

* Multi-Agent Architecture: Tenet uses Fetch.ai's orchestration capabilities to coordinate between multiple specialized agents, including routing agents, storage management agents, and memory management agents
* Agentverse Integration: All Tenet agents are registered on Agentverse for discoverability via ASI:One
* Chat Protocol Implementation: Full implementation of the Chat Protocol allows direct ASI:One interactions
* Real-World Problem Solving: Addresses the universal frustration of linear AI conversations
* Tool Execution: Agents execute workflows including model routing, storage optimization, memory management, and DAG operations

Specialized Agents:

* tenet-orchestrator
* tenet-storage
* tenet-memory

### Fetch.ai - OmegaClaw Skill Forge

How Tenet Fits:

* Specialist Skill for OmegaClaw
* Agentverse Integration
* Persistent context management
* API abstraction layer

### Cognition - Augment the Agent

How Tenet Fits:

* Capability enhancement
* Toil elimination
* Friction reduction
* Human-AI collaboration

### ASUS - Build Incredible

How Tenet Fits:

* Local AI execution
* Privacy-first architecture
* High performance inference

### ZETIC - Build AI Apps That Run On-Device

How Tenet Fits:

* Fully on-device core functionality
* Low latency interactions
* Efficient resource usage

### MongoDB Atlas

How Tenet Fits:

* Graph-based conversation storage
* Scalable architecture
* Optimized queries

### Figma Make Challenge

How Tenet Fits:

* Rapid prototyping
* UI/UX iteration
* Design system development

### GoDaddy Registry - Best Domain Name

How Tenet Fits:

* Strong domain identity
* Brand recognition
* Scalable naming strategy

### Cloudinary Challenge

How Tenet Fits:

* Media-rich conversations
* Optimized delivery
* Asset management

### Arista Networks - Connect the Dots

How Tenet Fits:

* Intelligent routing
* Resource orchestration
* Unified system design

### Vultr - Best Use of Vultr

How Tenet Fits:

* Cloud deployment
* GPU scaling
* Global infrastructure

## Use Cases

### 1. Software Development

* Explore different coding approaches in parallel branches
* Rollback when a solution doesn't work
* Keep context across debugging sessions
* Collaborate with team members

### 2. Research & Analysis

* Test multiple hypotheses simultaneously
* Maintain separate branches
* Preserve important findings
* Share workflows

### 3. Content Creation

* Iterate without losing versions
* Branch creative directions
* Merge successful ideas
* Maintain consistency

### 4. Learning & Education

* Explore explanations
* Build knowledge trees
* Track progress
* Share learning paths

## Competitive Advantages

### vs. Traditional Chat Interfaces

* Non-linear conversations
* Context preservation
* Version control
* Multi-model routing

### vs. Other AI Tools

* Local-first privacy
* Intelligent routing
* Graph-based organization
* Collaboration-ready

## License

[To be determined - likely MIT or Apache 2.0]

## Contact & Community

* Project Name: Tenet
* Tagline: "What happens when conversations happen in reverse"
* Inspiration: Christopher Nolan's Tenet
* Ecosystem: Fetch.ai, OpenClaw, MongoDB Atlas

> "Don't try to understand it. Feel it." - Tenet (2020)

---

Branch forward. Think backward.
