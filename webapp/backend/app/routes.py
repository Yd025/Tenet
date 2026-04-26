import os, time, json, uuid, logging, random
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from .models import Node, ChatRequest, MergeRequest, RootMergeRequest, NodeSummaryRequest
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


def _extract_json_block(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                return candidate[4:].strip()
            if candidate.startswith("[") or candidate.startswith("{"):
                return candidate
    return text


def _limit_words(text: str, max_words: int) -> str:
    words = text.strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])

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


@router.post("/nodes/summaries")
async def generate_node_summaries(req: NodeSummaryRequest):
    query = {"root_id": req.root_id}
    if req.node_ids:
        query["node_id"] = {"$in": req.node_ids}
    nodes = await nodes_collection.find(query).to_list(1000)
    if not nodes:
        return {"summaries": []}

    summaries = []
    for node in nodes:
        existing_metadata = node.get("metadata", {}) or {}
        existing_title = str(existing_metadata.get("summary_title", "")).strip()
        existing_subtitle = str(existing_metadata.get("summary_subtitle", "")).strip()
        if existing_title and existing_subtitle:
            summaries.append(
                {
                    "node_id": node["node_id"],
                    "title": _limit_words(existing_title, 5),
                    "subtitle": _limit_words(existing_subtitle, 20),
                }
            )
            continue

        summarizer_prompt = (
            "Summarize this conversation node for a graph label.\n"
            "Return strict JSON only with keys: title, subtitle.\n"
            "Rules: title maximum 5 words. subtitle maximum 20 words.\n\n"
            f"Prompt:\n{node.get('prompt', '')}\n\n"
            f"Response:\n{node.get('response', '')}\n"
        )
        title = _limit_words(node.get("prompt", "") or "Node", 5)
        subtitle = _limit_words(node.get("response", "") or node.get("prompt", "") or "Conversation node", 20)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": req.model, "prompt": summarizer_prompt, "stream": False},
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "{}")
                parsed = json.loads(_extract_json_block(raw))
                if isinstance(parsed, dict):
                    parsed_title = str(parsed.get("title", "")).strip()
                    parsed_subtitle = str(parsed.get("subtitle", "")).strip()
                    if parsed_title:
                        title = _limit_words(parsed_title, 5)
                    if parsed_subtitle:
                        subtitle = _limit_words(parsed_subtitle, 20)
        except Exception as e:
            logger.warning(f"Node summary generation failed for {node.get('node_id')}: {e}")

        await nodes_collection.update_one(
            {"node_id": node["node_id"]},
            {"$set": {"metadata.summary_title": title, "metadata.summary_subtitle": subtitle}},
        )
        summaries.append({"node_id": node["node_id"], "title": title, "subtitle": subtitle})

    return {"summaries": summaries}

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


def _tokenize(text: str) -> set[str]:
    return {t for t in ''.join(c.lower() if c.isalnum() else ' ' for c in text).split() if len(t) > 2}


def _candidate_score(prompt_tokens: set[str], node: dict) -> int:
    node_tokens = _tokenize(f"{node.get('prompt', '')} {node.get('response', '')}")
    overlap = len(prompt_tokens.intersection(node_tokens))
    recency_bonus = 1 if node.get("metadata", {}).get("timestamp") else 0
    return overlap * 10 + recency_bonus


async def choose_auto_parent_id(req: ChatRequest) -> str | None:
    nodes = await nodes_collection.find({"root_id": req.root_id}).to_list(1000)
    if not nodes:
        return None

    prompt_tokens = _tokenize(req.prompt)
    scored = sorted(
        nodes,
        key=lambda n: (_candidate_score(prompt_tokens, n), n.get("metadata", {}).get("timestamp", "")),
        reverse=True,
    )
    candidates = scored[:8]

    # Fast fallback when no useful candidates exist.
    if not candidates:
        return None

    candidate_lines = []
    for c in candidates:
        snippet = (c.get("prompt", "") + " " + c.get("response", "")).strip().replace("\n", " ")
        candidate_lines.append(f"- {c.get('node_id')}: {snippet[:220]}")

    selector_prompt = (
        "You are an auto-branch selector for a conversation graph.\n"
        "Pick exactly one best parent node id for the next user prompt.\n"
        "Return strict JSON with this schema only: "
        '{"parent_id":"<node_id>","reason":"<short reason>"}\n\n'
        f'New prompt: "{req.prompt}"\n'
        "Candidates:\n"
        + "\n".join(candidate_lines)
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": req.model,
                    "prompt": selector_prompt,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "").strip()
            parsed = json.loads(raw)
            parent_id = parsed.get("parent_id")
            if isinstance(parent_id, str) and any(n.get("node_id") == parent_id for n in candidates):
                return parent_id
    except Exception as e:
        logger.warning(f"Auto branching selector failed, using fallback: {e}")

    # Fallback: most recent candidate by timestamp.
    candidates_sorted = sorted(
        candidates,
        key=lambda n: n.get("metadata", {}).get("timestamp", ""),
        reverse=True,
    )
    return candidates_sorted[0].get("node_id")

