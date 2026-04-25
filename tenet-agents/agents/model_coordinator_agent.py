from uagents import Agent, Context
from protocols.storage_protocol import (
    StorageRequest, StorageResponse, ModelInfo, ModelStatusRequest,
    ModelStatusResponse, storage_protocol
)
from config.agent_config import AgentConfig
import httpx
import asyncio

class TenetModelCoordinator:
    """Coordinates AI model loading and hardware integration"""
    
    def __init__(self):
        self.config = AgentConfig()
        
        # Initialize the model coordinator agent
        self.agent = Agent(
            name="tenet-model-coordinator",
            seed=self.config.MODEL_COORDINATOR_SEED,
            port=self.config.MODEL_COORDINATOR_PORT
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
                if msg.action == "list":
                    response = await self.list_models()
                elif msg.action == "load":
                    response = await self.load_model(msg.model_name, msg.parameters)
                elif msg.action == "unload":
                    response = await self.unload_model(msg.model_name)
                elif msg.action == "status":
                    response = await self.get_model_status(msg.model_name)
                elif msg.action == "optimize":
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
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.HARDWARE_API_URL}/models",
                    timeout=10.0
                )
                response.raise_for_status()
                models_data = response.json()
                
                models = [
                    ModelInfo(
                        name=model.get("name"),
                        size_gb=model.get("size_gb", 0.0),
                        quantization=model.get("quantization", "unknown"),
                        status=model.get("status", "unknown"),
                        hardware_requirements=model.get("hardware_requirements", {}),
                        last_used=model.get("last_used")
                    )
                    for model in models_data.get("models", [])
                ]
                
                return {
                    "success": True,
                    "action": "list",
                    "models": models,
                    "message": f"Found {len(models)} models",
                    "storage_info": models_data.get("storage_info", {})
                }
                
        except Exception as e:
            # Return mock data if hardware API unavailable
            mock_models = [
                ModelInfo(
                    name="llama2-7b-4bit",
                    size_gb=4.2,
                    quantization="4bit",
                    status="loaded",
                    hardware_requirements={"ram_gb": 8, "vram_gb": 6},
                    last_used="2024-01-15T10:30:00Z"
                )
            ]
            
            return {
                "success": True,
                "action": "list",
                "models": mock_models,
                "message": f"Found {len(mock_models)} models (mock data)",
                "storage_info": {"total_gb": 100, "used_gb": 20, "available_gb": 80}
            }
    
    async def load_model(self, model_name: str, parameters: dict = None) -> dict:
        """Load a model into memory"""
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.HARDWARE_API_URL}/models/load",
                    json={
                        "model_name": model_name,
                        "parameters": parameters or {}
                    },
                    timeout=60.0  # Allow up to 1 minute for loading
                )
                response.raise_for_status()
                result = response.json()
                
                load_time = (asyncio.get_event_loop().time() - start_time) * 1000
                self.model_load_times[model_name] = load_time
                self.loaded_models[model_name] = {
                    "loaded_at": asyncio.get_event_loop().time(),
                    "load_time_ms": load_time
                }
                
                return {
                    "success": True,
                    "action": "load",
                    "models": None,
                    "message": f"Model '{model_name}' loaded successfully in {load_time:.0f}ms",
                    "storage_info": result.get("storage_info", {})
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "load",
                "models": None,
                "message": f"Failed to load model '{model_name}': {str(e)}",
                "storage_info": None
            }
    
    async def unload_model(self, model_name: str) -> dict:
        """Unload a model from memory"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.HARDWARE_API_URL}/models/unload",
                    json={"model_name": model_name},
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Remove from tracking
                if model_name in self.loaded_models:
                    del self.loaded_models[model_name]
                if model_name in self.model_load_times:
                    del self.model_load_times[model_name]
                
                return {
                    "success": True,
                    "action": "unload",
                    "models": None,
                    "message": f"Model '{model_name}' unloaded successfully",
                    "storage_info": result.get("storage_info", {})
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "unload",
                "models": None,
                "message": f"Failed to unload model '{model_name}': {str(e)}",
                "storage_info": None
            }
    
    async def get_model_status(self, model_name: str) -> dict:
        """Get status of a specific model"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.HARDWARE_API_URL}/models/{model_name}/status",
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": "status",
                    "models": None,
                    "message": f"Model '{model_name}' status retrieved",
                    "storage_info": result
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "status",
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
            # Get optimization suggestions from hardware
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.HARDWARE_API_URL}/models/optimize",
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "action": "optimize",
                    "models": None,
                    "message": result.get("message", "Model optimization completed"),
                    "storage_info": result.get("storage_info", {})
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "optimize",
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
