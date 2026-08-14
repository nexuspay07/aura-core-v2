"""add V2 enterprise document metadata and chunks

Revision ID: 20260809_0019
Revises: 20260808_0018
"""
from alembic import op
import sqlalchemy as sa

revision = "20260809_0019"
down_revision = "20260808_0018"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("mime_type", sa.String(100), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("source_type", sa.String(32), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("checksum", sa.String(64), nullable=False), sa.Column("storage_key", sa.String(512), nullable=True), sa.Column("status", sa.String(16), nullable=False, server_default="uploaded"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("size_bytes >= 0", name="ck_documents_size_nonnegative"), sa.CheckConstraint("status IN ('uploaded','processing','ready','failed','archived')", name="ck_documents_status"), sa.CheckConstraint("source_type IN ('uploaded_file','policy','contract','report','procedure','strategy_document','financial_document','operational_document','research','other')", name="ck_documents_source_type"), sa.UniqueConstraint("organization_id","workspace_id","checksum",name="uq_documents_scope_checksum"))
    op.create_index("ix_documents_org_workspace", "documents", ["organization_id","workspace_id"]); op.create_index("ix_documents_org_checksum", "documents", ["organization_id","checksum"]); op.create_index("ix_documents_status", "documents", ["status"])
    op.create_table("document_chunks", sa.Column("id",sa.Integer(),primary_key=True),sa.Column("document_id",sa.Integer(),sa.ForeignKey("documents.id",ondelete="CASCADE"),nullable=False),sa.Column("organization_id",sa.Integer(),sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("workspace_id",sa.Integer(),sa.ForeignKey("workspaces.id",ondelete="RESTRICT"),nullable=True),sa.Column("chunk_index",sa.Integer(),nullable=False),sa.Column("content",sa.Text(),nullable=False),sa.Column("page_number",sa.Integer(),nullable=True),sa.Column("section",sa.String(255),nullable=True),sa.Column("embedding",sa.Text(),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),sa.CheckConstraint("chunk_index >= 0",name="ck_document_chunks_index_nonnegative"),sa.UniqueConstraint("document_id","chunk_index",name="uq_document_chunks_order"))
    op.create_index("ix_document_chunks_org_workspace", "document_chunks", ["organization_id","workspace_id"]); op.create_index("ix_document_chunks_document", "document_chunks", ["document_id"])
def downgrade():
    op.drop_table("document_chunks"); op.drop_table("documents")
