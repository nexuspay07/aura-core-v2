"""Frozen metadata for the schema owned by Alembic revision 20260728_0001."""
from copy import copy

from sqlalchemy import (
    CheckConstraint,
    Column,
    DefaultClause,
    ForeignKeyConstraint,
    Index,
    MetaData,
    Table,
    UniqueConstraint,
)

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

# These objects belong to 20260807_0017, not the frozen baseline.
_POST_BASELINE_COLUMNS = {
    "users": frozenset({"active_workspace_id"}),
    "organizations": frozenset({"account_type"}),
}


def _column_copy(column):
    """Build an unbound column without importing current foreign-key state."""
    server_default = (
        DefaultClause(copy(column.server_default.arg))
        if column.server_default is not None
        else None
    )
    return Column(
        column.name,
        copy(column.type),
        key=column.key,
        primary_key=column.primary_key,
        nullable=column.nullable,
        server_default=server_default,
        autoincrement=column.autoincrement,
        comment=column.comment,
    )


def _mentions_removed_column(constraint, removed):
    local_columns = set(constraint.columns.keys())
    if local_columns & removed:
        return True
    sqltext = str(getattr(constraint, "sqltext", ""))
    return any(name in sqltext for name in removed)


class _BaselineMetadata:
    """Construct baseline tables from public SQLAlchemy schema objects only."""

    def __init__(self, source_metadata):
        frozen = MetaData(naming_convention=source_metadata.naming_convention)

        # Create every table and historical column first. No current FK object is
        # copied, so deferred PostgreSQL constraints cannot retain removed columns.
        for source in source_metadata.tables.values():
            if source.name not in BASELINE_TABLE_NAMES:
                continue
            removed = _POST_BASELINE_COLUMNS.get(source.name, frozenset())
            Table(
                source.name,
                frozen,
                *(_column_copy(column) for column in source.columns if column.name not in removed),
                schema=source.schema,
                comment=source.comment,
            )

        # Recreate only constraints whose complete local and remote shape exists
        # in the frozen schema.
        for source in source_metadata.tables.values():
            if source.name not in BASELINE_TABLE_NAMES:
                continue
            target = frozen.tables[source.key]
            removed = _POST_BASELINE_COLUMNS.get(source.name, frozenset())
            for constraint in source.constraints:
                if _mentions_removed_column(constraint, removed):
                    continue
                if isinstance(constraint, ForeignKeyConstraint):
                    local = [element.parent.name for element in constraint.elements]
                    remote = [element.target_fullname for element in constraint.elements]
                    if any(name not in target.c for name in local):
                        continue
                    for reference in remote:
                        table_name, column_name = reference.rsplit(".", 1)
                        if table_name not in frozen.tables or column_name not in frozen.tables[table_name].c:
                            raise ValueError(f"Invalid frozen baseline foreign key: {source.name}.{local} -> {reference}")
                    target.append_constraint(
                        ForeignKeyConstraint(
                            local,
                            remote,
                            name=constraint.name,
                            onupdate=constraint.onupdate,
                            ondelete=constraint.ondelete,
                            deferrable=constraint.deferrable,
                            initially=constraint.initially,
                            use_alter=constraint.use_alter,
                            match=constraint.match,
                        )
                    )
                elif isinstance(constraint, UniqueConstraint):
                    target.append_constraint(
                        UniqueConstraint(
                            *(target.c[name] for name in constraint.columns.keys()),
                            name=constraint.name,
                            deferrable=constraint.deferrable,
                            initially=constraint.initially,
                        )
                    )
                elif isinstance(constraint, CheckConstraint):
                    target.append_constraint(
                        CheckConstraint(copy(constraint.sqltext), name=constraint.name)
                    )

            for index in source.indexes:
                names = [column.name for column in index.columns]
                if set(names) & removed or any(name not in target.c for name in names):
                    continue
                Index(
                    index.name,
                    *(target.c[name] for name in names),
                    unique=index.unique,
                    **dict(index.dialect_kwargs),
                )

        self._source_metadata = frozen

    @property
    def tables(self):
        return self._source_metadata.tables

    @property
    def sorted_tables(self):
        return self._source_metadata.sorted_tables

    def create_all(self, bind, tables=None, **kwargs):
        self._source_metadata.create_all(bind=bind, tables=tables, **kwargs)


target_metadata = [_BaselineMetadata(metadata), strategy_metadata]
