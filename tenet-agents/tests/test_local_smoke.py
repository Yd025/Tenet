import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.local_runtime import dag_store, memory_store, model_registry, router
from agents.tag_manager_agent import TenetTagManager, TagRequest, TagAction
from agents.rollback_agent import TenetRollbackAgent
from agents.diff_viewer_agent import TenetDiffViewerAgent, DiffRequest
from agents.branch_comparator_agent import TenetBranchComparatorAgent


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


def test_tag_manager_smoke():
    conversation_id = "conv-tag-1"
    branch = dag_store.create_branch(conversation_id, None, "tag-branch")
    node = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=branch["branch_id"],
        prompt="Tag me",
        response="Tagged node",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )
    manager = TenetTagManager()
    add_response = manager.add_tags(
        TagRequest(
            action=TagAction.ADD,
            conversation_id=conversation_id,
            node_id=node["node_id"],
            tags=["todo", "important"],
        )
    )
    assert add_response.success
    assert "todo" in add_response.tags
    filter_response = manager.filter_nodes(
        TagRequest(
            action=TagAction.FILTER,
            conversation_id=conversation_id,
            tags=["todo"],
        )
    )
    assert filter_response.success
    assert any(item["node_id"] == node["node_id"] for item in filter_response.matched_nodes)


def test_rollback_diff_and_compare_smoke():
    conversation_id = "conv-advanced-1"
    main = dag_store.create_branch(conversation_id, None, "main")
    n1 = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=main["branch_id"],
        prompt="Start",
        response="Base response",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )
    n2 = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=main["branch_id"],
        parent_id=n1["node_id"],
        prompt="Update",
        response="Updated response",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )
    alt = dag_store.create_branch(conversation_id, n1["node_id"], "alt")
    n3 = dag_store.add_node(
        conversation_id=conversation_id,
        branch_id=alt["branch_id"],
        parent_id=n1["node_id"],
        prompt="Alternative",
        response="Alternative response",
        model_used="llama2-7b-4bit",
        execution_location="local",
    )

    rollback = TenetRollbackAgent()
    rolled = rollback.execute_rollback(conversation_id, main["branch_id"], n1["node_id"])
    assert rolled["head_node_id"] == n1["node_id"]

    diff_agent = TenetDiffViewerAgent()
    diff = diff_agent.build_diff(
        DiffRequest(
            conversation_id=conversation_id,
            left_node_id=n2["node_id"],
            right_node_id=n3["node_id"],
            include_prompt=True,
        )
    )
    assert diff.success
    assert len(diff.diff_lines) > 0

    comparator = TenetBranchComparatorAgent()
    compare = comparator.compare_branches(main["branch_id"], alt["branch_id"])
    assert compare.success
    assert n1["node_id"] in compare.shared_node_ids
