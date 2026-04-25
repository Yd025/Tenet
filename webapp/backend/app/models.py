from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid

# This is what the Frontend sends to you
class ChatRequest(BaseModel):
    prompt: str
    parent_id: Optional[str] = None
    root_id: str
    model: str
    is_sensitive: bool

# This is what you save to MongoDB
class MessageNode(BaseModel):
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    root_id: str
    role: str
    content: str
    metadata: Dict[str, Any] = {}