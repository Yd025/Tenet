import threading
from copy import deepcopy
from typing import Dict, List, Optional


class LocalMemoryStore:
    """In-memory context storage and retrieval."""

    def __init__(self):
        self._lock = threading.RLock()
        self._contexts: Dict[str, List[Dict]] = {}
        self._promoted: List[Dict] = []

    def _key(self, conversation_id: Optional[str], branch_id: Optional[str]) -> str:
        return f"{conversation_id or 'global'}::{branch_id or 'all'}"

    def store(self, context: Dict, conversation_id: Optional[str], branch_id: Optional[str]) -> Dict:
        with self._lock:
            key = self._key(conversation_id, branch_id)
            self._contexts.setdefault(key, []).append(deepcopy(context))
            return deepcopy(context)

    def retrieve(self, conversation_id: Optional[str], branch_id: Optional[str]) -> Optional[Dict]:
        with self._lock:
            key = self._key(conversation_id, branch_id)
            entries = self._contexts.get(key, [])
            if not entries:
                return None
            return deepcopy(entries[-1])

    def search(self, query: str, conversation_id: Optional[str], branch_id: Optional[str], limit: int) -> List[Dict]:
        with self._lock:
            key = self._key(conversation_id, branch_id)
            haystack = self._contexts.get(key, [])
            q = (query or "").lower()
            results = []
            for item in reversed(haystack):
                if q in str(item).lower():
                    results.append(deepcopy(item))
                if len(results) >= limit:
                    break
            return results

    def delete(self, conversation_id: Optional[str], branch_id: Optional[str]) -> int:
        with self._lock:
            key = self._key(conversation_id, branch_id)
            removed = len(self._contexts.get(key, []))
            self._contexts.pop(key, None)
            return removed

    def promote(self, conversation_id: Optional[str], branch_id: Optional[str], limit: int) -> List[Dict]:
        with self._lock:
            key = self._key(conversation_id, branch_id)
            entries = self._contexts.get(key, [])[-limit:]
            self._promoted.extend(deepcopy(entries))
            return deepcopy(entries)

