from fastapi import APIRouter, HTTPException
import httpx
import uuid
from .models import MessageNode, ChatRequest
from .database import nodes_collection
import os

router = APIRouter()

# Update these to match your 'ollama list' output exactly
MODEL_MAP = {
    "deepseek": "deepseek-v3.2:cloud", # Or whichever you prefer as default
    "qwen": "qwen3.6:latest",
    "mistral": "mistral-small3.2:24b"
}

OLLAMA_URL = os.getenv("OLLAMA_URL")

@router.post("/chat")
async def chat(req: ChatRequest):
    # 1. Map the model name
    model_name = MODEL_MAP.get(req.model, "qwen3.6:latest")
    if req.is_sensitive:
        model_name = MODEL_MAP["deepseek"]

    # 2. Reconstruct History (The 'Tenet' Walk)
    context = ""
    if req.parent_id:
        history = []
        curr_id = req.parent_id
        while curr_id:
            node = await nodes_collection.find_one({"node_id": curr_id})
            if not node: break
            history.insert(0, f"User: {node['prompt']}\nAssistant: {node['response']}")
            curr_id = node.get("parent_id")
        context = "\n".join(history)

    # 3. Call Ollama
    full_prompt = f"{context}\nUser: {req.prompt}\nAssistant:"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model_name, "prompt": full_prompt, "stream": False}
            )
            data = resp.json()
            response_text = data.get("response", "")
            # Calculate Tokens Per Second (TPS)
            tps = round(data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9), 1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference Error: {str(e)}")

    # 4. Save to MongoDB
    new_node_id = str(uuid.uuid4())
    new_node = {
        "node_id": new_node_id,
        "parent_id": req.parent_id,
        "root_id": req.root_id,
        "prompt": req.prompt,
        "response": response_text,
        "metadata": {"model": model_name, "tps": tps}
    }
    await nodes_collection.insert_one(new_node)

    return {"response": response_text, "node_id": new_node_id, "tps": tps}