import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.local_runtime import dag_store, memory_store, model_registry, router


def test_local_chat_branch_memory_flow():
    conversation_id = "conv-smoke-1"
    branch = dag_store.create_branch(conversation_id, None, "experiment")
    node = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=branch["branch_id"],
        prompt="What is Tenet?",
        response="Tenet is a DAG-native multi-agent conversation system.",
        model_used="llama2-7b-4bit",
        execution_location="local",
        metadata={"source": "smoke"},
    )
    memory_store.store(node, conversation_id, branch["branch_id"])
    retrieved = memory_store.retrieve(conversation_id, branch["branch_id"])
    assert retrieved is not None
    assert retrieved["node_id"] == node["node_id"]


def test_branch_operations_and_graph():
    conversation_id = "conv-smoke-2"
    root = dag_store.create_branch(conversation_id, None, "main")
    n1 = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=root["branch_id"],
        prompt="root prompt",
        response="root response",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )
    feature = dag_store.create_branch(conversation_id, n1["node_id"], "feature")
    dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=feature["branch_id"],
        parent_id=n1["node_id"],
        prompt="feature prompt",
        response="feature response",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )
    dag_store.rollback(conversation_id, feature["branch_id"], n1["node_id"])
    graph = dag_store.get_graph(conversation_id)
    assert graph["conversation_id"] == conversation_id
    assert len(graph["branches"]) >= 2


def test_search_prune_export_foundations():
    conversation_id = "conv-smoke-3"
    branch = dag_store.create_branch(conversation_id, None, "searchable")
    node = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=branch["branch_id"],
        prompt="Find me by keyword banana",
        response="banana is present in this response",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )
    results = memory_store.search("banana", conversation_id, branch["branch_id"], limit=5)
    assert isinstance(results, list)
    pruned = dag_store.prune_node(node["node_id"], "soft")
    assert pruned == 1


def test_model_registry_and_router():
    models = model_registry.list_models()
    assert len(models) >= 1
    ok, _ = model_registry.load(models[0]["name"])
    assert ok
    privacy = router.analyze_privacy("my password is 123", "private")
    assert privacy["privacy_level"] in {"private", "sensitive"}
