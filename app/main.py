import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ==========================
# CREATE APP
# ==========================
app = FastAPI(title="AURA AI")

# ==========================
# CORS CONFIGURATION
# ==========================
# 🔹 Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://aura-ai.onrender.com"],  # frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# DATABASE
# ==========================
from app.db.database import database, engine, metadata

# ==========================
# CORE SYSTEMS
# ==========================
from app.lab.world_engine import world_engine
from app.lab.history_engine import history_engine
from app.core.cognitive_loop import cognitive_loop
from app.control.control_engine import control_engine
from app.lab.simulation_engine import simulation_engine
from app.lab.explanation_engine import explanation_engine
from app.lab.agent_engine import agent_engine
from app.lab.debate_engine import debate_engine

# ==========================
# ROUTERS
# ==========================
from app.routes.auth import router as auth_router, get_current_user
from app.api.strategy_routes import router as strategy_router
from app.routes import simulation
from app.api.marketplace_routes import router as marketplace_router

app.include_router(auth_router, prefix="/auth")  # 🔹 fix prefix
app.include_router(strategy_router)
app.include_router(simulation.router)
app.include_router(marketplace_router)

# ==========================
# STARTUP / SHUTDOWN
# ==========================
@app.on_event("startup")
async def startup():
    metadata.create_all(engine)
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ==========================
# ROOT
# ==========================
@app.get("/")
def root():
    return {"message": "AURA AI running 🚀"}