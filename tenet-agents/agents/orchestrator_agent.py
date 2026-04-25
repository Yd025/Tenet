from uagents import Agent, Context
from protocols.chat_protocol import (
    ChatRequest, ChatResponse, PrivacyAnalysisRequest, PrivacyAnalysisResponse,
    chat_protocol, PrivacyLevel, ExecutionLocation
)
from protocols.branch_protocol import BranchRequest, BranchResponse, branch_protocol
from config.agent_config import AgentConfig
import httpx
import asyncio
import json
import time

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
        
        # Specialist agent addresses (will be auto-discovered)
        self.privacy_router_address = None
        self.branch_manager_address = None
        self.model_coordinator_address = None
        self.context_keeper_address = None
        
        # Performance tracking
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
                # Step 1: Analyze privacy requirements
                privacy_assessment = await self.analyze_privacy(msg)
                
                # Step 2: Route based on privacy level
                if privacy_assessment["level"] == PrivacyLevel.SENSITIVE:
                    # Route to local model (Person 2's hardware)
                    response_data = await self.route_to_local_model(msg)
                    self.performance_metrics["local_requests"] += 1
                else:
                    # Route to cloud API
                    response_data = await self.route_to_cloud_model(msg)
                    self.performance_metrics["cloud_requests"] += 1
                
                # Step 3: Store conversation context
                await self.store_conversation_context(msg, response_data)
                
                # Step 4: Calculate performance metrics
                response_time = (time.time() - start_time) * 1000
                self.performance_metrics["avg_response_time_ms"] = (
                    (self.performance_metrics["avg_response_time_ms"] * (self.performance_metrics["total_requests"] - 1) + response_time) /
                    self.performance_metrics["total_requests"]
                )
                
                # Step 5: Send response back
                response_data["performance_metrics"] = {
                    "response_time_ms": response_time,
                    "total_requests": self.performance_metrics["total_requests"],
                    "avg_response_time_ms": self.performance_metrics["avg_response_time_ms"]
                }
                
                await ctx.send(sender, ChatResponse(**response_data))
                
            except Exception as e:
                # Error handling
                self.performance_metrics["error_count"] += 1
                error_response = {
                    "response": f"I apologize, but I encountered an error: {str(e)}",
                    "model_used": "error",
                    "execution_location": ExecutionLocation.CLOUD,
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
                # Route branch operations to branch manager
                branch_result = await self.create_branch(msg)
                
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
        """Route request to local model on ASUS hardware"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.HARDWARE_API_URL}/generate",
                    json={
                        "prompt": msg.prompt,
                        "conversation_id": msg.conversation_id,
                        "branch_id": msg.branch_id,
                        "model": self.config.DEFAULT_LOCAL_MODEL
                    },
                    timeout=self.config.LOCAL_TIMEOUT
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "response": result.get("response", "Local model response"),
                    "model_used": result.get("model", self.config.DEFAULT_LOCAL_MODEL),
                    "execution_location": ExecutionLocation.LOCAL,
                    "conversation_id": msg.conversation_id,
                    "branch_id": msg.branch_id,
                    "metadata": {
                        "privacy": "local-execution",
                        "hardware_accelerated": True
                    }
                }
                
        except Exception as e:
            print(f"Local model failed: {e}, falling back to cloud")
            return await self.route_to_cloud_model(msg)
    
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
                "success": False,
                "branch_id": "",
                "node_id": "",
                "message": f"Failed to create branch: {str(e)}"
            }
    
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
