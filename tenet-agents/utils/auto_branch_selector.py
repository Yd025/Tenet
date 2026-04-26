import json
import os
from typing import Dict, Optional, Tuple
from urllib import request


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")


def _tokenize(text: str) -> set[str]:
    normalized = "".join(c.lower() if c.isalnum() else " " for c in text)
    return {token for token in normalized.split() if len(token) > 2}


def _score_candidate(prompt_tokens: set[str], node: Dict) -> int:
    content = f"{node.get('prompt', '')} {node.get('response', '')}"
    node_tokens = _tokenize(content)
    return len(prompt_tokens.intersection(node_tokens))


def _fallback_parent(dag_store, conversation_id: str, branch_id: Optional[str]) -> Optional[str]:
    if branch_id:
        branch = dag_store.get_branch(branch_id)
        if branch and branch.get("head_node_id"):
            return branch.get("head_node_id")

    graph = dag_store.get_graph(conversation_id)
    active_branch_id = graph.get("active_branch_id")
    if not active_branch_id:
        return None
    active_branch = dag_store.get_branch(active_branch_id)
    if not active_branch:
        return None
    return active_branch.get("head_node_id")


def choose_best_parent_node(
    dag_store,
    conversation_id: str,
    branch_id: Optional[str],
    prompt: str,
    model_name: str,
) -> Tuple[Optional[str], Dict]:
    nodes = dag_store.list_nodes(conversation_id, branch_id=branch_id, include_pruned=False)
    if not nodes:
        return None, {"selector": "auto-branch-llm", "reason": "no_candidates"}

    prompt_tokens = _tokenize(prompt)
    top_candidates = sorted(
        nodes,
        key=lambda n: (_score_candidate(prompt_tokens, n), n.get("timestamp", 0)),
        reverse=True,
    )[:10]
    if not top_candidates:
        return _fallback_parent(dag_store, conversation_id, branch_id), {
            "selector": "auto-branch-llm",
            "reason": "empty_top_candidates",
        }

    candidate_lines = []
    for node in top_candidates:
        snippet = f"{node.get('prompt', '')} {node.get('response', '')}".replace("\n", " ").strip()
        candidate_lines.append(f"- {node['node_id']}: {snippet[:260]}")

    selector_prompt = (
        "You are selecting the best parent node for branching in a conversation DAG.\n"
        "Choose one node_id from candidates.\n"
        'Return strict JSON only: {"parent_id":"<node_id>","reason":"<short reason>"}\n\n'
        f'User prompt: "{prompt}"\n'
        "Candidates:\n"
        + "\n".join(candidate_lines)
    )

    payload = json.dumps(
        {
            "model": model_name,
            "prompt": selector_prompt,
            "stream": False,
        }
    ).encode("utf-8")

    try:
        req = request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            raw = body.get("response", "").strip()
            parsed = json.loads(raw)
            parent_id = parsed.get("parent_id")
            if isinstance(parent_id, str) and any(n["node_id"] == parent_id for n in top_candidates):
                return parent_id, {
                    "selector": "auto-branch-llm",
                    "reason": parsed.get("reason", ""),
                    "candidates_considered": len(top_candidates),
                }
    except Exception as exc:
        fallback = _fallback_parent(dag_store, conversation_id, branch_id)
        return fallback, {
            "selector": "auto-branch-llm",
            "reason": "selector_failed",
            "error": str(exc),
            "candidates_considered": len(top_candidates),
        }

    fallback = top_candidates[0]["node_id"]
    return fallback, {
        "selector": "auto-branch-llm",
        "reason": "invalid_selector_output",
        "candidates_considered": len(top_candidates),
    }
