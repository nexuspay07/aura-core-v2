# app/api/api_engine.py

from fastapi import FastAPI, Request, HTTPException
from app.core.cognitive_loop import cognitive_loop
from app.monitoring.monitoring_engine import monitoring_engine
from app.security.security_engine import security_engine

app = FastAPI(title="AURA AI API Layer")

# -----------------------------
# Middleware: Agent / User Auth
# -----------------------------
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Check headers for agent or user token
    agent_name = request.headers.get("X-Agent-Name")
    agent_token = request.headers.get("X-Agent-Token")
    user_id = request.headers.get("X-User-Id")
    user_token = request.headers.get("X-User-Token")

    # Verify agent first
    if agent_name and agent_token:
        if not security_engine.verify_agent_token(agent_name, agent_token):
            monitoring_engine.log_event("agent_auth_failed", {"agent": agent_name})
            raise HTTPException(status_code=401, detail="Invalid agent token")
        monitoring_engine.log_event("agent_authenticated", {"agent": agent_name})

    # Verify user
    elif user_id and user_token:
        if not security_engine.verify_user_token(user_id, user_token):
            monitoring_engine.log_event("user_auth_failed", {"user": user_id})
            raise HTTPException(status_code=401, detail="Invalid user token")
        monitoring_engine.log_event("user_authenticated", {"user": user_id})

    return await call_next(request)

# -----------------------------
# Cognitive Loop Endpoint
# -----------------------------
@app.post("/system/run")
async def run_system():
    monitoring_engine.log_event("api_call", {"endpoint": "/system/run"})
    result = cognitive_loop.run()
    return result

# -----------------------------
# Health Check Endpoint
# -----------------------------
@app.get("/health")
async def health_check():
    return {"status": "AURA AI operational", "time": time.time()}

# -----------------------------
# Agent Token Endpoint
# -----------------------------
@app.post("/auth/agent")
async def authenticate_agent(agent_name: str):
    token = security_engine.authenticate_agent(agent_name)
    monitoring_engine.log_event("agent_token_issued", {"agent": agent_name})
    return {"agent_name": agent_name, "token": token}

# -----------------------------
# User Token Endpoint
# -----------------------------
@app.post("/auth/user")
async def authenticate_user(user_id: str):
    token = security_engine.authenticate_user(user_id)
    monitoring_engine.log_event("user_token_issued", {"user": user_id})
    return {"user_id": user_id, "token": token}