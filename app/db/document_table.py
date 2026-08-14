"""Canonical V2 enterprise-document metadata and extracted text chunks."""
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint, func
from app.db.database import metadata

document_table = Table(
    "documents", metadata,
    Column("id", Integer, primary_key=True),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
    Column("uploaded_by_user_id", Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
    Column("filename", String(255), nullable=False),
    Column("original_filename", String(255), nullable=False),
    Column("mime_type", String(100), nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("source_type", String(32), nullable=False),
    Column("title", String(255), nullable=False),
    Column("description", Text, nullable=True),
    Column("checksum", String(64), nullable=False),
    Column("storage_key", String(512), nullable=True),
    Column("status", String(16), nullable=False, server_default="uploaded"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    Column("processed_at", DateTime(timezone=True), nullable=True),
    CheckConstraint("size_bytes >= 0", name="ck_documents_size_nonnegative"),
    CheckConstraint("status IN ('uploaded','processing','ready','failed','archived')", name="ck_documents_status"),
    CheckConstraint("source_type IN ('uploaded_file','policy','contract','report','procedure','strategy_document','financial_document','operational_document','research','other')", name="ck_documents_source_type"),
    UniqueConstraint("organization_id", "workspace_id", "checksum", name="uq_documents_scope_checksum"),
)
Index("ix_documents_org_workspace", document_table.c.organization_id, document_table.c.workspace_id)
Index("ix_documents_org_checksum", document_table.c.organization_id, document_table.c.checksum)
Index("ix_documents_status", document_table.c.status)

document_chunk_table = Table(
    "document_chunks", metadata,
    Column("id", Integer, primary_key=True),
    Column("document_id", Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("organization_id", Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
    Column("workspace_id", Integer, ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
    Column("chunk_index", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("page_number", Integer, nullable=True),
    Column("section", String(255), nullable=True),
    Column("embedding", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("chunk_index >= 0", name="ck_document_chunks_index_nonnegative"),
    UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_order"),
)
Index("ix_document_chunks_org_workspace", document_chunk_table.c.organization_id, document_chunk_table.c.workspace_id)
Index("ix_document_chunks_document", document_chunk_table.c.document_id)
