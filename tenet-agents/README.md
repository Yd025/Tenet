# Tenet Agents (Local-Only Mode)

This package runs Tenet's agent system fully offline and local-only.

## What Changed

- Internal FastAPI/hardware endpoint calls were removed from runtime flows.
- Agents now share local services in `utils/`:
  - `local_dag_store.py`
  - `local_memory_store.py`
  - `local_model_registry.py`
  - `local_router.py`
  - `local_runtime.py` (singletons)
- Core and extended agents are wired for branching, merge/prune, search, summarize, and export operations without remote backends.

## Quick Start

```bash
cd tenet-agents
python3 -m venv ../.venv
../.venv/bin/python -m pip install -r requirements.txt
```

## Run All Agents

```bash
cd tenet-agents
../.venv/bin/python run_all_agents.py
```

## Run Individual Agents

```bash
cd tenet-agents
../.venv/bin/python agents/orchestrator_agent.py
../.venv/bin/python agents/privacy_router_agent.py
../.venv/bin/python agents/branch_manager_agent.py
../.venv/bin/python agents/model_coordinator_agent.py
../.venv/bin/python agents/context_keeper_agent.py
../.venv/bin/python agents/branch_summarizer_agent.py
../.venv/bin/python agents/branch_merger_agent.py
../.venv/bin/python agents/branch_pruner_agent.py
../.venv/bin/python agents/node_pruner_agent.py
../.venv/bin/python agents/semantic_search_agent.py
../.venv/bin/python agents/conversation_exporter_agent.py
../.venv/bin/python agents/tag_manager_agent.py
../.venv/bin/python agents/rollback_agent.py
../.venv/bin/python agents/diff_viewer_agent.py
../.venv/bin/python agents/branch_comparator_agent.py
../.venv/bin/python agents/storage_optimizer_agent.py
../.venv/bin/python agents/resource_monitor_agent.py
../.venv/bin/python agents/graph_integrity_agent.py
../.venv/bin/python agents/capability_registry_agent.py
```

## Capability-Based Routing

- `orchestrator_agent` now consults the local capability registry to select a specialist agent for each prompt.
- Registry state is managed by `capability_registry_agent` and seeded in `utils/local_runtime.py`.
- Routing decisions are attached to chat metadata as `selected_specialist_agent`.
- In local-only mode this is policy-and-selection logic; execution remains local.

## Validate Local Workflows

```bash
cd tenet-agents
../.venv/bin/python -m pytest tests/test_local_smoke.py
```

## Agentverse Gateway + Inspectors

```bash
cd tenet-agents
../.venv/bin/python gateway_agent.py
```

- HTTP gateway endpoint: `http://localhost:9000/process`
- Gateway uAgent port: `9020`

Register helper:

```bash
cd tenet-agents
../.venv/bin/python register_agent.py
```

Start local agents with health check:

```bash
cd tenet-agents
../.venv/bin/python start_all_agents.py
```

Gateway connectivity smoke test:

```bash
cd tenet-agents
../.venv/bin/python test_gateway_connection.py
```

Web inspector:

```bash
cd tenet-agents
../.venv/bin/python inspector_agent.py
```

CLI inspector:

```bash
cd tenet-agents
../.venv/bin/python cli_inspector.py
```

## Notes

- `ExecutionLocation` is still part of contracts, but local-only policy forces local execution.
- Cloud calls remain intentionally disabled in runtime behavior.
- Additional local-only tooling agents are available for tag management, rollback, diff viewing, branch comparison, storage optimization, resource monitoring, graph integrity checks, and capability registration.