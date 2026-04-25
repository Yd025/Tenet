from uagents import Agent, Context
from protocols.chat_protocol import ChatRequest, ChatResponse, chat_protocol, ExecutionLocation
from protocols.branch_protocol import BranchRequest, BranchResponse, branch_protocol, BranchAction
from config.agent_config import AgentConfig
from utils.local_runtime import dag_store, memory_store, router, capability_registry
import time

MODEL_MAP = {
    "deepseek": "deepseek-r1:latest",
    "qwen": "qwen2.5:latest",
}


async def call_ollama(prompt: str, model: str, is_sensitive: bool) -> dict:
    """Call Ollama REST API directly for local model inference.

    Args:
        prompt: The user prompt to send to the model.
        model: Model key ("deepseek", "qwen") or a full Ollama model name.
        is_sensitive: If True, forces use of deepseek-r1:latest for on-device privacy.

    Returns:
        dict with keys: response (str), tps (float), model_used (str)
    """
    if is_sensitive:
        model_name = MODEL_MAP["deepseek"]
    else:
        model_name = MODEL_MAP.get(model, model)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                }
            )
            resp.raise_for_status()
            data = resp.json()

        response_text = data.get("response", "")
        eval_duration = data.get("eval_duration", 1)  # nanoseconds
        eval_count = data.get("eval_count", 1)
        tps = round(eval_count / (eval_duration / 1e9), 1) if eval_duration > 0 else 0.0

        return {"response": response_text, "tps": tps, "model_used": model_name}

    except Exception as e:
        return {"response": f"Agent unavailable: {str(e)}", "tps": 0.0, "model_used": model_name}


