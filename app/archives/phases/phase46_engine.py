# app/engine/phase46_engine.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import sqlite3
import os

# -------------------------
# Router setup
# -------------------------
router = APIRouter(
    prefix="/phase46",
    tags=["Phase 46 — Persistence Engine"]
)

# -------------------------
# Pydantic models
# -------------------------
class Phase46Input(BaseModel):
    previous_results: Dict[str, float]

class Phase46Output(BaseModel):
    message: str
    saved_results: Dict[str, float]

# -------------------------
# Persistence Engine
# -------------------------
DB_PATH = "aura_memory.db"

class PersistenceEngine:
    """Phase 46: Persist optimized results to SQLite for long-term memory."""
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database and table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimized_results (
                key TEXT PRIMARY KEY,
                value REAL
            )
        """)
        conn.commit()
        conn.close()

    def save_results(self, results: Dict[str, float]):
        """Save the optimized results to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for key, value in results.items():
            cursor.execute("""
                INSERT INTO optimized_results(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (key, value))
        conn.commit()
        conn.close()

    def load_results(self) -> Dict[str, float]:
        """Load all previously saved results from the database."""
        if not os.path.exists(self.db_path):
            return {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM optimized_results")
        rows = cursor.fetchall()
        conn.close()
        return {key: value for key, value in rows}

# Instantiate engine
persistence_engine = PersistenceEngine()

# -------------------------
# API Endpoints
# -------------------------
@router.post("/save", response_model=Phase46Output)
async def save_phase46(data: Phase46Input):
    """Save the optimized results to persistent memory."""
    persistence_engine.save_results(data.previous_results)
    return Phase46Output(
        message="Phase 46: Results saved successfully",
        saved_results=data.previous_results
    )

@router.get("/load", response_model=Phase46Output)
async def load_phase46():
    """Load previously saved results from persistent memory."""
    results = persistence_engine.load_results()
    return Phase46Output(
        message="Phase 46: Results loaded successfully",
        saved_results=results
    )