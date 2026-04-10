from fastapi import APIRouter

router = APIRouter()

# ✅ Test route
@router.get("/")
def lab_root():
    return {"message": "Lab routes working"}

# ✅ Simulation endpoint
@router.post("/simulate")
def simulate(data: dict):
    # TEMP basic simulation
    result = {
        "input": data,
        "output": "Simulation ran successfully",
        "score": 85
    }

    return {
        "status": "success",
        "result": result
    }

# ✅ History endpoint
@router.get("/history")
def get_history():
    return {
        "history": [
            {"id": 1, "result": "Test simulation"},
            {"id": 2, "result": "Another simulation"}
        ]
    }