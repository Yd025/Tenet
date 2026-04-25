from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class PruneTarget(str, Enum):
    NODE = "node"
    BRANCH = "branch"
    SUBTREE = "subtree"

class PruneRequest(BaseModel):
    """Request to prune nodes or branches"""
    target_type: PruneTarget = Field(..., description="Type of target to prune")
    target_id: str = Field(..., description="ID of target to prune")
    conversation_id: str = Field(..., description="Parent conversation ID")
    prune_strategy: str = Field(default="soft", description="soft (archive) or hard (delete)")
    create_backup: bool = Field(default=True, description="Create backup before pruning")
    user_id: str = Field(..., description="User performing prune")
    reason: Optional[str] = Field(None, description="Reason for pruning")

class PruneResponse(BaseModel):
    """Response from prune operation"""
    success: bool = Field(..., description="Whether prune was successful")
    items_pruned: int = Field(..., description="Number of items pruned")
    space_freed_mb: float = Field(..., description="Space freed in MB")
    backup_created: bool = Field(..., description="Whether backup was created")
    backup_id: Optional[str] = Field(None, description="ID of backup if created")
    prune_summary: str = Field(..., description="Summary of prune operation")
    message: str = Field(..., description="Status message")

class PrunePreview(BaseModel):
    """Preview of what would be pruned"""
    target_id: str = Field(..., description="ID of target")
    items_to_prune: int = Field(..., description="Number of items that would be pruned")
    estimated_space_mb: float = Field(..., description="Estimated space to be freed")
    affected_branches: List[str] = Field(default_factory=list, description="Branches that would be affected")

prune_protocol = Protocol("prune", version="1.0")