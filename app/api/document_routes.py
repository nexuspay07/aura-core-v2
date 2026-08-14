"""Authenticated, tenant-hidden V2 document APIs.  No public sharing exists."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.api.auth_routes import get_current_user_from_token
from app.db.database import SessionLocal
from app.intelligence_v2.documents import DocumentAccessError, DocumentError, DuplicateDocumentError, document_ingestion_service

router=APIRouter(prefix="/knowledge/documents",tags=["Knowledge Documents"]); security=HTTPBearer()
async def current(c:HTTPAuthorizationCredentials=Depends(security)): return await get_current_user_from_token(c)
def ids(identity):
    user=(identity or {}).get("user"); organization=(identity or {}).get("organization"); workspace=(identity or {}).get("workspace")
    if not user or not organization: raise HTTPException(status_code=404,detail="Workspace not found")
    return user["id"],organization["id"],workspace.get("id") if workspace else None
def public(row): return {key:(value.isoformat() if hasattr(value,"isoformat") else value) for key,value in row.items() if key != "storage_key"}
@router.post("",status_code=201)
async def upload_document(file:UploadFile=File(...),source_type:str=Form("uploaded_file"),title:str|None=Form(None),description:str|None=Form(None),identity=Depends(current)):
    user_id,organization_id,workspace_id=ids(identity); db=SessionLocal()
    try:
        row=document_ingestion_service.ingest(db=db,organization_id=organization_id,workspace_id=workspace_id,user_id=user_id,original_filename=file.filename or "document.txt",mime_type=file.content_type or "text/plain",content=await file.read(),source_type=source_type,title=title,description=description); db.commit(); return public(row)
    except DuplicateDocumentError as error: db.rollback(); raise HTTPException(409,detail=str(error))
    except DocumentError as error: db.rollback(); raise HTTPException(422,detail=str(error))
    except DocumentAccessError as error: db.rollback(); raise HTTPException(404,detail=str(error))
    except Exception: db.rollback(); raise HTTPException(500,detail="Document processing failed")
    finally: db.close()
@router.get("")
async def list_documents(identity=Depends(current)):
    user_id,organization_id,workspace_id=ids(identity); db=SessionLocal()
    try: return [public(row) for row in document_ingestion_service.list(db=db,organization_id=organization_id,workspace_id=workspace_id)]
    finally: db.close()
@router.get("/{document_id}")
async def get_document(document_id:int,identity=Depends(current)):
    _,organization_id,workspace_id=ids(identity); db=SessionLocal()
    try: return public(document_ingestion_service.get_owned(db=db,document_id=document_id,organization_id=organization_id,workspace_id=workspace_id))
    except DocumentAccessError as error: raise HTTPException(404,detail=str(error))
    finally: db.close()
@router.delete("/{document_id}")
async def archive_document(document_id:int,identity=Depends(current)):
    _,organization_id,workspace_id=ids(identity); db=SessionLocal()
    try: document_ingestion_service.archive(db=db,document_id=document_id,organization_id=organization_id,workspace_id=workspace_id); db.commit(); return {"success":True}
    except DocumentAccessError as error: db.rollback(); raise HTTPException(404,detail=str(error))
    finally: db.close()
