"""Tenant-safe document ingestion, storage seam, chunking and V2 retrieval."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.db.document_table import document_chunk_table, document_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.intelligence_v2.contracts import EvidenceItem, EvidenceSourceType
from app.intelligence_v2.embeddings import EmbeddingProvider, configured_embedding_provider, cosine_similarity, deterministic_embedding_provider
from app.intelligence_v2.retrieval import _tokens, _utc

SOURCE_TYPES = {"uploaded_file", "policy", "contract", "report", "procedure", "strategy_document", "financial_document", "operational_document", "research", "other"}
SUPPORTED_TYPES = {"text/plain", "text/markdown", "text/x-markdown"}

class DocumentError(ValueError): pass
class DocumentAccessError(PermissionError): pass
class DuplicateDocumentError(DocumentError): pass

class FileStorage:
    def save(self, key: str, content: bytes) -> str: raise NotImplementedError
    def delete(self, key: str | None) -> None: raise NotImplementedError

class LocalFileStorage(FileStorage):
    """Development-only adapter; production can replace it without domain changes."""
    def __init__(self, root: str | Path | None = None): self.root = Path(root or os.getenv("AURA_DOCUMENT_STORAGE_DIR", "data/documents"))
    def save(self, key: str, content: bytes) -> str:
        path = self.root / key; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content); return key
    def delete(self, key: str | None) -> None:
        if key:
            path = self.root / key
            if path.exists(): path.unlink()

@dataclass(frozen=True)
class DocumentChunk:
    content: str
    index: int
    section: str | None = None
    page_number: int | None = None

class DeterministicChunker:
    def __init__(self, max_chars: int = 1200, overlap_chars: int = 160): self.max_chars=max_chars; self.overlap_chars=overlap_chars
    def chunk(self, text: str) -> list[DocumentChunk]:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if part.strip()]
        chunks=[]; buffer=""; section=None
        for paragraph in paragraphs:
            if re.match(r"^#{1,6}\s+", paragraph): section=re.sub(r"^#{1,6}\s+", "", paragraph).strip()
            candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
            if buffer and len(candidate) > self.max_chars:
                chunks.append(DocumentChunk(buffer, len(chunks), section)); buffer = buffer[-self.overlap_chars:] + "\n\n" + paragraph
            else: buffer = candidate
        if buffer: chunks.append(DocumentChunk(buffer, len(chunks), section))
        return chunks

class DocumentIngestionService:
    def __init__(self, storage: FileStorage | None = None, chunker: DeterministicChunker | None = None, embedding_provider: EmbeddingProvider | None = None):
        self.storage=storage or LocalFileStorage(); self.chunker=chunker or DeterministicChunker(); self.embedding_provider=embedding_provider or configured_embedding_provider()
    def _owned_workspace(self, db, *, organization_id: int, workspace_id: int | None, user_id: int) -> int | None:
        if workspace_id is None: return None
        workspace=db.execute(select(workspace_table.c.id).where(workspace_table.c.id==workspace_id, workspace_table.c.organization_id==organization_id, workspace_table.c.is_active.is_(True))).first()
        membership=db.execute(select(workspace_member_table.c.id).where(workspace_member_table.c.workspace_id==workspace_id, workspace_member_table.c.user_id==user_id, workspace_member_table.c.is_active.is_(True))).first()
        if not workspace or not membership: raise DocumentAccessError("Document not found")
        return workspace_id
    def ingest(self, *, db, organization_id: int, workspace_id: int | None, user_id: int, original_filename: str, mime_type: str, content: bytes, source_type: str="uploaded_file", title: str | None=None, description: str | None=None):
        if mime_type not in SUPPORTED_TYPES: raise DocumentError("Unsupported document type; TXT and Markdown are supported")
        if not content: raise DocumentError("Document is empty")
        if len(content) > 10 * 1024 * 1024: raise DocumentError("Document exceeds the 10 MB limit")
        if source_type not in SOURCE_TYPES: raise DocumentError("Unsupported document source type")
        try: text=content.decode("utf-8")
        except UnicodeDecodeError as error: raise DocumentError("Document must be UTF-8 text") from error
        normalized=text.replace("\x00", "").strip()
        if not normalized: raise DocumentError("Document contains no readable text")
        workspace_id=self._owned_workspace(db, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id)
        checksum=sha256(content).hexdigest()
        duplicate=db.execute(select(document_table.c.id).where(document_table.c.organization_id==organization_id, document_table.c.workspace_id.is_(workspace_id) if workspace_id is None else document_table.c.workspace_id==workspace_id, document_table.c.checksum==checksum, document_table.c.status != "archived")).first()
        if duplicate: raise DuplicateDocumentError("An identical document already exists in this tenant scope")
        key=f"{organization_id}/{uuid4().hex}-{Path(original_filename).name}"; stored=False
        try:
            storage_key=self.storage.save(key, content); stored=True
            result=db.execute(document_table.insert().values(organization_id=organization_id, workspace_id=workspace_id, uploaded_by_user_id=user_id, filename=Path(original_filename).name, original_filename=original_filename, mime_type=mime_type, size_bytes=len(content), source_type=source_type, title=(title or Path(original_filename).stem)[:255], description=description, checksum=checksum, storage_key=storage_key, status="processing"))
            document_id=result.inserted_primary_key[0]
            chunks=self.chunker.chunk(normalized)
            vectors=self.embedding_provider.embed_many([chunk.content for chunk in chunks])
            db.execute(document_chunk_table.insert(), [{"document_id":document_id,"organization_id":organization_id,"workspace_id":workspace_id,"chunk_index":chunk.index,"content":chunk.content,"page_number":chunk.page_number,"section":chunk.section,"embedding": ",".join(f"{value:.8f}" for value in vector)} for chunk,vector in zip(chunks,vectors)])
            db.execute(update(document_table).where(document_table.c.id==document_id).values(status="ready",processed_at=datetime.now(timezone.utc)))
            db.flush()
            return db.execute(select(document_table).where(document_table.c.id==document_id)).mappings().one()
        except IntegrityError as error:
            if stored: self.storage.delete(key)
            raise DuplicateDocumentError("An identical document already exists in this tenant scope") from error
        except Exception:
            if stored: self.storage.delete(key)
            raise
    def list(self, *, db, organization_id: int, workspace_id: int | None):
        query=select(document_table).where(document_table.c.organization_id==organization_id, document_table.c.status != "archived")
        if workspace_id is not None: query=query.where(or_(document_table.c.workspace_id.is_(None),document_table.c.workspace_id==workspace_id))
        return db.execute(query.order_by(document_table.c.created_at.desc(),document_table.c.id.desc())).mappings().all()
    def get_owned(self, *, db, document_id: int, organization_id: int, workspace_id: int | None):
        query=select(document_table).where(document_table.c.id==document_id,document_table.c.organization_id==organization_id,document_table.c.status != "archived")
        if workspace_id is not None: query=query.where(or_(document_table.c.workspace_id.is_(None),document_table.c.workspace_id==workspace_id))
        item=db.execute(query).mappings().first()
        if not item: raise DocumentAccessError("Document not found")
        return item
    def archive(self, *, db, document_id: int, organization_id: int, workspace_id: int | None):
        document=self.get_owned(db=db,document_id=document_id,organization_id=organization_id,workspace_id=workspace_id)
        db.execute(delete(document_chunk_table).where(document_chunk_table.c.document_id==document_id))
        db.execute(update(document_table).where(document_table.c.id==document_id).values(status="archived")); db.flush()
        return document

class DocumentEvidenceRetriever:
    candidate_limit=150; returned_limit=12
    def __init__(self, embedding_provider: EmbeddingProvider = deterministic_embedding_provider): self.embedding_provider=embedding_provider
    def retrieve(self, *, db, organization_id: int, workspace_id: int, query: str, limit: int | None=None) -> list[EvidenceItem]:
        rows=db.execute(select(document_chunk_table, document_table.c.title, document_table.c.original_filename, document_table.c.source_type, document_table.c.created_at.label("document_created_at")).join(document_table,document_table.c.id==document_chunk_table.c.document_id).where(document_chunk_table.c.organization_id==organization_id, document_table.c.status=="ready",or_(document_chunk_table.c.workspace_id.is_(None),document_chunk_table.c.workspace_id==workspace_id)).order_by(document_chunk_table.c.id.desc()).limit(self.candidate_limit)).mappings().all()
        tokens=_tokens(query); qv=self.embedding_provider.embed(query); ranked=[]
        for row in rows:
            ctokens=_tokens(row["content"]); lexical=len(tokens & ctokens)/max(1,len(tokens|ctokens)); numeric=0.2 if any(t in ctokens for t in tokens if any(c.isdigit() for c in t)) else 0; vector=[float(v) for v in row["embedding"].split(",")] if row.get("embedding") else []
            score=.65*lexical+.25*cosine_similarity(qv,vector)+numeric+.05
            page_label = f", page {row['page_number']}" if row.get("page_number") else ""
            section_label = f", {row['section']}" if row.get("section") else ""
            citation = f"{row['title']}{page_label}{section_label}"
            ranked.append((score,row["id"],EvidenceItem(id=f"document-chunk:{row['id']}",source_type=EvidenceSourceType.KNOWLEDGE_DOCUMENT,source_name=row["title"],content=row["content"],organization_id=organization_id,workspace_id=row["workspace_id"],timestamp=_utc(row["document_created_at"]),freshness="persisted document",reliability="untrusted_document",permission_scope="workspace" if row["workspace_id"] else "organization",citation_label=citation,provenance={"document_id":row["document_id"],"chunk_id":row["id"],"filename":row["original_filename"],"page":row.get("page_number"),"section":row.get("section"),"score":round(score,6),"untrusted_content":True})))
        ranked.sort(key=lambda item:(-item[0],-item[1])); return [item for _,_,item in ranked[:limit or self.returned_limit]]

document_ingestion_service=DocumentIngestionService(); document_evidence_retriever=DocumentEvidenceRetriever()
