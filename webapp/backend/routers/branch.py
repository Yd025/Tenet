from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

router = APIRouter()

# In-memory store — swap for MongoDB Atlas later
_branches: dict[str, dict] = {}

class BranchRequest(BaseModel):
    node_id: str
    label: str

class BranchResponse(BaseModel):
    branch_id: str

class MergeRequest(BaseModel):
    node_id_a: str
    node_id_b: str

class MergeResponse(BaseModel):
    response: str
    node_id: str

@router.post("/branch", response_model=BranchResponse)
async def create_branch(req: BranchRequest):
    branch_id = str(uuid.uuid4())
    _branches[branch_id] = {"node_id": req.node_id, "label": req.label}
    return BranchResponse(branch_id=branch_id)

@router.post("/merge", response_model=MergeResponse)
async def merge_branches(req: MergeRequest):
    import httpx
    from routers.chat import OLLAMA_URL, MODEL_MAP
    # Simple merge: ask Ollama to synthesize context from both branch contexts
    synthesis_prompt = (
        f"You are synthesizing insights from two conversation branches.\n"
        f"Branch A node: {req.node_id_a}\n"
        f"Branch B node: {req.node_id_b}\n"
        f"Create a brief synthesis commit message summarizing what both branches explored."
    )
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL_MAP["deepseek"],
                    "prompt": synthesis_prompt,
                    "stream": False,
                }
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "Synthesis commit: merged two conversation branches.")
    except Exception:
        response_text = "Synthesis commit: merged two conversation branches."

    return MergeResponse(
        response=response_text,
        node_id=str(uuid.uuid4()),
    )

@router.delete("/node/{node_id}")
async def prune_node(node_id: str):
    # Pruning is handled client-side in Zustand store; backend acknowledges
    return {"pruned": node_id}

@router.get("/models")
async def get_models():
    return ["deepseek", "qwen"]
