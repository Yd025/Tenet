"""
WebappDagStore — a drop-in replacement for LocalDagStore that reads/writes
through the webapp's REST API (MongoDB-backed).  Agents that import this
instead of LocalDagStore operate on the same data the frontend sees.
"""
import os
from typing import Dict, List, Optional

import httpx

WEBAPP_API = os.getenv("WEBAPP_API_URL", "http://127.0.0.1:8000/api")
_TIMEOUT = 15.0


def _get(path: str, params: dict = None) -> dict | list | None:
    try:
        r = httpx.get(f"{WEBAPP_API}{path}", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _post(path: str, body: dict) -> dict | None:
    try:
        r = httpx.post(f"{WEBAPP_API}{path}", json=body, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _put(path: str, body: dict) -> dict | None:
    try:
        r = httpx.put(f"{WEBAPP_API}{path}", json=body, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


class WebappDagStore:
    """
    Thin synchronous proxy to the webapp REST API.
    Exposes the same interface as LocalDagStore so agents need minimal changes.
    """

    # ------------------------------------------------------------------
    # Node access
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[Dict]:
        return _get(f"/nodes/{node_id}")

    def list_nodes(
        self,
        conversation_id: str,
        branch_id: Optional[str] = None,
        include_pruned: bool = False,
    ) -> List[Dict]:
        nodes = _get("/nodes", params={"root_id": conversation_id}) or []
        if include_pruned:
            # fetch all including pruned — webapp /nodes filters them out,
            # so we need a separate call pattern; for now return what we have
            pass
        return nodes

    def update_node_metadata(self, node_id: str, metadata: Dict) -> Optional[Dict]:
        return _put(f"/nodes/{node_id}", {"metadata": metadata})

    # ------------------------------------------------------------------
    # Graph / conversation
    # ------------------------------------------------------------------

    def get_graph(self, conversation_id: str, include_pruned: bool = False) -> Dict:
        """
        Build a graph-like dict from the webapp's flat node list.
        The webapp doesn't have a /graph endpoint so we reconstruct it here.
        """
        nodes = self.list_nodes(conversation_id, include_pruned=include_pruned)
        return {
            "conversation_id": conversation_id,
            "nodes": nodes,
            "branches": [],  # webapp uses flat node list, not branch objects
        }

    # ------------------------------------------------------------------
    # Stubs for branch operations (webapp is flat, not branch-based)
    # These return empty/None so agents degrade gracefully.
    # ------------------------------------------------------------------

    def get_branch(self, branch_id: str) -> Optional[Dict]:
        return None

    def list_branches(self, conversation_id: str, include_pruned: bool = False) -> List[Dict]:
        return []

    def prune_node(self, node_id: str, strategy: str) -> int:
        hard = strategy == "hard"
        result = None
        try:
            r = httpx.delete(
                f"{WEBAPP_API}/nodes/{node_id}",
                params={"hard": str(hard).lower()},
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            result = r.json()
        except Exception:
            return 0
        return 1 if result else 0
