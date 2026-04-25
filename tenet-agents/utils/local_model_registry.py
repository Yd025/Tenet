import threading
import time
from copy import deepcopy


class LocalModelRegistry:
    """Local model registry simulation for offline development."""

    def __init__(self):
        self._lock = threading.RLock()
        self._models = {
            "llama2-7b-4bit": {
                "name": "llama2-7b-4bit",
                "size_gb": 4.2,
                "quantization": "4bit",
                "status": "loaded",
                "hardware_requirements": {"ram_gb": 8, "vram_gb": 6},
                "last_used": None,
            },
            "mistral-7b-q8": {
                "name": "mistral-7b-q8",
                "size_gb": 7.1,
                "quantization": "8bit",
                "status": "unloaded",
                "hardware_requirements": {"ram_gb": 12, "vram_gb": 8},
                "last_used": None,
            },
        }

    def list_models(self):
        with self._lock:
            return [deepcopy(v) for v in self._models.values()]

    def load(self, model_name: str):
        with self._lock:
            if model_name not in self._models:
                return False, f"Model '{model_name}' not found"
            self._models[model_name]["status"] = "loaded"
            self._models[model_name]["last_used"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            return True, f"Model '{model_name}' loaded"

    def unload(self, model_name: str):
        with self._lock:
            if model_name not in self._models:
                return False, f"Model '{model_name}' not found"
            self._models[model_name]["status"] = "unloaded"
            return True, f"Model '{model_name}' unloaded"

    def status(self, model_name: str):
        with self._lock:
            model = self._models.get(model_name)
            if not model:
                return {"status": "missing", "memory_usage_mb": 0.0, "load_time_ms": None}
            return {
                "status": model["status"],
                "memory_usage_mb": model["size_gb"] * 1024 if model["status"] == "loaded" else 0.0,
                "load_time_ms": 500.0 if model["status"] == "loaded" else None,
            }

    def optimize(self):
        with self._lock:
            loaded = [m for m in self._models.values() if m["status"] == "loaded"]
            return {"loaded_models": len(loaded), "message": "Optimization complete (local simulation)"}

