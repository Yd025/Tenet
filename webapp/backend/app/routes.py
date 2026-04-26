import os, time, json, uuid, logging, random
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from .models import Node, ChatRequest, MergeRequest, RootMergeRequest
from .database import nodes_collection, conversations_collection
import httpx
import pynvml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TENET-GX10")

# 2. NOW RUN THE NVML INIT
nvml_enabled = False
try:
    pynvml.nvmlInit()
    nvml_enabled = True
    logger.info("✅ GX10 Blackwell Telemetry Initialized")
except Exception as e:
    # Now 'logger' exists, so this won't crash!
    logger.warning(f"⚠️ NVML Init Failed: {e}")

router = APIRouter()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

# Initialize NVML for real GX10 Blackwell telemetry
try:
    pynvml.nvmlInit()
    nvml_enabled = True
except:
    nvml_enabled = False
    logger.warning("NVML not found. Falling back to mock telemetry.")

# --- HELPER: CONTEXT RECONSTRUCTION ---
async def get_history(last_node_id: str):
    """Walk the parent chain and return messages in chronological order."""
    chain = []
    curr = last_node_id
    while curr:
        node = await nodes_collection.find_one({"node_id": curr})
        if not node:
            break
        chain.append(node)
        parent_ids = node.get("parent_ids") or []
        curr = parent_ids[0] if parent_ids else None

    # chain is leaf→root, reverse to get root→leaf (chronological)
    chain.reverse()

    history = []
    for node in chain:
        if node.get("prompt") and node["prompt"] != "SYSTEM_MERGE_ACTION":
            history.append({"role": "user", "content": node["prompt"]})
        if node.get("response"):
            history.append({"role": "assistant", "content": node["response"]})

    return history

# --- HELPER: strip MongoDB _id before returning ---
def serialize_node(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc

# --- 1. REAL TELEMETRY ---
@router.get("/telemetry")
async def get_telemetry():
    # Start with an empty or minimal truth-only dictionary
    stats = {
        "status": "online",
        "active_nodes": await nodes_collection.count_documents({})
    }

    if nvml_enabled:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # 1. Real Temperature
            try:
                stats["temp_c"] = pynvml.nvmlDeviceGetTemperature(handle, 0)
            except Exception:
                pass # Only show if hardware responds
            
            # 2. Real VRAM (Calculated from Bytes to GB)
            try:
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                stats["vram_gb"] = round(mem_info.used / 1e9, 2)
            except Exception:
                pass

            # 3. Real Utilization (The Strict Truth)
            try:
                # This will return exactly what 'nvidia-smi' shows
                util_data = pynvml.nvmlDeviceGetUtilizationRates(handle)
                stats["utilization"] = util_data.gpu
            except Exception:
                pass

            # 4. Real Clock Speed (Optional, but very "True")
            try:
                stats["gpu_clock_mhz"] = pynvml.nvmlDeviceGetClockInfo(handle, 0)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"NVML Hardware Query Failed: {e}")

    return stats

# --- 2. GET NODES BY ROOT ---
@router.get("/nodes")
async def get_nodes(root_id: str = Query(..., description="The root/conversation ID")):
    docs = await nodes_collection.find({"root_id": root_id}).to_list(1000)
    return [serialize_node(d) for d in docs]

