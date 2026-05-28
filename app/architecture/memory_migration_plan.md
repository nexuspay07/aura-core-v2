# AURA MEMORY MIGRATION PLAN

---

# PURPOSE

Track consolidation and migration of all memory systems inside AURA.

Goal:
- eliminate duplication
- define canonical memory systems
- preserve valuable research
- stabilize cognition memory architecture

---

# OFFICIAL MEMORY OWNER

Canonical production memory system:

```text
app/memory
```

Canonical persistence layer:

```text
app/db
```

---

# MEMORY CLASSIFICATION RULES

---

## KEEP
Official production systems.

---

## MERGE
Useful logic to integrate into canonical systems.

---

## ARCHIVE
Obsolete or duplicated systems.

Move into:
```text
app/_archive
```

---

## RESEARCH
Experimental memory systems.

Remain isolated from production cognition.

---

# MEMORY SYSTEM AUDIT

---

# intelligence_memory.py

Location:
```text
app/memory/intelligence_memory.py
```

Classification:
PARTIAL / RESEARCH

Reason:
JSON-based temporary memory system.

Problems:
- non-scalable
- isolated persistence
- bypasses unified memory architecture

Future Action:
Archive OR merge useful logic into unified memory services.

---

# memory_manager.py

Location:
```text
app/memory/memory_manager.py
```

Classification:
PARTIAL

Reason:
Useful abstraction layer but not persistent/scalable.

Problems:
- in-memory only
- isolated memory flow
- not integrated with semantic memory

Future Action:
Merge concepts into unified memory orchestration.

---

# vector_engine.py

Location:
```text
app/memory/vector_engine.py
```

Classification:
KEEP

Reason:
Core semantic cognition infrastructure.

Responsibilities:
- embeddings
- semantic similarity
- vector cognition

Future Action:
Expand into official semantic cognition engine.

---

# vector_memory.py

Location:
```text
app/memory/vector_memory.py
```

Classification:
PARTIAL / FUTURE

Reason:
Potential semantic memory layer.

Current Status:
Incomplete.

Future Action:
Review for future semantic memory integration.

---

# vector_search.py

Location:
```text
app/memory/vector_search.py
```

Classification:
PARTIAL / FUTURE

Reason:
Potential semantic retrieval layer.

Current Status:
Incomplete.

Future Action:
Review later during semantic cognition upgrades.

---

# vector_retriever.py

Location:
```text
app/memory/vector_retriever.py
```

Classification:
KEEP

Reason:
Supports semantic retrieval architecture.

Future Action:
Integrate into unified semantic retrieval pipeline.

---

# memory_retriever.py

Location:
```text
app/memory/memory_retriever.py
```

Classification:
KEEP

Reason:
Official memory retrieval layer candidate.

Future Action:
Become canonical retrieval interface.

---

# memory_service.py

Location:
```text
app/memory/memory_service.py
```

Classification:
KEEP

Reason:
Canonical service-layer candidate.

Future Action:
Expand into centralized memory orchestration service.

---

# memory_repository.py

Location:
```text
app/memory/memory_repository.py
```

Classification:
KEEP

Reason:
Persistence abstraction layer.

Future Action:
Standardize repository architecture.

---

# memory_schema.py

Location:
```text
app/memory/memory_schema.py
```

Classification:
KEEP

Reason:
Useful schema standardization layer.

---

# memory_models.py

Location:
```text
app/memory/memory_models.py
```

Classification:
MERGE

Reason:
Model overlap with db models.

Future Action:
Move persistence models into:
```text
app/db
```

---

# conversation_memory_model.py

Location:
```text
app/db/conversation_memory_model.py
```

Classification:
KEEP

Reason:
Canonical persistent conversation memory model.

---

# reinforcement memory systems

Classification:
FUTURE INTEGRATION

Reason:
Still fragmented across:
- reinforcement systems
- strategic evolution
- telemetry

Future Action:
Centralize under unified cognition memory.

---

# OFFICIAL MEMORY DIRECTION

Future architecture:

```text
working memory
↓
conversation memory
↓
semantic memory
↓
decision memory
↓
reinforcement memory
↓
organizational memory
↓
strategic evolution memory
```

---

# IMMEDIATE CONSOLIDATION RULES

---

## RULE 1
All production memory logic flows through:

```text
app/memory
```

---

## RULE 2
Persistence models belong to:

```text
app/db
```

---

## RULE 3
Core systems consume memory — not create isolated memory systems.

---

## RULE 4
Semantic retrieval becomes the future foundation of adaptive cognition.

---

# CURRENT CONSOLIDATION STATUS

---

## Semantic Memory
PARTIALLY ACTIVE

---

## Conversation Memory
ACTIVE

---

## Reinforcement Memory
EARLY STAGE

---

## Organizational Memory
FUTURE

---

## Strategic Evolution Memory
PARTIAL

---

# NEXT CONSOLIDATION PHASE

After memory stabilization:
- orchestration stabilization
- telemetry stabilization
- agent consolidation
- reasoning consolidation