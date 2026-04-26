import os, time, json, uuid, logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from .models import Node, ChatRequest, MergeRequest, RootMergeRequest, NodeSummaryRequest, UpdateNodeRequest, UpdateConversationRequest, BulkDeleteRequest, ExportRequest
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

# Cache for Ollama loaded-model list — refreshed at most once every 10 seconds
_ollama_models_cache: list[str] = []
_ollama_models_cache_ts: float = 0.0
_OLLAMA_MODELS_TTL = 10.0


async def _get_ollama_loaded_models() -> list[str]:
    global _ollama_models_cache, _ollama_models_cache_ts
    now = time.time()
    if now - _ollama_models_cache_ts < _OLLAMA_MODELS_TTL:
        return _ollama_models_cache
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/ps")
            if resp.status_code == 200:
                _ollama_models_cache = [
                    m.get("name") or m.get("model", "")
                    for m in resp.json().get("models", [])
                    if m.get("name") or m.get("model")
                ]
                _ollama_models_cache_ts = now
    except Exception:
        pass
    return _ollama_models_cache

# --- HELPER: CONTEXT RECONSTRUCTION ---
async def get_history(last_node_id: str):
    """Walk the parent chain and return messages in chronological order."""
    chain = []
    curr = last_node_id
    while curr:
        node = await nodes_collection.find_one({"node_id": curr})
        if not node:
            break
        parent_ids = node.get("parent_ids") or []
        chain.append(node)
        curr = parent_ids[0] if parent_ids else None

    # chain is leaf→root, reverse to get root→leaf (chronological)
    chain.reverse()

    history = []
    for node in chain:
        if node.get("prompt") and node["prompt"] not in ("SYSTEM_MERGE_ACTION", "⎇ Merge Synthesis"):
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
        "active_nodes": await nodes_collection.count_documents({"pruned": {"$ne": True}})
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
    docs = await nodes_collection.find({"root_id": root_id, "pruned": {"$ne": True}}).to_list(1000)
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
    docs = await conversations_collection.find({}).sort("last_active_at", -1).to_list(1000)
    return [serialize_node(d) for d in docs]


