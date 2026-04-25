# app/routes.py
from .models import MessageNode
from .database import nodes_collection

@router.post("/chat")
async def handle_chat(req: ChatRequest):
    # 1. Determine the root_id 
    # If this is the first message, the frontend generates a new root_id.
    # If it's a branch, the frontend sends the existing root_id.
    
    # 2. Reconstruct History for the AI (The "Git Walk")
    # This ensures the AI knows what happened in THIS specific branch
    context = ""
    if req.parent_id:
        history = []
        curr_id = req.parent_id
        while curr_id:
            past_node = await nodes_collection.find_one({"node_id": curr_id})
            if not past_node: break
            history.insert(0, f"{past_node['role']}: {past_node['content']}")
            curr_id = past_node.get("parent_id")
        context = "\n".join(history)

    # 3. Call your Ollama Logic (Your existing Step 10 code here)
    # response_text, tps = await call_ollama(req.prompt, context, req.model)

    # 4. Save the User's Message Node
    user_node = MessageNode(
        parent_id=req.parent_id,
        root_id=req.root_id,
        role="user",
        content=req.prompt,
        metadata={"model": req.model, "is_local": True}
    )
    await nodes_collection.insert_one(user_node.dict())

    # 5. Save the AI's Response Node (the parent is the user_node we just made)
    ai_node = MessageNode(
        parent_id=user_node.node_id,
        root_id=req.root_id,
        role="assistant",
        content=response_text,
        metadata={"model": req.model, "is_local": True, "tps": tps}
    )
    await nodes_collection.insert_one(ai_node.dict())

    return {
        "response": response_text,
        "node_id": ai_node.node_id, # Frontend needs this to "continue" the chat
        "root_id": req.root_id
    }
    
@router.get("/tree/{root_id}")
async def get_tree(root_id: str):
    # Fetch all messages belonging to this tree
    cursor = nodes_collection.find({"root_id": root_id})
    all_nodes = await cursor.to_list(length=1000)
    
    # We return them as a list; the Frontend (React Flow/D3) will connect the 
    # dots using the parent_id fields.
    return {"nodes": all_nodes}