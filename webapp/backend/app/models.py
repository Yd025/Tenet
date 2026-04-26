from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid

class ChatRequest(BaseModel):
    prompt: str
    parent_id: Optional[str] = None
    root_id: str
    model: str
    auto_branching: bool = False

class Node(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_ids: List[str] = []
    root_id: str
    prompt: str
    response: str
    model_used: str = "unknown"
    metadata: Dict[str, Any] = {}

class MergeRequest(BaseModel):
    node_ids: List[str]
    root_id: str
    model: str = "gemma4"
    conflict_resolutions: Optional[List[Dict[str, Any]]] = None

class RootMergeRequest(BaseModel):
    root_ids: List[str]
    new_root_name: str
    model: str = "gemma4"


class NodeSummaryRequest(BaseModel):
    root_id: str
    node_ids: Optional[List[str]] = None
    model: str = "gemma4"


class UpdateNodeRequest(BaseModel):
    prompt: Optional[str] = None
    response: Optional[str] = None
    branch_label: Optional[str] = None
    pruned: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateConversationRequest(BaseModel):
    title: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    node_ids: List[str]