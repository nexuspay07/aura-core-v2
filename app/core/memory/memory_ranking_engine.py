# app/core/memory/memory_ranking_engine.py

from datetime import datetime


class MemoryRankingEngine:

    def __init__(self):
        print("[MEMORY RANKING ENGINE] Initialized")

    def calculate_importance(
        self,
        memory_text: str,
        access_count: int = 0,
        success_score: float = 0.0,
        emotional_weight: float = 0.0,
        strategic_value: float = 0.0,
        recency_hours: float = 0.0
    ):

        score = 0.0

        # ==========================================
        # MEMORY LENGTH SIGNAL
        # ==========================================

        score += min(len(memory_text) / 100, 10)

        # ==========================================
        # ACCESS FREQUENCY
        # ==========================================

        score += access_count * 1.5

        # ==========================================
        # SUCCESS REINFORCEMENT
        # ==========================================

        score += success_score * 5

        # ==========================================
        # EMOTIONAL SIGNIFICANCE
        # ==========================================

        score += emotional_weight * 3

        # ==========================================
        # STRATEGIC VALUE
        # ==========================================

        score += strategic_value * 7

        # ==========================================
        # RECENCY BOOST
        # ==========================================

        if recency_hours < 24:
            score += 5

        elif recency_hours < 168:
            score += 2

        # ==========================================
        # FINAL CLASSIFICATION
        # ==========================================

        if score >= 40:
            level = "critical"

        elif score >= 25:
            level = "high"

        elif score >= 10:
            level = "medium"

        else:
            level = "low"

        return {
            "memory": memory_text,
            "importance_score": round(score, 2),
            "importance_level": level,
            "ranked_at": datetime.utcnow().isoformat()
        }


memory_ranking_engine = MemoryRankingEngine()