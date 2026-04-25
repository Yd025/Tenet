# app/models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

class MessageNode(BaseModel):
    # The unique ID for this specific message
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # The ID of the message this branched from (None if it's the start)
    parent_id: Optional[str] = None
    
    # The ID of the very first message in the whole tree (The "Project" ID)
    root_id: str
    
    role: str  # "user" or "assistant"
    content: str
    
    # metadata stores technical details for the ASUS/Privacy track
    metadata: Dict[str, Any] = {
        "branch_label": "Main Branch",
        "is_local": True,
        "model": "deepseek-r1",
        "tps": 0.0,
        "timestamp": datetime.utcnow().isoformat()
    }