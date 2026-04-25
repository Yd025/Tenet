from uagents import Agent, Context
from protocols.memory_protocol import (
    MemoryRequest, MemoryResponse, ContextData, memory_protocol
)
from config.agent_config import AgentConfig
import httpx
import time
import json

class TenetContextKeeper:
    """Maintains conversation context and memory"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the context keeper agent
        self.agent = Agent(
            name="tenet-context-keeper",
            seed=self.config.CONTEXT_KEEPER_SEED,
            port=self.config.CONTEXT_KEEPER_PORT
        )
        
        # In-memory cache for frequently accessed context
        self.context_cache = {}
        self.cache_max_size = 100
        
        # Setup protocol handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup memory management handlers"""
        
        @memory_protocol.on_message(model=MemoryRequest)
        async def handle_memory_request(ctx: Context, sender: str, msg: MemoryRequest):
            """Handle memory operations"""
            
            try:
                if msg.action == "store":
                    response = await self.store_context(msg)
                elif msg.action == "retrieve":
                    response = await self.retrieve_context(msg)
                elif msg.action == "search":
                    response = await self.search_context(msg)
                elif msg.action == "delete":
                    response = await self.delete_context(msg)
                elif msg.action == "promote":
                    response = await self.promote_context(msg)
                else:
                    response = {
                        "success": False,
                        "action": msg.action,
                        "context": None,
                        "results": None,
                        "message": f"Unknown action: {msg.action}"
                    }
                
                await ctx.send(sender, MemoryResponse(**response))
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "action": msg.action,
                    "context": None,
                    "results": None,
                    "message": f"Memory operation failed: {str(e)}"
                }
                await ctx.send(sender, MemoryResponse(**error_response))
    
    async def store_context(self, msg: MemoryRequest) -> dict:
        """Store conversation context"""
        
        try:
            # Create context data
            context_data = ContextData(
                conversation_id=msg.conversation_id,
                branch_id=msg.branch_id,
                node_id=msg.context.get("node_id", str(int(time.time()))),
                prompt=msg.context.get("prompt", ""),
                response=msg.context.get("response", ""),
                model_used=msg.context.get("model_used", "unknown"),
                timestamp=time.time(),
                metadata=msg.context.get("metadata", {})
            )
            
            # Store in cache
            cache_key = f"{msg.conversation_id}_{msg.branch_id}"
            self.context_cache[cache_key] = context_data.dict()
            
            # Limit cache size
            if len(self.context_cache) > self.cache_max_size:
                # Remove oldest entry
                oldest_key = next(iter(self.context_cache))
                del self.context_cache[oldest_key]
            
            # Store in backend database
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/memory/store",
                    json=context_data.dict(),
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": "store",
                    "context": context_data.dict(),
                    "results": None,
                    "message": "Context stored successfully"
                }
                
        except Exception as e:
            # Store locally if backend fails
            cache_key = f"{msg.conversation_id}_{msg.branch_id}"
            self.context_cache[cache_key] = msg.context
            
            return {
                "success": True,
                "action": "store",
                "context": msg.context,
                "results": None,
                "message": f"Context stored locally (backend unavailable): {str(e)}"
            }
    
    async def retrieve_context(self, msg: MemoryRequest) -> dict:
        """Retrieve conversation context"""
        
        try:
            # Check cache first
            cache_key = f"{msg.conversation_id}_{msg.branch_id}"
            if cache_key in self.context_cache:
                return {
                    "success": True,
                    "action": "retrieve",
                    "context": self.context_cache[cache_key],
                    "results": None,
                    "message": "Context retrieved from cache"
                }
            
            # Retrieve from backend
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.BACKEND_API_URL}/api/memory/{msg.conversation_id}",
                    params={"branch_id": msg.branch_id} if msg.branch_id else {},
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": "retrieve",
                    "context": result.get("context"),
                    "results": None,
                    "message": "Context retrieved successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "retrieve",
                "context": None,
                "results": None,
                "message": f"Failed to retrieve context: {str(e)}"
            }
    
    async def search_context(self, msg: MemoryRequest) -> dict:
        """Search conversation context"""
        
        try:
            # Search in backend
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/memory/search",
                    json={
                        "query": msg.query,
                        "conversation_id": msg.conversation_id,
                        "branch_id": msg.branch_id,
                        "limit": msg.limit
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": "search",
                    "context": None,
                    "results": result.get("results", []),
                    "message": f"Found {len(result.get('results', []))} matching contexts"
                }
                
        except Exception as e:
            # Simple local search as fallback
            local_results = []
            query_lower = msg.query.lower()
            
            for context in self.context_cache.values():
                context_str = json.dumps(context).lower()
                if query_lower in context_str:
                    local_results.append(context)
                    if len(local_results) >= msg.limit:
                        break
            
            return {
                "success": True,
                "action": "search",
                "context": None,
                "results": local_results,
                "message": f"Found {len(local_results)} matching contexts (local search)"
            }
    
    async def delete_context(self, msg: MemoryRequest) -> dict:
        """Delete conversation context"""
        
        try:
            # Remove from cache
            cache_key = f"{msg.conversation_id}_{msg.branch_id}"
            if cache_key in self.context_cache:
                del self.context_cache[cache_key]
            
            # Delete from backend
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.config.BACKEND_API_URL}/api/memory/{msg.conversation_id}",
                    params={"branch_id": msg.branch_id} if msg.branch_id else {},
                    timeout=10.0
                )
                response.raise_for_status()
                
                return {
                    "success": True,
                    "action": "delete",
                    "context": None,
                    "results": None,
                    "message": "Context deleted successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "delete",
                "context": None,
                "results": None,
                "message": f"Failed to delete context: {str(e)}"
            }
    
    async def promote_context(self, msg: MemoryRequest) -> dict:
        """Promote important context to long-term memory"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.BACKEND_API_URL}/api/memory/promote",
                    json={
                        "conversation_id": msg.conversation_id,
                        "branch_id": msg.branch_id,
                        "limit": msg.limit
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": "promote",
                    "context": result.get("context"),
                    "results": None,
                    "message": "Context promoted successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "promote",
                "context": None,
                "results": None,
                "message": f"Failed to promote context: {str(e)}"
            }
    
    def run(self):
        """Start the context keeper agent"""
        self.agent.include(memory_protocol)
        print("🧠 Tenet Context Keeper Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Memory Protocol: Enabled")
        print("💾 Memory operations: store, retrieve, search, delete, promote")
        print(f"📦 Cache size: {self.cache_max_size} contexts")
        self.agent.run()

# Run the context keeper
if __name__ == "__main__":
    context_keeper = TenetContextKeeper()
    context_keeper.run()
