from app.services.unified_context_service import (
    unified_context_service
)


class AuraContextService:
    """
    =======================================================
                    AURA CONTEXT SERVICE

    The Aura Context Service is the highest-level
    context builder in the platform.

    Every major Aura capability should obtain its
    organizational understanding from here.

    Responsibilities

    • Identity
    • Organization
    • Workspace
    • Business DNA
    • Unified Context

    Future Versions

    • Memory
    • Marketplace
    • Knowledge
    • Permissions
    • Activity
    • Intelligence
    • Simulation

    =======================================================
    """

    def build(

        self,

        db,

        organization_id: int,

        workspace_id: int,

        user: dict

    ):

        unified_context = (
            unified_context_service.build(

                db=db,

                organization_id=organization_id,

                workspace_id=workspace_id

            )
        )

        return {

            # -----------------------
            # USER IDENTITY
            # -----------------------

            "identity": {

                "id": user.get("id"),

                "email": user.get("email"),

                "first_name": user.get("first_name"),

                "last_name": user.get("last_name"),

                "role": user.get("role")

            },

            # -----------------------
            # ORGANIZATION CONTEXT
            # -----------------------

            "organization": unified_context.get(

                "business",

                {}

            ).get(

                "organization",

                {}

            ),

            # -----------------------
            # WORKSPACE CONTEXT
            # -----------------------

            "workspace": unified_context.get(

                "business",

                {}

            ).get(

                "workspace",

                {}

            ),

            # -----------------------
            # BUSINESS CONTEXT
            # -----------------------

            "business": unified_context.get(

                "business",

                {}

            ),

            # -----------------------
            # COMPLETE CONTEXT
            # -----------------------

            "unified_context": unified_context

        }


aura_context_service = AuraContextService()