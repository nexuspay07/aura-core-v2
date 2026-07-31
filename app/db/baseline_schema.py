"""Frozen metadata imports for the pre-commercial Alembic baseline."""
from app.db import business_profile_table, decision_memory_table, intelligence_session_table, knowledge_edge_table, knowledge_node_table, knowledge_table, memory_table, organization_invitation_table, organization_member_table, organization_table, simulation_history_table, usage_log_table, user_table, workspace_member_table, workspace_table  # noqa: F401
from app.db.database import metadata
from app.db.strategy import metadata as strategy_metadata


BASELINE_TABLE_NAMES = frozenset(
    {
        "users",
        "organizations",
        "organization_members",
        "organization_invitations",
        "workspaces",
        "workspace_members",
        "business_profiles",
        "decision_memory",
        "intelligence_sessions",
        "knowledge_edges",
        "knowledge_nodes",
        "knowledge",
        "memory",
        "simulation_history",
        "usage_logs",
    }
)


class _BaselineMetadata:
    """Expose only the tables owned by revision 20260728_0001."""

    def __init__(self, source_metadata):
        self._source_metadata = source_metadata

    @property
    def sorted_tables(self):
        return [
            table
            for table in self._source_metadata.sorted_tables
            if table.name in BASELINE_TABLE_NAMES
        ]

    def create_all(self, bind, tables=None, **kwargs):
        self._source_metadata.create_all(bind=bind, tables=tables, **kwargs)


target_metadata = [_BaselineMetadata(metadata), strategy_metadata]
