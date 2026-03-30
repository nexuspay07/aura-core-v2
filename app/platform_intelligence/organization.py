from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

router = APIRouter(
    prefix="/platform",
    tags=["Platform Layer"]
)

# In-memory storage (safe for Phase 122)
ORGANIZATIONS = []

# Request model
class OrganizationCreate(BaseModel):
    name: str
    industry: str
    size: int

# Response model
class OrganizationResponse(BaseModel):
    id: str
    name: str
    industry: str
    size: int
    created_at: datetime


# Register organization
@router.post("/organization/register", response_model=OrganizationResponse)
def register_organization(org: OrganizationCreate):

    organization = {
        "id": str(uuid.uuid4()),
        "name": org.name,
        "industry": org.industry,
        "size": org.size,
        "created_at": datetime.utcnow()
    }

    ORGANIZATIONS.append(organization)

    return organization


# List organizations
@router.get("/organizations", response_model=List[OrganizationResponse])
def list_organizations():
    return ORGANIZATIONS


# Platform status
@router.get("/status")
def platform_status():
    return {
        "platform": "Aura AI Platform Layer",
        "status": "operational",
        "organizations_registered": len(ORGANIZATIONS),
        "timestamp": datetime.utcnow()
    }