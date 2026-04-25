from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from enum import Enum

class PrivacyLevel(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    SENSITIVE = "sensitive"

class ExecutionLocation(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"

class ChatRequest(BaseModel):
    """Incoming chat request to Tenet system"""
    prompt: str = Field(..., description="User's input prompt")
    conversation_id: str = Field(..., description="Conversation identifier")
    branch_id: Optional[str] = Field(None, description="Branch identifier if applicable")
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.PRIVATE)
    user_id: Optional[str] = Field(None, description="User identifier")
    user_preferences: Optional[Dict] = Field(None, description="User preferences")
    context: Optional[Dict] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    """Response from Tenet system"""
    response: str = Field(..., description="AI generated response")
    model_used: str = Field(..., description="Which model generated the response")
    execution_location: ExecutionLocation = Field(..., description="Where execution happened")
    conversation_id: str = Field(..., description="Conversation identifier")
    branch_id: Optional[str] = Field(None, description="Branch identifier")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")
    performance_metrics: Optional[Dict] = Field(None, description="Performance data")

class PrivacyAnalysisRequest(BaseModel):
    """Request for privacy analysis"""
    content: str = Field(..., description="Content to analyze")
    context: Optional[Dict] = Field(None, description="Additional context")

class PrivacyAnalysisResponse(BaseModel):
    """Response from privacy analysis"""
    privacy_level: PrivacyLevel = Field(..., description="Determined privacy level")
    confidence: float = Field(..., description="Confidence score (0-1)")
    sensitive_elements: List[str] = Field(default_factory=list, description="Found sensitive elements")
    recommendation: str = Field(..., description="Routing recommendation")

chat_protocol = Protocol("chat", version="1.0")
