# app/persistence/persistence_engine.py

import json
import time
from AURA.AURA_CORE_V2.app.db.database import database


class PersistenceEngine:

    # -------------------
    # Users
    # -------------------
    def save_user(self, user_id, username, role):
        database.save(
            "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
            (user_id, username, role, time.time())
        )

    def get_user(self, user_id):
        result = database.fetch(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        return result

    # -------------------
    # Goals
    # -------------------
    def save_goal(self, goal):
        database.save(
            "INSERT INTO goals (goal_name, created_at) VALUES (?, ?)",
            (goal.get("name"), time.time())
        )

    # -------------------
    # Plans
    # -------------------
    def save_plan(self, goal, plan):
        database.save(
            "INSERT INTO plans (goal_name, plan, created_at) VALUES (?, ?, ?)",
            (goal.get("name"), json.dumps(plan), time.time())
        )

    # -------------------
    # Executions
    # -------------------
    def save_execution(self, goal, result):
        database.save(
            "INSERT INTO executions (goal_name, result, created_at) VALUES (?, ?, ?)",
            (goal.get("name"), json.dumps(result), time.time())
        )

    def get_execution_history(self):
        return database.fetch("SELECT * FROM executions ORDER BY created_at DESC")
    
    # app/persistence/persistence_engine.py

def save_simulation_results(results):
    """
    Placeholder for saving simulation results.
    For now, just print to console.
    Later, integrate with database or file storage.
    """
    print("[PERSISTENCE] Simulation results saved:")
    for strategy, score in results.items():
        print(f"  {strategy}: {score}")


# Singleton
persistence_engine = PersistenceEngine()