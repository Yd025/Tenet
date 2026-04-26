"""
Slash-command dispatcher for Tenet chat.

Intercepts prompts starting with '/' and routes them to in-process
agent logic (LocalDagStore / LocalMemoryStore).  Commands that benefit
from natural-language intelligence call Ollama for real LLM responses.
Normal prompts fall through untouched.
"""

import json
import os
import sys
import uuid
from typing import Optional

import httpx

_AGENTS_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "tenet-agents"))
if _AGENTS_ROOT not in sys.path:
    sys.path.insert(0, _AGENTS_ROOT)

from utils.local_dag_store import LocalDagStore
from utils.local_memory_store import LocalMemoryStore

dag_store = LocalDagStore()
memory_store = LocalMemoryStore()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")

COMMANDS = {
    "/branch":    "Manage branches.  Usage: /branch create <name> | list | switch <id>",
    "/search":    "Search nodes.     Usage: /search <query>",
    "/summarize": "Summarize branch. Usage: /summarize [branch_id]",
    "/prune":     "Prune a node.     Usage: /prune <node_id>",
    "/export":    "Export data.       Usage: /export [json|markdown]",
    "/help":      "Show this help message.",
}


# ---------------------------------------------------------------------------
# Ollama helper
# ---------------------------------------------------------------------------
async def _call_ollama(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
    except Exception as exc:
        return f"(LLM unavailable: {exc})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def is_command(prompt: str) -> bool:
    return prompt.strip().startswith("/")


async def dispatch(prompt: str, conversation_id: str, branch_id: Optional[str]) -> dict:
    parts = prompt.strip().split(maxsplit=2)
    cmd = parts[0].lower()
    sub = parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else ""

    handlers = {
        "/branch": _handle_branch,
        "/search": _handle_search,
        "/summarize": _handle_summarize,
        "/prune": _handle_prune,
        "/export": _handle_export,
        "/help": _handle_help,
    }
    handler = handlers.get(cmd, _handle_unknown)
    try:
        return await handler(conversation_id, branch_id, sub, arg)
    except Exception as exc:
        return {"response": f"**Error:** {exc}", "node_id": str(uuid.uuid4())}


# ---------------------------------------------------------------------------
# /branch  (data operations -- no LLM needed)
# ---------------------------------------------------------------------------
async def _handle_branch(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    action = sub.lower().strip()

    if action == "create":
        name = arg.strip() or "New Branch"
        result = dag_store.create_branch(conversation_id, None, name)
        return {
            "response": (
                f"**Branch created**\n\n"
                f"- **Name:** {name}\n"
                f"- **Branch ID:** `{result['branch_id']}`"
            ),
            "node_id": str(uuid.uuid4()),
        }

    if action == "list":
        branches = dag_store.list_branches(conversation_id, include_pruned=False)
        if not branches:
            return {"response": "No branches found for this conversation.", "node_id": str(uuid.uuid4())}
        lines = ["**Branches:**\n"]
        for i, b in enumerate(branches, 1):
            nodes = len(b.get("node_ids", []))
            name = b.get("branch_name", "unnamed")
            bid = b["branch_id"]
            lines.append(f"{i}. **{name}** — `{bid[:12]}…` ({nodes} nodes)")
        return {"response": "\n".join(lines), "node_id": str(uuid.uuid4())}

    if action == "switch":
        target = arg.strip()
        if not target:
            return {"response": "Usage: `/branch switch <branch_id>`", "node_id": str(uuid.uuid4())}
        all_branches = dag_store.list_branches(conversation_id, include_pruned=False)
        match = next((b for b in all_branches if b["branch_id"].startswith(target)), None)
        if not match:
            return {"response": f"No branch matching `{target}`.", "node_id": str(uuid.uuid4())}
        dag_store.switch_branch(conversation_id, match["branch_id"])
        return {
            "response": f"Switched to branch **{match.get('branch_name', '')}** (`{match['branch_id'][:12]}…`)",
            "node_id": str(uuid.uuid4()),
        }

    return {
        "response": "Usage: `/branch create <name>` | `/branch list` | `/branch switch <id>`",
        "node_id": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# /search  (keyword match + LLM synthesis of results)
# ---------------------------------------------------------------------------
async def _handle_search(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    query = f"{sub} {arg}".strip()
    if not query:
        return {"response": "Usage: `/search <query>`", "node_id": str(uuid.uuid4())}

    nodes = dag_store.list_nodes(conversation_id, branch_id=None, include_pruned=False)
    q = query.lower()
    hits = []
    for node in nodes:
        content = f"{node.get('prompt', '')}\n{node.get('response', '')}".lower()
        if q in content:
            hits.append(node)
        if len(hits) >= 10:
            break

    if not hits:
        return {"response": f"No results for **\"{query}\"**.", "node_id": str(uuid.uuid4())}

    # Build context from matching nodes for LLM synthesis
    context_parts = []
    for i, h in enumerate(hits, 1):
        context_parts.append(
            f"[Result {i}]\n"
            f"Prompt: {h.get('prompt', '')[:200]}\n"
            f"Response: {h.get('response', '')[:300]}"
        )
    context_block = "\n\n".join(context_parts)

    llm_prompt = (
        f"The user searched a conversation for \"{query}\". "
        f"Here are the matching conversation nodes:\n\n"
        f"{context_block}\n\n"
        f"Provide a concise synthesis of what these results tell us about \"{query}\". "
        f"Highlight the key information found."
    )
    synthesis = await _call_ollama(llm_prompt)

    return {
        "response": (
            f"**Search results for \"{query}\"** ({len(hits)} hits):\n\n"
            f"{synthesis}"
        ),
        "node_id": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# /summarize  (LLM-generated summary of branch content)
# ---------------------------------------------------------------------------
async def _handle_summarize(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    target_branch = sub.strip() or None
    nodes = dag_store.list_nodes(conversation_id, branch_id=target_branch, include_pruned=False)
    if not nodes:
        return {"response": "No nodes to summarize.", "node_id": str(uuid.uuid4())}

    branch_info = dag_store.get_branch(target_branch) if target_branch else None
    branch_name = branch_info.get("branch_name", "unknown") if branch_info else "current"

    # Build conversation transcript for the LLM
    transcript_parts = []
    for n in nodes[:20]:  # cap at 20 nodes to stay within context limits
        prompt = n.get("prompt", "").strip()
        response = n.get("response", "").strip()
        if prompt:
            transcript_parts.append(f"User: {prompt[:300]}")
        if response:
            transcript_parts.append(f"Assistant: {response[:300]}")
    transcript = "\n\n".join(transcript_parts)

    llm_prompt = (
        f"Summarize the following conversation branch named \"{branch_name}\" "
        f"({len(nodes)} messages). Identify the main topics discussed, "
        f"key decisions or insights, and any open questions.\n\n"
        f"--- Conversation ---\n{transcript}\n--- End ---\n\n"
        f"Provide a structured summary with sections for: "
        f"Overview, Key Topics, Important Insights, and Open Questions."
    )
    summary = await _call_ollama(llm_prompt)

    return {
        "response": (
            f"**Summary of branch \"{branch_name}\"** ({len(nodes)} nodes):\n\n"
            f"{summary}"
        ),
        "node_id": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# /prune  (data operation -- no LLM needed)
# ---------------------------------------------------------------------------
async def _handle_prune(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    target_id = sub.strip()
    if not target_id:
        return {"response": "Usage: `/prune <node_id>`", "node_id": str(uuid.uuid4())}

    all_nodes = dag_store.list_nodes(conversation_id, include_pruned=False)
    match = next((n for n in all_nodes if n["node_id"].startswith(target_id)), None)
    if not match:
        return {"response": f"No node matching `{target_id}`.", "node_id": str(uuid.uuid4())}

    count = dag_store.prune_node(match["node_id"], "soft")
    return {
        "response": f"**Pruned** node `{match['node_id'][:12]}…` (soft delete, {count} item(s) affected).",
        "node_id": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# /export  (data formatting + LLM-generated intro)
# ---------------------------------------------------------------------------
async def _handle_export(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    fmt = sub.strip().lower() or "json"
    nodes = dag_store.list_nodes(conversation_id, branch_id=None, include_pruned=False)
    if not nodes:
        return {"response": "Nothing to export.", "node_id": str(uuid.uuid4())}

    # Ask LLM to generate a title/description for the export
    first_prompts = [n.get("prompt", "")[:100] for n in nodes[:5] if n.get("prompt")]
    topics = "; ".join(first_prompts) if first_prompts else "general conversation"
    intro = await _call_ollama(
        f"Write a one-sentence title for a conversation export covering these topics: {topics}"
    )

    if fmt == "markdown":
        lines = [f"# {intro.strip()}\n"]
        for n in nodes:
            lines.append(f"### {n.get('prompt', '(no prompt)')}\n")
            lines.append(f"{n.get('response', '')}\n")
            lines.append("---\n")
        data = "\n".join(lines)
    else:
        safe_nodes = []
        for n in nodes:
            safe_nodes.append({
                "node_id": n["node_id"],
                "prompt": n.get("prompt", ""),
                "response": n.get("response", ""),
                "branch_id": n.get("branch_id"),
                "timestamp": n.get("timestamp"),
            })
        data = json.dumps({"title": intro.strip(), "nodes": safe_nodes}, indent=2)

    truncated = data[:3000]
    if len(data) > 3000:
        truncated += "\n\n… (truncated)"

    return {
        "response": f"**Export ({fmt}, {len(nodes)} nodes):**\n\n```\n{truncated}\n```",
        "node_id": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# /help  (static -- no LLM needed)
# ---------------------------------------------------------------------------
async def _handle_help(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    lines = ["**Available commands:**\n"]
    for cmd, desc in COMMANDS.items():
        lines.append(f"- `{cmd}` — {desc}")
    lines.append("\nCommands like `/summarize` and `/search` use the LLM for intelligent responses.")
    return {"response": "\n".join(lines), "node_id": str(uuid.uuid4())}


# ---------------------------------------------------------------------------
# unknown
# ---------------------------------------------------------------------------
async def _handle_unknown(conversation_id: str, branch_id: Optional[str], sub: str, arg: str) -> dict:
    return {
        "response": "Unknown command. Type `/help` to see available commands.",
        "node_id": str(uuid.uuid4()),
    }
