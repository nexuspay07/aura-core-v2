from datetime import datetime


# =====================================================
# IN-MEMORY STORE
# (Temporary phase before vector database)
# =====================================================

memory_store = {
    "users": {},
    "organizations": {},
    "sessions": {},
}


# =====================================================
# SAVE USER MEMORY
# =====================================================

def save_user_memory(
    user_id: str,
    memory_type: str,
    content: dict
):

    if user_id not in memory_store["users"]:
        memory_store["users"][user_id] = []

    memory_store["users"][user_id].append({
        "type": memory_type,
        "content": content,
        "timestamp": str(datetime.utcnow())
    })


# =====================================================
# GET USER MEMORIES
# =====================================================

def get_user_memories(
    user_id: str,
    limit: int = 10
):

    memories = memory_store["users"].get(
        user_id,
        []
    )

    return memories[-limit:]


# =====================================================
# SAVE ORGANIZATION MEMORY
# =====================================================

def save_organization_memory(
    organization_id: str,
    memory_type: str,
    content: dict
):

    if organization_id not in memory_store["organizations"]:
        memory_store["organizations"][organization_id] = []

    memory_store["organizations"][organization_id].append({
        "type": memory_type,
        "content": content,
        "timestamp": str(datetime.utcnow())
    })


# =====================================================
# GET ORGANIZATION MEMORIES
# =====================================================

def get_organization_memories(
    organization_id: str,
    limit: int = 20
):

    memories = memory_store["organizations"].get(
        organization_id,
        []
    )

    return memories[-limit:]


# =====================================================
# SAVE SESSION MEMORY
# =====================================================

def save_session_memory(
    session_id: str,
    role: str,
    message: str
):

    if session_id not in memory_store["sessions"]:
        memory_store["sessions"][session_id] = []

    memory_store["sessions"][session_id].append({
        "role": role,
        "message": message,
        "timestamp": str(datetime.utcnow())
    })


# =====================================================
# GET SESSION MEMORY
# =====================================================

def get_session_memory(
    session_id: str,
    limit: int = 20
):

    memories = memory_store["sessions"].get(
        session_id,
        []
    )

    return memories[-limit:]