class TenetOrchestrator:
    """Main orchestrator agent - Routes requests to specialist agents"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the orchestrator agent
        self.agent = Agent(
            name="tenet-orchestrator",
            seed=self.config.ORCHESTRATOR_SEED,
            port=self.config.ORCHESTRATOR_PORT
        )
        
        self.performance_metrics = {
            "total_requests": 0,
            "local_requests": 0,
            "cloud_requests": 0,
            "avg_response_time_ms": 0,
            "error_count": 0
        }
        
        # Setup protocol handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup message handlers for the orchestrator"""
        
        @chat_protocol.on_message(model=ChatRequest)
        async def handle_chat_request(ctx: Context, sender: str, msg: ChatRequest):
            """Main chat request handler - routes to appropriate specialist agents"""
            
            start_time = time.time()
            self.performance_metrics["total_requests"] += 1
            
            try:
                privacy_assessment = router.analyze_privacy(msg.prompt, msg.privacy_level.value)
                execution_location = router.choose_execution_location(privacy_assessment["privacy_level"])
                response_data = self.generate_local_response(msg, privacy_assessment)
                if execution_location == "local":
                    self.performance_metrics["local_requests"] += 1
                else:
                    self.performance_metrics["cloud_requests"] += 1

                node = dag_store.add_node(
                    conversation_id=msg.conversation_id,
                    branch_id=msg.branch_id,
                    parent_id=(msg.context or {}).get("parent_id") if msg.context else None,
                    prompt=msg.prompt,
                    response=response_data["response"],
                    model_used=response_data["model_used"],
                    execution_location=ExecutionLocation.LOCAL.value,
                    metadata=response_data["metadata"],
                )
                memory_store.store(
                    context=node,
                    conversation_id=msg.conversation_id,
                    branch_id=node.get("branch_id"),
                )
                
                # Step 4: Calculate performance metrics
                response_time = (time.time() - start_time) * 1000
                self.performance_metrics["avg_response_time_ms"] = (
                    (self.performance_metrics["avg_response_time_ms"] * (self.performance_metrics["total_requests"] - 1) + response_time) /
                    self.performance_metrics["total_requests"]
                )
                
                response_data["performance_metrics"] = {
                    "response_time_ms": response_time,
                    "total_requests": self.performance_metrics["total_requests"],
                    "avg_response_time_ms": self.performance_metrics["avg_response_time_ms"]
                }
                
                await ctx.send(sender, ChatResponse(**response_data))
                
            except Exception as e:
                self.performance_metrics["error_count"] += 1
                error_response = {
                    "response": f"I apologize, but I encountered an error: {str(e)}",
                    "model_used": "error",
                    "execution_location": ExecutionLocation.LOCAL,
                    "conversation_id": msg.conversation_id,
                    "branch_id": msg.branch_id,
                    "metadata": {"error": True, "error_type": str(type(e).__name__)},
                    "performance_metrics": {"error": True}
                }
                await ctx.send(sender, ChatResponse(**error_response))
        
        @branch_protocol.on_message(model=BranchRequest)
        async def handle_branch_request(ctx: Context, sender: str, msg: BranchRequest):
            """Handle conversation branching requests"""
            
            try:
                branch_result = self.handle_branch_action(msg)
                
                response = BranchResponse(
                    success=branch_result["success"],
                    action=msg.action,
                    new_branch_id=branch_result.get("branch_id"),
                    new_node_id=branch_result.get("node_id"),
                    branches=branch_result.get("branches"),
                    message=branch_result["message"]
                )
                
                await ctx.send(sender, response)
                
            except Exception as e:
                error_response = BranchResponse(
                    success=False,
                    action=msg.action,
                    new_branch_id="",
                    new_node_id="",
                    branches=None,
                    message=f"Error creating branch: {str(e)}"
                )
                await ctx.send(sender, error_response)
    
    def generate_local_response(self, msg: ChatRequest, privacy_assessment: dict) -> dict:
        selected_agent = self.select_specialist_agent(msg.prompt, privacy_assessment["privacy_level"])
        response = (
            f"Local-only mode response for '{msg.prompt[:80]}'. "
            "This response is generated without outbound service calls."
        )
        return {
            "response": response,
            "model_used": self.config.DEFAULT_LOCAL_MODEL,
    async def analyze_privacy(self, msg: ChatRequest) -> dict:
        """Analyze privacy level of the request"""
        
        # Check explicit privacy level
        if msg.privacy_level == PrivacyLevel.SENSITIVE:
            return {"level": PrivacyLevel.SENSITIVE, "confidence": 1.0}
        
        # Analyze content for sensitive information
        prompt_lower = msg.prompt.lower()
        has_sensitive = any(keyword in prompt_lower for keyword in self.config.SENSITIVE_KEYWORDS)
        
        if has_sensitive:
            return {"level": PrivacyLevel.SENSITIVE, "confidence": 0.9}
        elif msg.privacy_level == PrivacyLevel.PRIVATE:
            return {"level": PrivacyLevel.PRIVATE, "confidence": 1.0}
        else:
            return {"level": PrivacyLevel.PUBLIC, "confidence": 1.0}
    
    async def route_to_local_model(self, msg: ChatRequest) -> dict:
        """Route request to local Ollama model for sensitive/private data.

        Uses call_ollama() which POSTs to http://localhost:11434/api/generate.
        Sensitive requests are always routed to deepseek-r1:latest.
        Falls back to cloud if Ollama is unavailable.
        """
        is_sensitive = (msg.privacy_level == PrivacyLevel.SENSITIVE)
        model_key = getattr(msg, "model", self.config.DEFAULT_LOCAL_MODEL)
        ollama_result = await call_ollama(msg.prompt, model_key, is_sensitive)

        if ollama_result["response"].startswith("Agent unavailable:"):
            print(f"Ollama unavailable: {ollama_result['response']}, falling back to cloud")
            return await self.route_to_cloud_model(msg)

        return {
            "response": ollama_result["response"],
            "model_used": ollama_result["model_used"],
            "execution_location": ExecutionLocation.LOCAL,
            "conversation_id": msg.conversation_id,
            "branch_id": msg.branch_id,
            "metadata": {
                "privacy_level": privacy_assessment["privacy_level"],
                "route_recommendation": privacy_assessment["recommendation"],
                "local_only_mode": True,
                "selected_specialist_agent": selected_agent.get("agent_name") if selected_agent else "tenet-orchestrator",
            },
        }

    def select_specialist_agent(self, prompt: str, privacy_level: str) -> dict | None:
        prompt_lower = prompt.lower()
        if privacy_level == "sensitive":
            return capability_registry.find_best_agent("secure_routing")
        if any(word in prompt_lower for word in ["search", "find", "retrieve"]):
            return capability_registry.find_best_agent("semantic_search")
        if any(word in prompt_lower for word in ["branch", "fork", "rollback", "merge"]):
            return capability_registry.find_best_agent("branch_management")
        if any(word in prompt_lower for word in ["memory", "context", "recall"]):
            return capability_registry.find_best_agent("context_management")
        if any(word in prompt_lower for word in ["model", "load", "unload", "optimize"]):
            return capability_registry.find_best_agent("model_management")
        return None

    def handle_branch_action(self, msg: BranchRequest) -> dict:
        action = msg.action
        if action in {BranchAction.CREATE, BranchAction.FORK}:
            branch = dag_store.create_branch(msg.conversation_id, msg.node_id, msg.branch_name)
                "privacy": "local-execution",
                "tps": ollama_result["tps"],
            }
        }
    
    async def route_to_cloud_model(self, msg: ChatRequest) -> dict:
        """Route request to cloud API"""
        
        try:
            # Try OpenAI first
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.DEFAULT_CLOUD_MODEL,
                        "messages": [{"role": "user", "content": msg.prompt}],
                        "max_tokens": 1000
                    },
                    timeout=self.config.CLOUD_TIMEOUT
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "response": result["choices"][0]["message"]["content"],
                    "model_used": self.config.DEFAULT_CLOUD_MODEL,
                    "execution_location": ExecutionLocation.CLOUD,
                    "conversation_id": msg.conversation_id,
                    "branch_id": msg.branch_id,
                    "metadata": {
                        "privacy": "cloud-execution",
                        "provider": "openai"
                    }
                }
                
        except Exception as e:
            # Fallback to simpler model if main fails
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.config.OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.config.FALLBACK_MODEL,
                            "messages": [{"role": "user", "content": msg.prompt}],
                            "max_tokens": 500
                        },
                        timeout=self.config.CLOUD_TIMEOUT
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    return {
                        "response": result["choices"][0]["message"]["content"],
                        "model_used": self.config.FALLBACK_MODEL,
                        "execution_location": ExecutionLocation.CLOUD,
                        "conversation_id": msg.conversation_id,
                        "branch_id": msg.branch_id,
                        "metadata": {
                            "privacy": "cloud-execution-fallback",
                            "provider": "openai"
                        }
                    }
            except Exception as fallback_error:
                raise Exception(f"Both primary and fallback cloud APIs failed: {str(e)}")
    
    async def store_conversation_context(self, msg: ChatRequest, response: dict):
        """Store conversation context via context keeper"""
        
        try:
            context_data = {
                "conversation_id": msg.conversation_id,
                "branch_id": msg.branch_id,
                "prompt": msg.prompt,
                "response": response["response"],
                "model_used": response["model_used"],
                "execution_location": response["execution_location"],
                "timestamp": time.time(),
                "metadata": response.get("metadata", {})
            }
            
            # Store via backend API (Person 4)
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.config.BACKEND_API_URL}/api/context",
                    json=context_data,
                    timeout=5.0
                )
                
        except Exception as e:
            print(f"Failed to store context: {e}")
    
    async def create_branch(self, msg: BranchRequest) -> dict:
        """Create new conversation branch via backend API"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/branches",
                    json={
                        "action": msg.action,
                        "conversation_id": msg.conversation_id,
                        "node_id": msg.node_id,
                        "branch_name": msg.branch_name,
                        "user_id": msg.user_id,
                        "source_branch_id": msg.source_branch_id,
                        "target_branch_id": msg.target_branch_id
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            return {
                "success": True,
                "branch_id": branch["branch_id"],
                "node_id": branch.get("head_node_id"),
                "message": "Branch created",
            }
        if action == BranchAction.LIST:
            branches = dag_store.list_branches(msg.conversation_id, include_pruned=msg.include_pruned)
            return {"success": True, "branches": branches, "message": f"Found {len(branches)} branches"}
        if action == BranchAction.SWITCH:
            branch = dag_store.switch_branch(msg.conversation_id, msg.branch_id or "")
            return {"success": True, "branch_id": branch["branch_id"], "message": "Branch switched"}
        if action == BranchAction.ROLLBACK:
            branch = dag_store.rollback(msg.conversation_id, msg.branch_id or "", msg.target_node_id or "")
            return {"success": True, "branch_id": branch["branch_id"], "node_id": branch["head_node_id"], "message": "Rollback complete"}
        if action == BranchAction.GET_GRAPH:
            graph = dag_store.get_graph(msg.conversation_id, include_pruned=msg.include_pruned)
            return {"success": True, "graph": graph, "message": "Graph loaded"}
        if action == BranchAction.DELETE:
            ok = dag_store.delete_branch(msg.conversation_id, msg.branch_id or "")
            return {"success": ok, "message": "Branch pruned" if ok else "Unable to delete branch"}
        return {"success": False, "message": f"Unsupported action: {action}"}
    
    def run(self):
        """Start the orchestrator agent"""
        self.agent.include(chat_protocol)
        self.agent.include(branch_protocol)
        print("🚀 Tenet Orchestrator Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Chat Protocol: Enabled")
        print(f"🔗 Branch Protocol: Enabled")
        self.agent.run()

# Run the orchestrator
if __name__ == "__main__":
    orchestrator = TenetOrchestrator()
    orchestrator.run()
