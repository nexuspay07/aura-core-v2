"""Frozen metadata imports for the pre-commercial Alembic baseline."""
from app.db import business_profile_table, decision_memory_table, intelligence_session_table, knowledge_edge_table, knowledge_node_table, knowledge_table, memory_table, organization_invitation_table, organization_member_table, organization_table, simulation_history_table, usage_log_table, user_table, workspace_member_table, workspace_table  # noqa: F401
from app.db.database import metadata
from app.db.strategy import metadata as strategy_metadata
from sqlalchemy import MetaData


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

# Revisions after the frozen baseline own these columns.  The baseline must not
# accidentally create them just because the current ORM metadata has evolved.
_POST_BASELINE_COLUMNS = {
    "users": {"active_workspace_id"},
    "organizations": {"account_type"},
}


class _BaselineMetadata:
    """Expose only the tables owned by revision 20260728_0001."""

    def __init__(self, source_metadata):
        self._source_metadata = MetaData()
        for source in source_metadata.tables.values():
            if source.name in BASELINE_TABLE_NAMES:
                source.to_metadata(self._source_metadata)

        for table_name, column_names in _POST_BASELINE_COLUMNS.items():
            table = self._source_metadata.tables[table_name]
            for column_name in column_names:
                column = table.c[column_name]
                for constraint in list(table.foreign_key_constraints):
                    if any(item.name == column_name for item in constraint.columns):
                        table.foreign_key_constraints.remove(constraint)
                        table.constraints.remove(constraint)
                for constraint in list(table.constraints):
                    if (
                        column_name in constraint.columns.keys()
                        or column_name in str(getattr(constraint, "sqltext", ""))
                    ):
                        table.constraints.remove(constraint)
                        if constraint in table.foreign_key_constraints:
                            table.foreign_key_constraints.remove(constraint)
                for index in list(table.indexes):
                    if column_name in index.columns.keys():
                        table.indexes.remove(index)
                column.foreign_keys.clear()
                table._columns.remove(column)

    @property
    def sorted_tables(self):
        return [
            table
            for table in self._source_metadata.sorted_tables
        ]

    def create_all(self, bind, tables=None, **kwargs):
        self._source_metadata.create_all(bind=bind, tables=tables, **kwargs)


target_metadata = [_BaselineMetadata(metadata), strategy_metadata]