# --- 6. GET SINGLE CONVERSATION ---
@router.get("/conversations/{root_id}")
async def get_conversation(root_id: str):
    doc = await conversations_collection.find_one({"root_id": root_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return serialize_node(doc)


# --- 7. UPDATE CONVERSATION TITLE ---
@router.put("/conversations/{root_id}")
async def update_conversation(root_id: str, req: UpdateConversationRequest):
    update_fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await conversations_collection.update_one(
        {"root_id": root_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
    doc = await conversations_collection.find_one({"root_id": root_id})
    return serialize_node(doc)


# --- 8. DELETE CONVERSATION AND ALL ITS NODES ---
@router.delete("/conversations/{root_id}")
async def delete_conversation(root_id: str):
    node_result = await nodes_collection.delete_many({"root_id": root_id})
    conv_result = await conversations_collection.delete_one({"root_id": root_id})
    return {
        "deleted_nodes": node_result.deleted_count,
        "deleted_conversation": conv_result.deleted_count,
    }


# --- 9. UPDATE A NODE ---
@router.put("/nodes/{node_id}")
async def update_node(node_id: str, req: UpdateNodeRequest):
    update_fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    # Flatten metadata updates so we don't overwrite the whole metadata object
    if "metadata" in update_fields:
        meta = update_fields.pop("metadata")
        for k, v in meta.items():
            update_fields[f"metadata.{k}"] = v
    result = await nodes_collection.update_one(
        {"node_id": node_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Node not found")
    doc = await nodes_collection.find_one({"node_id": node_id})
    return serialize_node(doc)


# --- 10. SOFT-DELETE (PRUNE) A NODE ---
@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str, hard: bool = Query(False, description="Hard delete removes from DB; soft delete marks pruned=True")):
    if hard:
        result = await nodes_collection.delete_one({"node_id": node_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"deleted": True, "node_id": node_id}
    else:
        result = await nodes_collection.update_one(
            {"node_id": node_id},
            {"$set": {"pruned": True}},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Node not found")
        return {"pruned": True, "node_id": node_id}


# --- 11. BULK DELETE NODES ---
@router.delete("/nodes")
async def bulk_delete_nodes(req: BulkDeleteRequest, hard: bool = Query(False)):
    if hard:
        result = await nodes_collection.delete_many({"node_id": {"$in": req.node_ids}})
        return {"deleted": result.deleted_count}
    else:
        result = await nodes_collection.update_many(
            {"node_id": {"$in": req.node_ids}},
            {"$set": {"pruned": True}},
        )
        return {"pruned": result.modified_count}


# --- 12. RESTORE A PRUNED NODE ---
@router.patch("/nodes/{node_id}/restore")
async def restore_node(node_id: str):
    result = await nodes_collection.update_one(
        {"node_id": node_id},
        {"$set": {"pruned": False}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Node not found")
    doc = await nodes_collection.find_one({"node_id": node_id})
    return serialize_node(doc)


# --- 13. REPARENT A NODE (move branch point) ---
@router.patch("/nodes/{node_id}/reparent")
async def reparent_node(node_id: str, new_parent_id: str = Query(...)):
    parent = await nodes_collection.find_one({"node_id": new_parent_id})
    if not parent:
        raise HTTPException(status_code=404, detail="New parent node not found")
    result = await nodes_collection.update_one(
        {"node_id": node_id},
        {"$set": {"parent_ids": [new_parent_id]}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Node not found")
    doc = await nodes_collection.find_one({"node_id": node_id})
    return serialize_node(doc)


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

        # Already summarised (including previously written fallbacks) — return as-is
        if existing_title and existing_subtitle:
            summaries.append(
                {
                    "node_id": node["node_id"],
                    "title": _limit_words(existing_title, 5),
                    "subtitle": _limit_words(existing_subtitle, 20),
                }
            )
            continue

        # Skip nodes that already failed — don't hammer Ollama while it's busy
        if existing_metadata.get("summary_failed"):
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
            async with httpx.AsyncClient(timeout=12.0) as client:
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

            # Success — persist and return
            await nodes_collection.update_one(
                {"node_id": node["node_id"]},
                {"$set": {
                    "metadata.summary_title": title,
                    "metadata.summary_subtitle": subtitle,
                    "metadata.summary_failed": False,
                }},
            )
            summaries.append({"node_id": node["node_id"], "title": title, "subtitle": subtitle})

        except Exception as e:
            logger.warning(f"Node summary generation failed for {node.get('node_id')}: {type(e).__name__}: {e}")
            # Mark as failed so we don't retry on the next poll — frontend can
            # clear this flag by explicitly requesting a refresh later
            await nodes_collection.update_one(
                {"node_id": node["node_id"]},
                {"$set": {"metadata.summary_failed": True}},
            )

    return {"summaries": summaries}

# --- MIGRATION: backfill created_at from ObjectId timestamp ---
@router.post("/conversations/backfill-timestamps")
async def backfill_conversation_timestamps():
    docs = await conversations_collection.find({}).to_list(1000)
    updated = 0
    for doc in docs:
        if doc.get("created_at"):
            continue  # already has a timestamp
        # Extract creation time from MongoDB ObjectId
        oid = doc.get("_id")
        if oid:
            ts = oid.generation_time.isoformat()
            await conversations_collection.update_one(
                {"_id": oid},
                {"$set": {"created_at": ts}},
            )
            updated += 1
    return {"backfilled": updated}

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


_STOPWORDS = {
    "the", "and", "are", "for", "that", "this", "with", "what", "how",
    "why", "who", "when", "where", "was", "were", "has", "have", "had",
    "not", "but", "from", "they", "their", "there", "been", "will",
    "can", "its", "you", "your", "all", "any", "one", "out", "about",
    "which", "would", "could", "should", "than", "then", "into", "also",
    "more", "some", "just", "like", "over", "such", "each", "most",
}


def _tokenize(text: str) -> set[str]:
    tokens = ''.join(c.lower() if c.isalnum() else ' ' for c in text).split()
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}


def _candidate_score(prompt_tokens: set[str], node: dict) -> int:
    node_prompt_tokens = _tokenize(node.get("prompt", ""))
    node_response_tokens = _tokenize(node.get("response", ""))
    # Prompt matches are worth 3x — topic word in the node's question is a
    # much stronger signal than it appearing somewhere in a long response
    prompt_overlap = len(prompt_tokens.intersection(node_prompt_tokens))
    response_overlap = len(prompt_tokens.intersection(node_response_tokens - node_prompt_tokens))
    return prompt_overlap * 3 + response_overlap


async def choose_auto_parent_id(req: ChatRequest) -> str | None:
    nodes = await nodes_collection.find({"root_id": req.root_id, "pruned": {"$ne": True}}).to_list(1000)
    if not nodes:
        return None

    # Exclude internal system marker nodes — they have no real content to score
    candidates = [
        n for n in nodes
        if n.get("prompt") != "SYSTEM_MERGE_ACTION"
    ]
    if not candidates:
        return None

    prompt_tokens = _tokenize(req.prompt)
    scored = sorted(
        candidates,
        key=lambda n: (_candidate_score(prompt_tokens, n), n.get("timestamp", "")),
        reverse=True,
    )

    winner = scored[0]
    top_score = _candidate_score(prompt_tokens, winner)

    for node in scored:
        score = _candidate_score(prompt_tokens, node)
        node_tokens = _tokenize(f"{node.get('prompt', '')} {node.get('response', '')}")
        matched = prompt_tokens.intersection(node_tokens)
        logger.info(
            f"  candidate score={score} matched={matched} "
            f"node_id={node.get('node_id')} "
            f"prompt={str(node.get('prompt', ''))[:50]!r}"
        )

    logger.info(
        f"Auto branching: prompt_tokens={prompt_tokens} "
        f"winner={winner.get('node_id')} score={top_score} "
        f"winner_prompt={str(winner.get('prompt', ''))[:60]!r}"
    )
    return winner.get("node_id")

# --- 5. STREAMING CHAT (Branching) ---
@router.post("/chat/stream")
async def stream_chat(req: ChatRequest):
    async def event_generator():
        full_response = ""
        resolved_parent_id = req.parent_id
        if req.auto_branching:
            resolved_parent_id = await choose_auto_parent_id(req)
            logger.info(f"Auto branching picked parent_id={resolved_parent_id} for root_id={req.root_id}")

        # Build context from the parent chain
        history = await get_history(resolved_parent_id) if resolved_parent_id else []
        history.insert(0, {
            "role": "system",
            "content": "Be concise. Answer directly without unnecessary preamble, repetition, or filler. Use markdown only when it genuinely helps clarity."
        })
        history.append({"role": "user", "content": req.prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", 
                json={"model": req.model, "messages": history, "stream": True}) as r:
                
                last_tps = 0.0
                async for line in r.aiter_lines():
                    if not line: continue
                    data = json.loads(line)
                    token = data.get("message", {}).get("content", "")
                    full_response += token
                    # Ollama reports eval_count / eval_duration (ns) on the final chunk
                    if data.get("eval_count") and data.get("eval_duration"):
                        last_tps = round(data["eval_count"] / (data["eval_duration"] / 1e9), 1)
                    yield f"data: {json.dumps({'token': token, 'tps': last_tps})}\n\n"
        
        p_ids = [resolved_parent_id] if resolved_parent_id and resolved_parent_id != "null" else []
        
        new_node = Node(
            parent_ids=p_ids,
            root_id=req.root_id,
            prompt=req.prompt,
            response=full_response,
            model_used=req.model,
            metadata={
                "model": req.model,
                "tps": last_tps,
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
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_active_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )
        else:
            # Update last_active_at on every subsequent message
            await conversations_collection.update_one(
                {"root_id": req.root_id},
                {"$set": {"last_active_at": datetime.now(timezone.utc).isoformat()}},
            )

        yield f"data: {json.dumps({'type': 'node_saved', 'node_id': new_node.node_id, 'parent_id': resolved_parent_id})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- 6. NODE MERGE (Intra-Root) ---
@router.post("/merge/nodes")
async def merge_nodes(req: MergeRequest):
    if len(req.node_ids) < 2 or len(req.node_ids) > 5:
        raise HTTPException(status_code=400, detail="Merge requires between 2 and 5 node_ids")

    nodes = await nodes_collection.find({"node_id": {"$in": req.node_ids}}).to_list(10)

    # Check if we actually found nodes
    if not nodes:
        raise HTTPException(status_code=400, detail="Merge requires between 2 and 5 node_ids")

    node_by_id = {n.get("node_id"): n for n in nodes}
    missing_ids = [nid for nid in req.node_ids if nid not in node_by_id]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Source nodes not found: {', '.join(missing_ids)}",
        )

    ordered_nodes = [node_by_id[nid] for nid in req.node_ids]

    # Build context from all selected nodes
    node_texts = []
    for i, n in enumerate(ordered_nodes):
        node_texts.append(f"Branch {i+1}:\nPrompt: {n.get('prompt', '')}\nResponse: {n.get('response', '')}")

    # Conflict detection only for 2-node merges (too complex for N-way)
    left = ordered_nodes[0]
    right = ordered_nodes[1]
    left_text = f"Prompt: {left.get('prompt', '')}\nResponse: {left.get('response', '')}"
    right_text = f"Prompt: {right.get('prompt', '')}\nResponse: {right.get('response', '')}"

    if not req.conflict_resolutions:
        conflict_scan_prompt = (
            "Find the most important direct contradiction between these two branches, if any.\n"
            "Return strict JSON array with at most 2 items, or [] if no real conflict.\n"
            'Schema: [{"id":"c1","left_claim":"<10 words>","right_claim":"<10 words>","why_conflict":"<10 words>"}]\n\n'
            f"LEFT:\n{left_text}\n\nRIGHT:\n{right_text}\n"
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

    context_str = "\n\n".join(node_texts)
    if req.conflict_resolutions:
        context_str += f"\n\n{resolution_context}"
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
        prompt="⎇ Merge Synthesis",
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

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/generate", 
                                 json={"model": req.model, "prompt": prompt, "stream": False})
        summary = resp.json().get("response") or "Root merge failed to generate summary."

    new_node = Node(
        parent_ids=[n['node_id'] for n in leaf_nodes],
        root_id=req.new_root_name,
        prompt=f"Root Merge: {', '.join(req.root_ids)}",
        response=summary,
        metadata={"type": "root_merge"}
    )
    await nodes_collection.insert_one(new_node.model_dump())
    return {"message": "Roots unified", "new_root": req.new_root_name, "node_id": new_node.node_id}


# ---------------------------------------------------------------------------
# AGENT-INTEGRATED ROUTES
# ---------------------------------------------------------------------------

# --- A1. GRAPH INTEGRITY CHECK ---
@router.get("/graph-integrity/{root_id}")
async def check_graph_integrity(root_id: str, include_pruned: bool = Query(False)):
    """
    Validate the DAG for a conversation: detect cycles, orphan nodes,
    and parent-child mismatches.  Runs entirely in-process against MongoDB.
    """
    query: dict = {"root_id": root_id}
    if not include_pruned:
        query["pruned"] = {"$ne": True}
    raw_nodes = await nodes_collection.find(query).to_list(5000)

    # Build node map with normalised parent_id / children_ids
    nodes: dict[str, dict] = {}
    for n in raw_nodes:
        nid = n.get("node_id")
        if not nid:
            continue
        parent_ids = n.get("parent_ids") or []
        nodes[nid] = {
            "node_id": nid,
            "parent_id": parent_ids[0] if parent_ids else None,
            "parent_ids": parent_ids,
            "children_ids": [],
        }

    # Reconstruct children_ids from parent_ids
    for node in nodes.values():
        for pid in node["parent_ids"]:
            if pid in nodes and node["node_id"] not in nodes[pid]["children_ids"]:
                nodes[pid]["children_ids"].append(node["node_id"])

    orphan_nodes = 0
    mismatches = 0
    for node in nodes.values():
        pid = node["parent_id"]
        if pid and pid not in nodes:
            orphan_nodes += 1
        for cid in node["children_ids"]:
            child = nodes.get(cid)
            if not child:
                mismatches += 1
            elif child["parent_id"] != node["node_id"]:
                mismatches += 1

    # Iterative DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    colors = {nid: WHITE for nid in nodes}
    cycles = 0

    def dfs(start: str):
        nonlocal cycles
        stack = [(start, False)]
        while stack:
            nid, returning = stack.pop()
            if returning:
                colors[nid] = BLACK
                continue
            if colors[nid] != WHITE:
                continue
            colors[nid] = GRAY
            stack.append((nid, True))
            for cid in nodes[nid]["children_ids"]:
                if cid not in nodes:
                    continue
                if colors[cid] == GRAY:
                    cycles += 1
                elif colors[cid] == WHITE:
                    stack.append((cid, False))

    for nid in nodes:
        if colors[nid] == WHITE:
            dfs(nid)

    valid = cycles == 0 and orphan_nodes == 0 and mismatches == 0
    return {
        "root_id": root_id,
        "valid": valid,
        "total_nodes_checked": len(nodes),
        "cycles_detected": cycles,
        "orphan_nodes": orphan_nodes,
        "parent_child_mismatches": mismatches,
        "message": "Graph is valid" if valid else "Graph integrity violations found",
    }


# --- A2. EXPORT CONVERSATION ---
@router.post("/export")
async def export_conversation(req: ExportRequest):
    """
    Export all nodes for a conversation in the requested format.
    Returns the content inline (as a string in JSON, or as a file download
    for csv/html/markdown).
    """
    nodes = await nodes_collection.find(
        {"root_id": req.root_id, "pruned": {"$ne": True}}
    ).sort("_id", 1).to_list(5000)
    for n in nodes:
        n.pop("_id", None)

    conv = await conversations_collection.find_one({"root_id": req.root_id})
    if conv:
        conv.pop("_id", None)
    title = (conv or {}).get("title") or req.root_id
    exported_at = datetime.now(timezone.utc).isoformat()

    fmt = req.format.lower()

    if fmt == "json":
        payload = json.dumps(
            {"conversation": conv or {}, "nodes": nodes, "exported_at": exported_at},
            indent=2, default=str,
        )
        return {"format": "json", "items_exported": len(nodes), "data": payload}

    if fmt == "markdown":
        lines = [f"# {title}\n"]
        for n in sorted(nodes, key=lambda x: x.get("timestamp", "")):
            prompt = n.get("prompt", "")
            response = n.get("response", "")
            if prompt and prompt not in ("⎇ Merge Synthesis",):
                lines.append(f"**User:** {prompt}\n")
            if response:
                lines.append(f"**AI:** {response}\n")
            if req.include_metadata and n.get("metadata"):
                lines.append(f"*metadata: {n['metadata']}*\n")
            lines.append("---\n")
        lines.append(f"\n*Exported {exported_at}*")
        content = "\n".join(lines)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{req.root_id}.md"'},
        )

    if fmt == "csv":
        import csv as csv_mod
        import io
        out = io.StringIO()
        writer = csv_mod.writer(out)
        writer.writerow(["node_id", "parent_ids", "prompt", "response", "model_used", "timestamp"])
        for n in sorted(nodes, key=lambda x: x.get("timestamp", "")):
            writer.writerow([
                n.get("node_id", ""),
                ",".join(n.get("parent_ids", [])),
                n.get("prompt", ""),
                n.get("response", ""),
                n.get("model_used", ""),
                n.get("timestamp", ""),
            ])
        return Response(
            content=out.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{req.root_id}.csv"'},
        )

    if fmt == "html":
        rows = []
        for n in sorted(nodes, key=lambda x: x.get("timestamp", "")):
            p = (n.get("prompt") or "").replace("<", "&lt;").replace(">", "&gt;")
            r = (n.get("response") or "").replace("<", "&lt;").replace(">", "&gt;")
            rows.append(
                f"<div class='node'>"
                f"<p><strong>User:</strong> {p}</p>"
                f"<p><strong>AI:</strong> {r}</p>"
                f"</div>"
            )
        html = (
            f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>body{{font-family:sans-serif;max-width:800px;margin:auto;padding:2rem}}"
            f".node{{border-bottom:1px solid #eee;padding:1rem 0}}</style></head>"
            f"<body><h1>{title}</h1>{''.join(rows)}"
            f"<p><em>Exported {exported_at}</em></p></body></html>"
        )
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{req.root_id}.html"'},
        )

    raise HTTPException(status_code=400, detail=f"Unsupported format: {req.format}. Use json, markdown, csv, or html.")


# --- A3. AGENT TELEMETRY (GPU + Ollama model list) ---
@router.get("/agent-telemetry")
async def get_agent_telemetry():
    """
    Extended telemetry: reuses /telemetry GPU stats and adds the list of
    currently loaded Ollama models from /api/ps plus derived alerts.
    """
    # Reuse the existing telemetry logic directly
    stats: dict = dict(await get_telemetry())

    # Ollama loaded models (cached, refreshes every 10s)
    loaded_models = await _get_ollama_loaded_models()

    stats["loaded_models"] = loaded_models

    # Derive alerts
    alerts: list[str] = []
    if stats.get("temp_c") is not None and stats["temp_c"] > 85:
        alerts.append(f"GPU temperature critical: {stats['temp_c']}°C")
    if stats.get("vram_gb") is not None and stats.get("vram_total_gb") is not None:
        pct = stats["vram_gb"] / stats["vram_total_gb"] * 100
        if pct > 90:
            alerts.append(f"VRAM usage high: {stats['vram_gb']:.1f} / {stats['vram_total_gb']:.1f} GB")
    stats["alerts"] = alerts

    return stats
