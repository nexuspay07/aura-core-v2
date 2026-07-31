"""Canonical metadata discovery for Alembic; import every persisted table/model here."""
from app.db import business_profile_table, decision_memory_table, intelligence_session_table, knowledge_edge_table, knowledge_node_table, knowledge_table, memory_table, organization_invitation_table, organization_member_table, organization_table, simulation_history_table, usage_log_table, user_table, workspace_member_table, workspace_table  # noqa: F401
from app.db.database import metadata
from app.db.strategy import metadata as strategy_metadata
from app.commercial import models as commercial_models  # noqa: F401
from app.db import organization_orm  # noqa: F401

target_metadata = [metadata, strategy_metadata]
