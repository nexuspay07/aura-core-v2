from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()


async def agent_stream():
    steps = [
        {"agent": "Planner", "message": "Analyzing goal..."},
        {"agent": "Market Analyst", "message": "Evaluating market conditions..."},
        {"agent": "Risk Engine", "message": "Calculating risk exposure..."},
        {"agent": "Execution Agent", "message": "Building logistics structure..."},
        {"agent": "Optimizer", "message": "Optimizing strategy..."},
        {"agent": "Finalizer", "message": "Simulation complete"}
    ]

    for step in steps:
        yield f"data: {json.dumps(step)}\n\n"
        await asyncio.sleep(1)


@router.get("/stream")
async def stream():
    return StreamingResponse(agent_stream(), media_type="text/event-stream")