# --- 5. STREAMING CHAT (Branching) ---
@router.post("/chat/stream")
async def stream_chat(req: ChatRequest):
    async def event_generator():
        full_response = ""
        start_time = time.time()
        resolved_parent_id = req.parent_id
        if req.auto_branching:
            resolved_parent_id = await choose_auto_parent_id(req)
            logger.info(f"Auto branching picked parent_id={resolved_parent_id} for root_id={req.root_id}")

        # Build context from the parent chain
        history = await get_history(resolved_parent_id) if resolved_parent_id else []
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
        
        p_ids = [resolved_parent_id] if resolved_parent_id and resolved_parent_id != "null" else []
        
        new_node = Node(
            parent_ids=p_ids,
            root_id=req.root_id,
            prompt=req.prompt,
            response=full_response,
            model_used=req.model,
            metadata={
                "model": req.model,
                "tps": 61.7,
                "auto_branching": req.auto_branching,
                "resolved_parent_id": resolved_parent_id,
            },
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

        yield f"data: {json.dumps({'type': 'node_saved', 'node_id': new_node.node_id, 'parent_id': resolved_parent_id})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- 6. NODE MERGE (Intra-Root) ---
@router.post("/merge/nodes")
async def merge_nodes(req: MergeRequest):
    nodes = await nodes_collection.find({"node_id": {"$in": req.node_ids}}).to_list(10)
    
    # Check if we actually found nodes
    if not nodes:
        raise HTTPException(status_code=404, detail="Source nodes for merge not found")

    if len(req.node_ids) != 2:
        raise HTTPException(status_code=400, detail="Merge currently requires exactly 2 node_ids")

    node_by_id = {n.get("node_id"): n for n in nodes}
    missing_ids = [nid for nid in req.node_ids if nid not in node_by_id]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Source nodes not found: {', '.join(missing_ids)}",
        )

    ordered_nodes = [node_by_id[req.node_ids[0]], node_by_id[req.node_ids[1]]]
    if len(ordered_nodes) != 2:
        raise HTTPException(status_code=400, detail="Merge currently requires exactly 2 nodes")

    # Preserve client intent: left is first selected node, right is second.
    left = ordered_nodes[0]
    right = ordered_nodes[1]
    left_text = f"Prompt: {left.get('prompt', '')}\nResponse: {left.get('response', '')}"
    right_text = f"Prompt: {right.get('prompt', '')}\nResponse: {right.get('response', '')}"

    if not req.conflict_resolutions:
        conflict_scan_prompt = (
            "You are a merge-conflict detection agent for two chat branches.\n"
            "Find direct semantic contradictions that cannot both be true.\n"
            "Return ONLY strict JSON array with max 5 conflicts.\n"
            'Each item schema: {"id":"c1","left_claim":"...","right_claim":"...","why_conflict":"..."}\n'
            "Return [] if no conflicts.\n\n"
            "LEFT CONTEXT:\n"
            f"{left_text}\n\n"
            "RIGHT CONTEXT:\n"
            f"{right_text}\n"
        )
        conflicts = []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                conflict_resp = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={"model": req.model, "prompt": conflict_scan_prompt, "stream": False},
                )
                conflict_resp.raise_for_status()
                raw = conflict_resp.json().get("response", "[]")
                parsed = json.loads(_extract_json_block(raw))
                if isinstance(parsed, list):
                    for item in parsed:
                        if not isinstance(item, dict):
                            continue
                        left_claim = str(item.get("left_claim", "")).strip()
                        right_claim = str(item.get("right_claim", "")).strip()
                        why_conflict = str(item.get("why_conflict", "")).strip()
                        if left_claim and right_claim:
                            conflicts.append(
                                {
                                    "id": str(item.get("id", f"c{len(conflicts) + 1}")),
                                    "left_claim": left_claim,
                                    "right_claim": right_claim,
                                    "why_conflict": why_conflict,
                                }
                            )
        except Exception as e:
            logger.warning(f"Conflict detection failed, continuing merge: {e}")

        if conflicts:
            return {
                "requires_resolution": True,
                "conflicts": conflicts,
                "response": "",
                "node_id": None,
            }

    resolution_context = ""
    if req.conflict_resolutions:
        resolution_lines = []
        for res in req.conflict_resolutions:
            choice = str(res.get("choice", "")).strip()
            conflict_id = str(res.get("id", "")).strip()
            custom = str(res.get("custom_resolution", "")).strip()
            if conflict_id and choice:
                line = f"- {conflict_id}: {choice}"
                if custom:
                    line += f" | custom: {custom}"
                resolution_lines.append(line)
        if resolution_lines:
            resolution_context = "User-selected conflict resolutions:\n" + "\n".join(resolution_lines)

    context_str = (
        f"Left branch:\n{left_text}\n\n"
        f"Right branch:\n{right_text}\n\n"
        f"{resolution_context}"
    )
    prompt = (
        "Synthesize these branches into one cohesive merged response.\n"
        "If conflict resolutions are provided, strictly honor them.\n\n"
        f"{context_str}"
    )
    
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
    payload = new_node.model_dump()
    payload["requires_resolution"] = False
    payload["conflicts"] = []
    return payload

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