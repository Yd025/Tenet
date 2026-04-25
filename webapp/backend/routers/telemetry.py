from fastapi import APIRouter
import random

router = APIRouter()

# Stateful mock that drifts ±5% per call
_state = {"temp_c": 72.0, "petaflops_pct": 45.0, "tps": 128.0}

def _drift(value: float, lo: float, hi: float, step: float = 0.05) -> float:
    delta = value * step * random.uniform(-1, 1)
    return round(max(lo, min(hi, value + delta)), 1)

@router.get("/telemetry")
async def get_telemetry():
    _state["temp_c"] = _drift(_state["temp_c"], 65.0, 85.0)
    _state["petaflops_pct"] = _drift(_state["petaflops_pct"], 30.0, 70.0)
    _state["tps"] = _drift(_state["tps"], 80.0, 180.0)
    return {
        "temp_c": _state["temp_c"],
        "petaflops_pct": _state["petaflops_pct"],
        "tps": _state["tps"],
    }
