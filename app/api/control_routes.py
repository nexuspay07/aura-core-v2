# app/api/control_routes.py

from fastapi import APIRouter
from app.control.control_engine import control_engine

router = APIRouter(prefix="/control", tags=["Control"])

@router.post("/approve")
def approve():
    control_engine.set_decision("approved")
    return {"status": "approved"}

@router.post("/reject")
def reject():
    control_engine.set_decision("rejected")
    return {"status": "rejected"}