# app/api/system.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio

router = APIRouter()

@router.get("/run_stream")
async def run_system_stream():
    async def event_generator():
        for i in range(10):
            yield f"data: Step {i}\n\n"  # Server-Sent Events format
            await asyncio.sleep(0.5)
    return StreamingResponse(event_generator(), media_type="text/event-stream")