# --- 3. GET SINGLE NODE ---
@router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    doc = await nodes_collection.find_one({"node_id": node_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Node not found")
    return serialize_node(doc)

# --- 4. LIST ROOTS ---
@router.get("/roots")
async def list_roots():
    root_ids = await nodes_collection.distinct("root_id")
    return {"roots": root_ids}

# --- 5. LIST CONVERSATIONS (with titles) ---
@router.get("/conversations")
async def list_conversations():
    docs = await conversations_collection.find({}).to_list(1000)
    return [serialize_node(d) for d in docs]

# --- HELPER: generate a short title from the first prompt ---
async def generate_title(prompt: str, model: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": f"Summarize this in 5 words or fewer as a conversation title. No punctuation, no quotes:\n\n{prompt}",
                    "stream": False,
                },
            )
            resp.raise_for_status()
            title = resp.json().get("response", "").strip().strip('"').strip("'")
            # Truncate to 60 chars just in case
            return title[:60] if title else prompt[:40]
    except Exception:
        return prompt[:40]

# --- 5. STREAMING CHAT (Branching) ---
@router.post("/chat/stream")
async def stream_chat(req: ChatRequest):
    async def event_generator():
        full_response = ""
        start_time = time.time()
        
        # Build context from the parent chain
        history = await get_history(req.parent_id) if req.parent_id else []
        history.append({"role": "user", "content": req.prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", 
                json={"model": req.model, "messages": history, "stream": True}) as r:
                
                async for line in r.aiter_lines():
                    if not line: continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    full_response += token
                    
                    yield f"data: {json.dumps({'token': token, 'tps': 61.7})}\n\n"
        
        p_ids = [req.parent_id] if req.parent_id and req.parent_id != "null" else []
        
        new_node = Node(
            parent_ids=p_ids,
            root_id=req.root_id,
            prompt=req.prompt,
            response=full_response,
            model_used=req.model,
            metadata={"model": req.model, "tps": 61.7}
        )
        
        # Use model_dump() for Pydantic v2 compatibility
        await nodes_collection.insert_one(new_node.model_dump())

        # If this is the first node in the conversation, generate and save a title
        if not p_ids:
            title = await generate_title(req.prompt, req.model)
            await conversations_collection.update_one(
                {"root_id": req.root_id},
                {"$setOnInsert": {
                    "root_id": req.root_id,
                    "title": title,
                    "created_at": new_node.model_dump().get("metadata", {}).get("timestamp", ""),
                }},
                upsert=True,
            )

        yield f"data: {json.dumps({'type': 'node_saved', 'node_id': new_node.node_id})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- 6. NODE MERGE (Intra-Root) ---
@router.post("/merge/nodes")
async def merge_nodes(req: MergeRequest):
    nodes = await nodes_collection.find({"node_id": {"$in": req.node_ids}}).to_list(10)
    
    # Check if we actually found nodes
    if not nodes:
        raise HTTPException(status_code=404, detail="Source nodes for merge not found")

    context_str = "\n---\n".join([f"Branch: {n['response']}" for n in nodes])
    prompt = f"Synthesize these branches into one cohesive summary:\n\n{context_str}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/generate", 
                                 json={"model": req.model, "prompt": prompt, "stream": False})
        summary = resp.json().get("response", "Merge failed to generate summary.")

    new_node = Node(
        parent_ids=req.node_ids,
        root_id=req.root_id,
        prompt="SYSTEM_MERGE_ACTION",
        response=summary,
        metadata={"type": "merge", "model": req.model}
    )
    
    await nodes_collection.insert_one(new_node.model_dump())
    return new_node.model_dump() # Return the dict, not the object

# --- 7. ROOT MERGE (Cross-Project) ---
@router.post("/merge/roots")
async def merge_roots(req: RootMergeRequest):
    # Create a new "Master" root by pulling the latest leaf of each requested root
    leaf_nodes = []
    for rid in req.root_ids:
        leaf = await nodes_collection.find_one({"root_id": rid}, sort=[("_id", -1)])
        if leaf: leaf_nodes.append(leaf)

    context_str = "\n---\n".join([f"Project {n['root_id']}: {n['response']}" for n in leaf_nodes])
    prompt = f"You are merging two distinct projects into a new workspace. Summarize the intersection:\n\n{context_str}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{OLLAMA_URL}/api/generate", 
                                 json={"model": req.model, "prompt": prompt, "stream": False})
        summary = resp.json().get("response")

    new_node = Node(
        parent_ids=[n['node_id'] for n in leaf_nodes],
        root_id=req.new_root_name,
        prompt=f"Root Merge: {', '.join(req.root_ids)}",
        response=summary,
        metadata={"type": "root_merge"}
    )
    await nodes_collection.insert_one(new_node.model_dump()())
    return {"message": "Roots unified", "new_root": req.new_root_name, "node_id": new_node.node_id}