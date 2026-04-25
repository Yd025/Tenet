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
```

## Validate Local Workflows

```bash
cd tenet-agents
../.venv/bin/python -m pytest tests/test_local_smoke.py
```

## Notes

- `ExecutionLocation` is still part of contracts, but local-only policy forces local execution.
- Cloud calls remain intentionally disabled in runtime behavior.