from uagents import Agent, Context
from protocols.memory_protocol import (
    MemoryRequest, MemoryResponse, ContextData, memory_protocol, MemoryAction
)
from config.agent_config import AgentConfig
import time
from utils.local_runtime import memory_store

class TenetContextKeeper:
    """Maintains conversation context and memory"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the context keeper agent
        self.agent = Agent(
            name="tenet-context-keeper",
            seed=self.config.CONTEXT_KEEPER_SEED,
            port=self.config.CONTEXT_KEEPER_PORT,
            mailbox=True,
            publish_agent_details=True,
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
                if msg.action == MemoryAction.STORE:
                    response = await self.store_context(msg)
                elif msg.action == MemoryAction.RETRIEVE:
                    response = await self.retrieve_context(msg)
                elif msg.action == MemoryAction.SEARCH:
                    response = await self.search_context(msg)
                elif msg.action == MemoryAction.DELETE:
                    response = await self.delete_context(msg)
                elif msg.action == MemoryAction.PROMOTE:
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
            
            memory_store.store(context_data.dict(), msg.conversation_id, msg.branch_id)
            return {
                "success": True,
                "action": MemoryAction.STORE,
                "context": context_data.dict(),
                "results": None,
                "message": "Context stored successfully"
            }
        except Exception as e:
            cache_key = f"{msg.conversation_id}_{msg.branch_id}"
            self.context_cache[cache_key] = msg.context
            
            return {
                "success": True,
                "action": MemoryAction.STORE,
                "context": msg.context,
                "results": None,
                "message": f"Context stored in cache: {str(e)}"
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
            
            context = memory_store.retrieve(msg.conversation_id, msg.branch_id)
            return {
                "success": context is not None,
                "action": MemoryAction.RETRIEVE,
                "context": context,
                "results": None,
                "message": "Context retrieved successfully" if context else "No context found"
            }
                
        except Exception as e:
            return {
                "success": False,
                "action": MemoryAction.RETRIEVE,
                "context": None,
                "results": None,
                "message": f"Failed to retrieve context: {str(e)}"
            }
    
    async def search_context(self, msg: MemoryRequest) -> dict:
        """Search conversation context"""
        
        try:
            results = memory_store.search(msg.query or "", msg.conversation_id, msg.branch_id, msg.limit or 10)
            return {
                "success": True,
                "action": MemoryAction.SEARCH,
                "context": None,
                "results": results,
                "message": f"Found {len(results)} matching contexts"
            }
        except Exception as e:
            return {
                "success": False,
                "action": MemoryAction.SEARCH,
                "context": None,
                "results": [],
                "message": f"Search failed: {str(e)}"
            }
    
    async def delete_context(self, msg: MemoryRequest) -> dict:
        """Delete conversation context"""
        
        try:
            # Remove from cache
            cache_key = f"{msg.conversation_id}_{msg.branch_id}"
            if cache_key in self.context_cache:
                del self.context_cache[cache_key]
            
            removed = memory_store.delete(msg.conversation_id, msg.branch_id)
            return {
                "success": True,
                "action": MemoryAction.DELETE,
                "context": None,
                "results": None,
                "message": f"Deleted {removed} context entries"
            }
                
        except Exception as e:
            return {
                "success": False,
                "action": MemoryAction.DELETE,
                "context": None,
                "results": None,
                "message": f"Failed to delete context: {str(e)}"
            }
    
    async def promote_context(self, msg: MemoryRequest) -> dict:
        """Promote important context to long-term memory"""
        
        try:
            promoted = memory_store.promote(msg.conversation_id, msg.branch_id, msg.limit or 10)
            return {
                "success": True,
                "action": MemoryAction.PROMOTE,
                "context": promoted[0] if promoted else None,
                "results": promoted,
                "message": "Context promoted successfully"
            }
                
        except Exception as e:
            return {
                "success": False,
                "action": MemoryAction.PROMOTE,
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
