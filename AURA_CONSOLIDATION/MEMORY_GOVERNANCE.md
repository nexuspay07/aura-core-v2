# MEMORY GOVERNANCE

## CANONICAL MEMORY SYSTEMS

### app/services/memory_service.py
STATUS: CANONICAL

Purpose:
- session memory
- user memory
- organization memory
- runtime memory access

This is the PRIMARY production memory layer.

---

### app/core/decision_memory_engine.py
STATUS: KEEP

Purpose:
- strategic memory
- decision history
- reinforcement context
- cognition evolution

This is an ADVANCED cognition memory layer.

---

### app/core/conversation_memory.py
STATUS: KEEP

Purpose:
- active conversation state
- conversation continuity
- runtime context

---

## CONDITIONAL MEMORY SYSTEMS

### app/core/memory_engine.py
STATUS: REVIEW

Purpose:
- long-term memory
- adaptive cognition
- memory retrieval
- persistent cognition

Needs:
- integration review
- duplication analysis
- possible merge into canonical architecture

---

### app/core/memory_retrieval_engine.py
STATUS: REVIEW

Purpose:
- memory retrieval abstraction

Needs:
- compare against:
  - memory_service.py
  - decision_memory_engine.py
  - vector retrieval systems

---

## LEGACY / EXPERIMENTAL MEMORY SYSTEMS

### app/engine/memory_engine.py
STATUS: LEGACY

Reason:
- duplicate memory abstraction
- older cognition architecture

ACTION:
- archive candidate

---

### app/engine/memory_reflection_engine.py
STATUS: LEGACY RESEARCH

Purpose:
- experimental reflection memory

ACTION:
- move to research layer later

---

### app/engine/memory_reinforcement_engine.py
STATUS: REVIEW

Purpose:
- reinforcement learning for memory importance

Potentially valuable.

Needs:
- extraction review

---

### app/engine/memory_optimizer.py
STATUS: REVIEW

Purpose:
- memory strengthening
- confidence evolution

Potential merge candidate.

---

### app/engine/memory_consolidation_engine.py
STATUS: REVIEW

Purpose:
- memory ranking
- consolidation logic

Potential merge candidate.

---

## LEARNING MEMORY SYSTEMS

### app/learning/reinforcement_memory.py
STATUS: KEEP

Purpose:
- reinforcement experience tracking

---

### app/learning/strategy_memory_engine.py
STATUS: KEEP

Purpose:
- strategy learning memory
- strategy evolution

---

## MEMORY ARCHITECTURE TARGET

TARGET FLOW:

chat_routes.py
    ↓
chat_service.py
    ↓
memory_service.py
    ↓
decision_memory_engine.py
    ↓
advanced cognition memory systems

---

## CONSOLIDATION RULES

1. NO duplicate memory ownership
2. ALL runtime memory flows through memory_service.py
3. ALL strategic memory flows through decision_memory_engine.py
4. Experimental memory stays isolated
5. Legacy memory systems moved to archive later