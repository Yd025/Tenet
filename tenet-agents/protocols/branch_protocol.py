from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class BranchAction(str, Enum):
    CREATE = "create"
    DELETE = "delete"
    MERGE = "merge"
    SWITCH = "switch"
    LIST = "list"

class BranchRequest(BaseModel):
    """Request for branch operations"""
    action: BranchAction = Field(..., description="Action to perform")
    conversation_id: str = Field(..., description="Conversation identifier")
    node_id: Optional[str] = Field(None, description="Node to branch from")
    branch_name: Optional[str] = Field(None, description="Name for new branch")
    source_branch_id: Optional[str] = Field(None, description="Source branch for merge")
    target_branch_id: Optional[str] = Field(None, description="Target branch for merge")
    user_id: str = Field(..., description="User performing the action")

class BranchResponse(BaseModel):
    """Response from branch operations"""
    success: bool = Field(..., description="Whether operation was successful")
    action: BranchAction = Field(..., description="Action performed")
    new_branch_id: Optional[str] = Field(None, description="ID of new branch")
    new_node_id: Optional[str] = Field(None, description="ID of new node")
    branches: Optional[List[Dict]] = Field(None, description="List of branches")
    message: str = Field(..., description="Status message")

class BranchInfo(BaseModel):
    """Information about a branch"""
    branch_id: str = Field(..., description="Branch identifier")
    branch_name: str = Field(..., description="Branch name")
    conversation_id: str = Field(..., description="Parent conversation ID")
    created_at: str = Field(..., description="Creation timestamp")
    node_count: int = Field(..., description="Number of nodes in branch")
    last_activity: str = Field(..., description="Last activity timestamp")

branch_protocol = Protocol("branch", version="1.0")
