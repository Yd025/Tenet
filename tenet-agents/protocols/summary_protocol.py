from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List

class SummaryRequest(BaseModel):
    """Request for branch/conversation summarization"""
    target_type: str = Field(..., description="Type: branch, conversation, node")
    target_id: str = Field(..., description="ID of target to summarize")
    summary_length: str = Field(default="medium", description="Length: short, medium, long")
    include_metadata: bool = Field(default=True, description="Include metadata in summary")
    user_id: str = Field(..., description="User requesting summary")

class SummaryResponse(BaseModel):
    """Response with summary"""
    success: bool = Field(..., description="Whether summary was generated")
    summary: str = Field(..., description="Generated summary")
    key_points: List[str] = Field(default_factory=list, description="Key points extracted")
    statistics: dict = Field(default_factory=dict, description="Summary statistics")
    message: str = Field(..., description="Status message")

class SummaryStatistics(BaseModel):
    """Statistics about summarized content"""
    total_nodes: int = Field(..., description="Total nodes summarized")
    total_tokens: int = Field(..., description="Total tokens processed")
    summary_tokens: int = Field(..., description="Tokens in summary")
    compression_ratio: float = Field(..., description="Compression ratio")

summary_protocol = Protocol("summary", version="1.0")