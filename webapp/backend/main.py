from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, branch, telemetry

app = FastAPI(title="Tenet API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(branch.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
