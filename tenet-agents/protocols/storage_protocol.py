from uagents.protocol import Protocol
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class StorageAction(str, Enum):
    LIST = "list"
    LOAD = "load"
    UNLOAD = "unload"
    STATUS = "status"
    OPTIMIZE = "optimize"

class ModelInfo(BaseModel):
    """Information about a model"""
    name: str = Field(..., description="Model name")
    size_gb: float = Field(..., description="Model size in GB")
    quantization: str = Field(..., description="Quantization level")
    status: str = Field(..., description="Model status: loaded, unloaded, error")
    hardware_requirements: Dict = Field(..., description="Hardware requirements")
    last_used: Optional[str] = Field(None, description="Last used timestamp")

class StorageRequest(BaseModel):
    """Request for storage operations"""
    action: StorageAction = Field(..., description="Action: list, load, unload, status, optimize")
    model_name: Optional[str] = Field(None, description="Model name for specific actions")
    parameters: Optional[Dict] = Field(None, description="Additional parameters")

class StorageResponse(BaseModel):
    """Response from storage operations"""
    success: bool = Field(..., description="Whether operation was successful")
    action: StorageAction = Field(..., description="Action performed")
    models: Optional[List[ModelInfo]] = Field(None, description="List of models")
    message: str = Field(..., description="Status message")
    storage_info: Optional[Dict] = Field(None, description="Storage information")

class ModelStatusRequest(BaseModel):
    """Request for model status"""
    model_name: str = Field(..., description="Model name")

class ModelStatusResponse(BaseModel):
    """Response with model status"""
    model_name: str = Field(..., description="Model name")
    status: str = Field(..., description="Current status")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    load_time_ms: Optional[float] = Field(None, description="Load time in milliseconds")

storage_protocol = Protocol("storage", version="1.0")
