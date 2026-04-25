from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    CSV = "csv"
    HTML = "html"

class ExportRequest(BaseModel):
    """Request to export conversation data"""
    target_type: str = Field(..., description="Type: conversation, branch, node")
    target_id: str = Field(..., description="ID of target to export")
    export_format: ExportFormat = Field(default=ExportFormat.MARKDOWN, description="Export format")
    include_metadata: bool = Field(default=True, description="Include metadata")
    include_branches: bool = Field(default=True, description="Include branch information")
    user_id: str = Field(..., description="User requesting export")

class ExportResponse(BaseModel):
    """Response with exported data"""
    success: bool = Field(..., description="Whether export was successful")
    export_url: Optional[str] = Field(None, description="URL to download export")
    export_data: Optional[str] = Field(None, description="Exported data (if small)")
    export_size_bytes: int = Field(..., description="Size of export in bytes")
    export_format: ExportFormat = Field(..., description="Format of export")
    items_exported: int = Field(..., description="Number of items exported")
    message: str = Field(..., description="Status message")

export_protocol = Protocol("export", version="1.0")