from app.core.memory.memory_ranking_engine import memory_ranking_engine
from app.core.memory.memory_decay_engine import memory_decay_engine


result = memory_ranking_engine.calculate_importance(
    memory_text="AURA successfully predicted a market crash",
    access_count=12,
    success_score=0.95,
    emotional_weight=0.4,
    strategic_value=0.9,
    recency_hours=2
)

print(result)


decay_result = memory_decay_engine.calculate_decay(
    importance_score=result["importance_score"],
    hours_since_access=72,
    reinforcement_count=5
)

from app.core.memory.memory_clustering_engine import memory_clustering_engine


cluster_result = memory_clustering_engine.cluster_memories([
    "AURA predicted market collapse",
    "Finance strategy increased profit",
    "Customer behavior shifted rapidly",
    "Risk analysis detected instability",
    "General business insight"
])

print(cluster_result)

print(decay_result)

from app.core.memory.memory_reinforcement_engine import memory_reinforcement_engine


reinforcement_result = memory_reinforcement_engine.reinforce_memory(
    memory_text="Expansion strategy increased company revenue",
    outcome_score=0.92,
    usage_count=15,
    strategic_value=0.95
)

print(reinforcement_result)

from app.core.memory.memory_priority_retrieval_engine import (
    memory_priority_retrieval_engine
)


priority_result = (
    memory_priority_retrieval_engine.retrieve_priority_memories([
        {
            "memory": "Market expansion succeeded",
            "importance_score": 32
        },
        {
            "memory": "Minor UI adjustment",
            "importance_score": 6
        },
        {
            "memory": "Risk prediction prevented losses",
            "importance_score": 41
        }
    ])
)

print(priority_result)