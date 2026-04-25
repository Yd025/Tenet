# Chat routing:
# 1. FastAPI receives request
# 2. For demo: calls Ollama directly (Step 10 implementation)
# 3. Production: orchestrator_agent.py handles routing via uagents protocol
#    The orchestrator applies privacy routing (deepseek for sensitive, qwen for general)
#    and can be extended to route between local and cloud models

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from command_dispatcher import is_command, dispatch as dispatch_command, dag_store

router = APIRouter()

OLLAMA_URL = "http://100.127.248.116:11434"

class ChatRequest(BaseModel):
    prompt: str
    conversation_id: str
    branch_id: str
    model: str  # "deepseek" or "qwen"
    is_sensitive: bool

class ChatResponse(BaseModel):
    response: str
    node_id: str
    model_used: str
    tps: float

# Model name mapping
MODEL_MAP = {
    "deepseek": "deepseek-r1:latest",
    "qwen": "qwen2.5:latest",
    "gemma4": "gemma4",
}

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if is_command(req.prompt):
        result = await dispatch_command(req.prompt, req.conversation_id, req.branch_id)
        node = dag_store.add_node(
            conversation_id=req.conversation_id,
            prompt=req.prompt,
            response=result["response"],
            model_used="system",
            execution_location="local",
            parent_id=req.branch_id or None,
        )
        return ChatResponse(
            response=result["response"],
            node_id=node["node_id"],
            model_used="system",
            tps=0.0,
        )

    model_name = MODEL_MAP.get(req.model, req.model)
    if req.is_sensitive:
        model_name = MODEL_MAP["deepseek"]

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model_name,
                    "prompt": req.prompt,
                    "stream": False,
                }
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Ollama not reachable at {OLLAMA_URL}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    response_text = data.get("response", "")
    eval_duration = data.get("eval_duration", 1)  # nanoseconds
    eval_count = data.get("eval_count", 1)
    tps = round(eval_count / (eval_duration / 1e9), 1) if eval_duration > 0 else 0.0

    node = dag_store.add_node(
        conversation_id=req.conversation_id,
        prompt=req.prompt,
        response=response_text,
        model_used=req.model,
        execution_location="local",
        parent_id=req.branch_id or None,
    )

    return ChatResponse(
        response=response_text,
        node_id=node["node_id"],
        model_used=req.model,
        tps=tps,
    )
