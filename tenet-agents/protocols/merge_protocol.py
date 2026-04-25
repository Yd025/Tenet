from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class MergeStrategy(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    SEMANTIC = "semantic"
    CHRONOLOGICAL = "chronological"

class MergeRequest(BaseModel):
    """Request to merge branches"""
    source_branch_id: str = Field(..., description="Source branch to merge from")
    target_branch_id: str = Field(..., description="Target branch to merge into")
    conversation_id: str = Field(..., description="Parent conversation ID")
    merge_strategy: MergeStrategy = Field(default=MergeStrategy.AUTO, description="Merge strategy")
    conflict_resolution: str = Field(default="keep_both", description="How to handle conflicts")
    user_id: str = Field(..., description="User performing merge")
    preview_only: bool = Field(default=False, description="Preview merge without executing")

class MergeConflict(BaseModel):
    """Represents a merge conflict"""
    conflict_id: str = Field(..., description="Unique conflict ID")
    node_id: str = Field(..., description="Conflicting node ID")
    conflict_type: str = Field(..., description="Type of conflict")
    source_content: str = Field(..., description="Content from source branch")
    target_content: str = Field(..., description="Content from target branch")
    suggested_resolution: Optional[str] = Field(None, description="Suggested resolution")

class MergeResponse(BaseModel):
    """Response from merge operation"""
    success: bool = Field(..., description="Whether merge was successful")
    merged_branch_id: Optional[str] = Field(None, description="ID of merged branch")
    conflicts: List[MergeConflict] = Field(default_factory=list, description="Any conflicts found")
    merge_summary: str = Field(..., description="Summary of merge operation")
    nodes_merged: int = Field(..., description="Number of nodes merged")
    message: str = Field(..., description="Status message")

merge_protocol = Protocol("merge", version="1.0")