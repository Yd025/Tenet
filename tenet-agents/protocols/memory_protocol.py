from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class MemoryAction(str, Enum):
    STORE = "store"
    RETRIEVE = "retrieve"
    SEARCH = "search"
    DELETE = "delete"
    PROMOTE = "promote"

class MemoryRequest(BaseModel):
    """Request for memory operations"""
    action: MemoryAction = Field(..., description="Action: store, retrieve, search, delete, promote")
    conversation_id: Optional[str] = Field(None, description="Conversation identifier")
    branch_id: Optional[str] = Field(None, description="Branch identifier")
    context: Optional[Dict] = Field(None, description="Context to store")
    query: Optional[str] = Field(None, description="Search query")
    limit: Optional[int] = Field(10, description="Result limit")

class MemoryResponse(BaseModel):
    """Response from memory operations"""
    success: bool = Field(..., description="Whether operation was successful")
    action: MemoryAction = Field(..., description="Action performed")
    context: Optional[Dict] = Field(None, description="Retrieved context")
    results: Optional[List[Dict]] = Field(None, description="Search results")
    message: str = Field(..., description="Status message")

class ContextData(BaseModel):
    """Conversation context data"""
    conversation_id: str = Field(..., description="Conversation identifier")
    branch_id: Optional[str] = Field(None, description="Branch identifier")
    node_id: str = Field(..., description="Node identifier")
    prompt: str = Field(..., description="User prompt")
    response: str = Field(..., description="AI response")
    model_used: str = Field(..., description="Model used")
    timestamp: float = Field(..., description="Unix timestamp")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")

memory_protocol = Protocol("memory", version="1.0")
