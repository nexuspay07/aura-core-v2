"""Tenant-safe assembly of persisted enterprise context for Decision V2."""

from sqlalchemy import select

from app.db.business_profile_table import business_profile_table
from app.db.organization_table import organization_table
from app.db.user_table import user_table
from app.db.workspace_member_table import workspace_member_table
from app.db.workspace_table import workspace_table
from app.intelligence_v2.contracts import EvidenceItem, EvidenceSourceType


class ContextAccessError(PermissionError):
    """Raised when an identity cannot assemble the requested tenant context."""


class EnterpriseContextAssembler:
    """Reads persisted facts only; it never infers business conclusions."""

    def assemble(self, *, db, user_id: int, organization_id: int, workspace_id: int) -> tuple[dict, list[EvidenceItem]]:
        user = db.execute(select(user_table).where(user_table.c.id == user_id)).mappings().first()
        organization = db.execute(select(organization_table).where(organization_table.c.id == organization_id)).mappings().first()
        workspace = db.execute(select(workspace_table).where(workspace_table.c.id == workspace_id, workspace_table.c.organization_id == organization_id, workspace_table.c.is_active.is_(True))).mappings().first()
        membership = db.execute(select(workspace_member_table.c.id).where(workspace_member_table.c.workspace_id == workspace_id, workspace_member_table.c.user_id == user_id, workspace_member_table.c.is_active.is_(True))).first()
        if not user or not organization or not workspace or not membership:
            raise ContextAccessError("Workspace context is not accessible by this identity")
        profile = db.execute(select(business_profile_table).where(business_profile_table.c.organization_id == organization_id, business_profile_table.c.workspace_id == workspace_id, business_profile_table.c.is_active.is_(True))).mappings().first()

        identity = {field: user.get(field) for field in ("id", "email", "full_name", "role")}
        organization_context = {field: organization.get(field) for field in ("id", "name", "industry", "company_size", "account_type")}
        workspace_context = {field: workspace.get(field) for field in ("id", "name", "description", "workspace_type")}
        profile_fields = ("id", "business_name", "legal_name", "industry", "business_stage", "business_model", "mission", "vision", "description", "target_market", "target_customer", "geographic_focus", "products_services", "pricing_model", "business_goals", "current_challenges", "competitive_advantage")
        profile_context = {field: profile.get(field) for field in profile_fields} if profile else {}
        context = {"identity": identity, "organization": organization_context, "workspace": workspace_context, "business_profile": profile_context}
        evidence = [
            EvidenceItem(id=f"organization:{organization_id}", source_type=EvidenceSourceType.ORGANIZATION_PROFILE, source_name="organizations", structured_value=organization_context, organization_id=organization_id, permission_scope="organization", citation_label="Organization profile", provenance={"table": "organizations", "record_id": organization_id}),
            EvidenceItem(id=f"workspace:{workspace_id}", source_type=EvidenceSourceType.WORKSPACE_CONTEXT, source_name="workspaces", structured_value=workspace_context, organization_id=organization_id, workspace_id=workspace_id, permission_scope="workspace", citation_label="Workspace context", provenance={"table": "workspaces", "record_id": workspace_id}),
        ]
        if profile:
            evidence.append(EvidenceItem(id=f"business-profile:{profile['id']}", source_type=EvidenceSourceType.ORGANIZATION_PROFILE, source_name="business_profiles", structured_value=profile_context, organization_id=organization_id, workspace_id=workspace_id, permission_scope="workspace", citation_label="Business profile", provenance={"table": "business_profiles", "record_id": profile["id"]}))
        return context, evidence
