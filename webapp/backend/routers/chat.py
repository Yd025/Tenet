# Chat routing:
# 1. FastAPI receives request
# 2. For demo: calls Ollama directly (Step 10 implementation)
# 3. Production: orchestrator_agent.py handles routing via uagents protocol
#    The orchestrator applies privacy routing (deepseek for sensitive, qwen for general)
#    and can be extended to route between local and cloud models

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter()

OLLAMA_URL = "http://localhost:11434"

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
}

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    model_name = MODEL_MAP.get(req.model, req.model)
    # If sensitive, override with deepseek regardless of selection
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
        raise HTTPException(status_code=503, detail="Ollama not running at localhost:11434")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    import uuid
    response_text = data.get("response", "")
    eval_duration = data.get("eval_duration", 1)  # nanoseconds
    eval_count = data.get("eval_count", 1)
    tps = round(eval_count / (eval_duration / 1e9), 1) if eval_duration > 0 else 0.0

    return ChatResponse(
        response=response_text,
        node_id=str(uuid.uuid4()),
        model_used=req.model,
        tps=tps,
    )
