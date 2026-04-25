from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum

class SearchType(str, Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    REGEX = "regex"

class SearchRequest(BaseModel):
    """Request to search conversations"""
    search_type: SearchType = Field(default=SearchType.SEMANTIC, description="Type of search")
    query: str = Field(..., description="Search query")
    conversation_id: Optional[str] = Field(None, description="Specific conversation to search")
    branch_id: Optional[str] = Field(None, description="Specific branch to search")
    limit: int = Field(default=10, description="Maximum results")
    filters: Optional[Dict] = Field(None, description="Additional filters")
    user_id: str = Field(..., description="User performing search")

class SearchResult(BaseModel):
    """Single search result"""
    result_id: str = Field(..., description="Unique result ID")
    conversation_id: str = Field(..., description="Conversation ID")
    branch_id: Optional[str] = Field(None, description="Branch ID")
    node_id: str = Field(..., description="Node ID")
    content: str = Field(..., description="Matching content")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    metadata: Optional[Dict] = Field(None, description="Additional metadata")

class SearchResponse(BaseModel):
    """Response from search operation"""
    success: bool = Field(..., description="Whether search was successful")
    results: List[SearchResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(..., description="Total number of results")
    search_time_ms: float = Field(..., description="Search time in milliseconds")
    query_understood: bool = Field(..., description="Whether query was understood")
    suggestions: Optional[List[str]] = Field(None, description="Search suggestions")
    message: str = Field(..., description="Status message")

search_protocol = Protocol("search", version="1.0")