import threading
import time
import uuid
from copy import deepcopy
from typing import Dict, List, Optional


class LocalDagStore:
    """Thread-safe in-memory conversation DAG store."""

    def __init__(self):
        self._lock = threading.RLock()
        self._conversations: Dict[str, Dict] = {}
        self._branches: Dict[str, Dict] = {}
        self._nodes: Dict[str, Dict] = {}

    def _ensure_conversation(self, conversation_id: str) -> Dict:
        conversation = self._conversations.get(conversation_id)
        if conversation:
            return conversation

        root_branch_id = str(uuid.uuid4())
        now = time.time()
        conversation = {
            "conversation_id": conversation_id,
            "active_branch_id": root_branch_id,
            "branch_ids": [root_branch_id],
            "created_at": now,
            "updated_at": now,
        }
        self._conversations[conversation_id] = conversation
        self._branches[root_branch_id] = {
            "branch_id": root_branch_id,
            "conversation_id": conversation_id,
            "branch_name": "main",
            "node_ids": [],
            "head_node_id": None,
            "pruned": False,
            "created_at": now,
            "last_activity": now,
        }
        return conversation

    def _touch_conversation(self, conversation_id: str):
        self._conversations[conversation_id]["updated_at"] = time.time()

    def add_node(
        self,
        conversation_id: str,
        prompt: str,
        response: str,
        model_used: str,
        execution_location: str,
        branch_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        with self._lock:
            conversation = self._ensure_conversation(conversation_id)
            active_branch_id = branch_id or conversation["active_branch_id"]
            if active_branch_id not in self._branches:
                raise ValueError(f"Unknown branch: {active_branch_id}")

            node_id = str(uuid.uuid4())
            now = time.time()
            node = {
                "node_id": node_id,
                "conversation_id": conversation_id,
                "branch_id": active_branch_id,
                "parent_id": parent_id,
                "children_ids": [],
                "prompt": prompt,
                "response": response,
                "model_used": model_used,
                "execution_location": execution_location,
                "timestamp": now,
                "metadata": metadata or {},
                "pruned": False,
            }
            self._nodes[node_id] = node

            if parent_id and parent_id in self._nodes:
                self._nodes[parent_id]["children_ids"].append(node_id)

            branch = self._branches[active_branch_id]
            branch["node_ids"].append(node_id)
            branch["head_node_id"] = node_id
            branch["last_activity"] = now
            self._touch_conversation(conversation_id)
            return deepcopy(node)

    def create_branch(
        self,
        conversation_id: str,
        source_node_id: Optional[str],
        branch_name: Optional[str],
    ) -> Dict:
        with self._lock:
            conversation = self._ensure_conversation(conversation_id)
            new_branch_id = str(uuid.uuid4())
            now = time.time()
            self._branches[new_branch_id] = {
                "branch_id": new_branch_id,
                "conversation_id": conversation_id,
                "branch_name": branch_name or f"branch-{new_branch_id[:8]}",
                "node_ids": [source_node_id] if source_node_id else [],
                "head_node_id": source_node_id,
                "pruned": False,
                "created_at": now,
                "last_activity": now,
            }
            conversation["branch_ids"].append(new_branch_id)
            conversation["active_branch_id"] = new_branch_id
            self._touch_conversation(conversation_id)
            return deepcopy(self._branches[new_branch_id])

    def list_branches(self, conversation_id: str, include_pruned: bool = False) -> List[Dict]:
        with self._lock:
            conversation = self._ensure_conversation(conversation_id)
            results = []
            for branch_id in conversation["branch_ids"]:
                branch = self._branches[branch_id]
                if not include_pruned and branch.get("pruned"):
                    continue
                results.append(deepcopy(branch))
            return results

    def switch_branch(self, conversation_id: str, branch_id: str) -> Dict:
        with self._lock:
            conversation = self._ensure_conversation(conversation_id)
            if branch_id not in conversation["branch_ids"]:
                raise ValueError("Branch not in conversation")
            conversation["active_branch_id"] = branch_id
            self._touch_conversation(conversation_id)
            return deepcopy(self._branches[branch_id])

    def rollback(self, conversation_id: str, branch_id: str, target_node_id: str) -> Dict:
        with self._lock:
            self._ensure_conversation(conversation_id)
            branch = self._branches.get(branch_id)
            if not branch:
                raise ValueError("Unknown branch")
            if target_node_id not in branch["node_ids"]:
                raise ValueError("Target node not in branch")
            branch["head_node_id"] = target_node_id
            branch["last_activity"] = time.time()
            self._touch_conversation(conversation_id)
            return deepcopy(branch)

    def delete_branch(self, conversation_id: str, branch_id: str) -> bool:
        with self._lock:
            conversation = self._ensure_conversation(conversation_id)
            if branch_id not in conversation["branch_ids"]:
                return False
            if len(conversation["branch_ids"]) == 1:
                return False
            self._branches[branch_id]["pruned"] = True
            if conversation["active_branch_id"] == branch_id:
                conversation["active_branch_id"] = conversation["branch_ids"][0]
            self._touch_conversation(conversation_id)
            return True

    def get_node(self, node_id: str) -> Optional[Dict]:
        with self._lock:
            node = self._nodes.get(node_id)
            return deepcopy(node) if node else None

    def list_nodes(
        self,
        conversation_id: str,
        branch_id: Optional[str] = None,
        include_pruned: bool = False,
    ) -> List[Dict]:
        with self._lock:
            nodes: List[Dict] = []
            for node in self._nodes.values():
                if node.get("conversation_id") != conversation_id:
                    continue
                if branch_id and node.get("branch_id") != branch_id:
                    continue
                if not include_pruned and node.get("pruned"):
                    continue
                nodes.append(deepcopy(node))
            nodes.sort(key=lambda n: n.get("timestamp", 0))
            return nodes

    def update_node_metadata(self, node_id: str, metadata: Dict) -> Optional[Dict]:
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return None
            current = node.get("metadata", {})
            current.update(metadata)
            node["metadata"] = current
            return deepcopy(node)

    def get_branch(self, branch_id: str) -> Optional[Dict]:
        with self._lock:
            branch = self._branches.get(branch_id)
            if not branch:
                return None
            nodes = [deepcopy(self._nodes[nid]) for nid in branch["node_ids"] if nid in self._nodes]
            payload = deepcopy(branch)
            payload["nodes"] = nodes
            return payload

    def prune_node(self, node_id: str, strategy: str) -> int:
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return 0
            if strategy == "hard":
                del self._nodes[node_id]
                return 1
            node["pruned"] = True
            return 1

    def prune_branch(self, branch_id: str, strategy: str) -> int:
        with self._lock:
            branch = self._branches.get(branch_id)
            if not branch:
                return 0
            count = 0
            for node_id in list(branch["node_ids"]):
                count += self.prune_node(node_id, strategy)
            branch["pruned"] = True
            return count + 1

    def prune_subtree(self, root_node_id: str, strategy: str) -> int:
        with self._lock:
            root = self._nodes.get(root_node_id)
            if not root:
                return 0
            to_visit = [root_node_id]
            seen = set()
            while to_visit:
                node_id = to_visit.pop()
                if node_id in seen or node_id not in self._nodes:
                    continue
                seen.add(node_id)
                to_visit.extend(self._nodes[node_id].get("children_ids", []))
            for node_id in seen:
                self.prune_node(node_id, strategy)
            return len(seen)

    def get_subtree(self, root_node_id: str) -> Dict:
        with self._lock:
            to_visit = [root_node_id]
            seen = []
            while to_visit:
                node_id = to_visit.pop()
                node = self._nodes.get(node_id)
                if not node or node_id in seen:
                    continue
                seen.append(node_id)
                to_visit.extend(node.get("children_ids", []))
            return {"nodes": [deepcopy(self._nodes[nid]) for nid in seen]}

    def merge_branches(self, conversation_id: str, source_branch_id: str, target_branch_id: str) -> Dict:
        with self._lock:
            source = self.get_branch(source_branch_id)
            target = self.get_branch(target_branch_id)
            if not source or not target:
                raise ValueError("Invalid source or target branch")
            merged = self.create_branch(
                conversation_id=conversation_id,
                source_node_id=target.get("head_node_id"),
                branch_name=f"merged-{source_branch_id[:6]}-{target_branch_id[:6]}",
            )
            existing_ids = set(self._branches[merged["branch_id"]]["node_ids"])
            for node in source["nodes"] + target["nodes"]:
                if node["node_id"] not in existing_ids:
                    self._branches[merged["branch_id"]]["node_ids"].append(node["node_id"])
                    existing_ids.add(node["node_id"])
            if self._branches[merged["branch_id"]]["node_ids"]:
                self._branches[merged["branch_id"]]["head_node_id"] = self._branches[merged["branch_id"]]["node_ids"][-1]
            return deepcopy(self._branches[merged["branch_id"]])

    def get_graph(self, conversation_id: str, include_pruned: bool = False) -> Dict:
        with self._lock:
            conversation = self._ensure_conversation(conversation_id)
            branches = self.list_branches(conversation_id, include_pruned=include_pruned)
            node_ids = {nid for b in branches for nid in b["node_ids"]}
            nodes = []
            for node_id in node_ids:
                node = self._nodes.get(node_id)
                if not node:
                    continue
                if not include_pruned and node.get("pruned"):
                    continue
                nodes.append(deepcopy(node))
            return {
                "conversation_id": conversation_id,
                "active_branch_id": conversation["active_branch_id"],
                "branches": branches,
                "nodes": nodes,
            }

