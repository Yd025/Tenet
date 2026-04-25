from uagents import Agent, Context
from protocols.storage_protocol import (
    StorageRequest, StorageResponse, ModelInfo, ModelStatusRequest,
    ModelStatusResponse, storage_protocol, StorageAction
)
from config.agent_config import AgentConfig
import asyncio
from utils.local_runtime import model_registry

class TenetModelCoordinator:
    """Coordinates AI model loading and hardware integration"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the model coordinator agent
        self.agent = Agent(
            name="tenet-model-coordinator",
            seed=self.config.MODEL_COORDINATOR_SEED,
            port=self.config.MODEL_COORDINATOR_PORT,
            mailbox=True,
            publish_agent_details=True,
        )
        
        # Model cache tracking
        self.loaded_models = {}
        self.model_load_times = {}
        
        # Setup protocol handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup model coordination handlers"""
        
        @storage_protocol.on_message(model=StorageRequest)
        async def handle_storage_request(ctx: Context, sender: str, msg: StorageRequest):
            """Handle model storage and coordination requests"""
            
            try:
                if msg.action == StorageAction.LIST:
                    response = await self.list_models()
                elif msg.action == StorageAction.LOAD:
                    response = await self.load_model(msg.model_name, msg.parameters)
                elif msg.action == StorageAction.UNLOAD:
                    response = await self.unload_model(msg.model_name)
                elif msg.action == StorageAction.STATUS:
                    response = await self.get_model_status(msg.model_name)
                elif msg.action == StorageAction.OPTIMIZE:
                    response = await self.optimize_models()
                else:
                    response = {
                        "success": False,
                        "action": msg.action,
                        "models": None,
                        "message": f"Unknown action: {msg.action}",
                        "storage_info": None
                    }
                
                await ctx.send(sender, StorageResponse(**response))
                
            except Exception as e:
                error_response = {
                    "success": False,
                    "action": msg.action,
                    "models": None,
                    "message": f"Model coordination failed: {str(e)}",
                    "storage_info": None
                }
                await ctx.send(sender, StorageResponse(**error_response))
        
        @storage_protocol.on_message(model=ModelStatusRequest)
        async def handle_model_status(ctx: Context, sender: str, msg: ModelStatusRequest):
            """Handle model status requests"""
            
            try:
                status_info = await self.get_detailed_model_status(msg.model_name)
                
                response = ModelStatusResponse(
                    model_name=msg.model_name,
                    status=status_info["status"],
                    memory_usage_mb=status_info["memory_usage_mb"],
                    load_time_ms=status_info.get("load_time_ms")
                )
                
                await ctx.send(sender, response)
                
            except Exception as e:
                error_response = ModelStatusResponse(
                    model_name=msg.model_name,
                    status="error",
                    memory_usage_mb=0.0,
                    load_time_ms=None
                )
                await ctx.send(sender, error_response)
    
    async def list_models(self) -> dict:
        """List all available models"""
        
        try:
            models = [ModelInfo(**model) for model in model_registry.list_models()]
            return {
                "success": True,
                "action": StorageAction.LIST,
                "models": models,
                "message": f"Found {len(models)} models",
                "storage_info": {"total_gb": 100, "used_gb": 20, "available_gb": 80}
            }
        except Exception as e:
            return {"success": False, "action": StorageAction.LIST, "models": None, "message": str(e), "storage_info": None}
    
    async def load_model(self, model_name: str, parameters: dict = None) -> dict:
        """Load a model into memory"""
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            success, status_message = model_registry.load(model_name)
            load_time = (asyncio.get_event_loop().time() - start_time) * 1000
            self.model_load_times[model_name] = load_time
            self.loaded_models[model_name] = {
                "loaded_at": asyncio.get_event_loop().time(),
                "load_time_ms": load_time
            }
            
            return {
                "success": success,
                "action": StorageAction.LOAD,
                "models": None,
                "message": f"{status_message} in {load_time:.0f}ms",
                "storage_info": {"local_only_mode": True}
            }
                
        except Exception as e:
            return {
                "success": False,
                "action": StorageAction.LOAD,
                "models": None,
                "message": f"Failed to load model '{model_name}': {str(e)}",
                "storage_info": None
            }
    
    async def unload_model(self, model_name: str) -> dict:
        """Unload a model from memory"""
        
        try:
            success, status_message = model_registry.unload(model_name)
            # Remove from tracking
            if model_name in self.loaded_models:
                del self.loaded_models[model_name]
            if model_name in self.model_load_times:
                del self.model_load_times[model_name]
            
            return {
                "success": success,
                "action": StorageAction.UNLOAD,
                "models": None,
                "message": status_message,
                "storage_info": {"local_only_mode": True}
            }
                
        except Exception as e:
            return {
                "success": False,
                "action": StorageAction.UNLOAD,
                "models": None,
                "message": f"Failed to unload model '{model_name}': {str(e)}",
                "storage_info": None
            }
    
    async def get_model_status(self, model_name: str) -> dict:
        """Get status of a specific model"""
        
        try:
            status = model_registry.status(model_name)
            return {
                "success": True,
                "action": StorageAction.STATUS,
                "models": None,
                "message": f"Model '{model_name}' status retrieved",
                "storage_info": status
            }
        except Exception as e:
            return {
                "success": False,
                "action": StorageAction.STATUS,
                "models": None,
                "message": f"Failed to get model status: {str(e)}",
                "storage_info": None
            }
    
    async def get_detailed_model_status(self, model_name: str) -> dict:
        """Get detailed model status information"""
        
        if model_name in self.loaded_models:
            return {
                "status": "loaded",
                "memory_usage_mb": self.loaded_models[model_name].get("memory_usage_mb", 0),
                "load_time_ms": self.model_load_times.get(model_name)
            }
        else:
            return {
                "status": "unloaded",
                "memory_usage_mb": 0.0,
                "load_time_ms": None
            }
    
    async def optimize_models(self) -> dict:
        """Optimize model loading and memory usage"""
        
        try:
            result = model_registry.optimize()
            return {
                "success": True,
                "action": StorageAction.OPTIMIZE,
                "models": None,
                "message": result.get("message", "Model optimization completed"),
                "storage_info": result
            }
        except Exception as e:
            return {
                "success": False,
                "action": StorageAction.OPTIMIZE,
                "models": None,
                "message": f"Optimization failed: {str(e)}",
                "storage_info": None
            }
    
    def run(self):
        """Start the model coordinator agent"""
        self.agent.include(storage_protocol)
        print("🤖 Tenet Model Coordinator Agent starting...")
        print(f"📍 Agent Address: {self.agent.address}")
        print(f"🔗 Storage Protocol: Enabled")
        print("⚙️  Model operations: list, load, unload, status, optimize")
        self.agent.run()

# Run the model coordinator
if __name__ == "__main__":
    model_coordinator = TenetModelCoordinator()
    model_coordinator.run()
