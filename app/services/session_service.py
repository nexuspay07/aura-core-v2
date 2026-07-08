from sqlalchemy import (
    insert,
    select,
    update
)

from app.db.database import (
    SessionLocal
)

from app.db.intelligence_session_table import (
    intelligence_session_table
)


class SessionService:
    """
    ======================================================

                    SESSION SERVICE

    Responsible for managing Intelligence Sessions.

    Responsibilities

    • Create Session
    • Update Session
    • Retrieve Session
    • List Sessions

    This service MUST NOT contain any
    AI reasoning logic.

    ======================================================
    """

    def create_session(

        self,

        *,

        organization_id: int,

        workspace_id: int,

        created_by_user_id: int,

        title: str,

        goal: str,

        domain: str,

        session_type: str,

        status: str,

        summary: str,

        recommended_move: str,

        risk_level: str,

        report_json: dict,

        business_model: str,

        is_active: bool = True

    ) -> int:

        db = SessionLocal()

        try:

            query = insert(
                intelligence_session_table
            ).values(

                organization_id=organization_id,

                workspace_id=workspace_id,

                created_by_user_id=created_by_user_id,

                title=title,

                goal=goal,

                domain=domain,

                session_type=session_type,

                status=status,

                summary=summary,

                recommended_move=recommended_move,

                risk_level=risk_level,

                report_json=report_json,

                business_model=business_model,

                is_active=is_active

            )

            result = db.execute(query)

            db.commit()

            return result.inserted_primary_key[0]

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()

    def get_session(

        self,

        session_id: int

    ):

        db = SessionLocal()

        try:

            query = (

                select(
                    intelligence_session_table
                )

                .where(

                    intelligence_session_table.c.id

                    == session_id

                )

            )

            result = db.execute(query)

            row = result.fetchone()

            if not row:

                return None

            return dict(row._mapping)

        finally:

            db.close()

    def list_sessions(

        self,

        organization_id: int,

        workspace_id: int

    ):

        db = SessionLocal()

        try:

            query = (

                select(
                    intelligence_session_table
                )

                .where(

                    intelligence_session_table.c.organization_id
                    == organization_id

                )

                .where(

                    intelligence_session_table.c.workspace_id
                    == workspace_id

                )

                .order_by(

                    intelligence_session_table.c.created_at.desc()

                )

            )

            result = db.execute(query)

            return [

                dict(row._mapping)

                for row in result.fetchall()

            ]

        finally:

            db.close()

    def update_status(

        self,

        session_id: int,

        status: str

    ):

        db = SessionLocal()

        try:

            query = (

                update(
                    intelligence_session_table
                )

                .where(

                    intelligence_session_table.c.id

                    == session_id

                )

                .values(

                    status=status

                )

            )

            db.execute(query)

            db.commit()

        except Exception:

            db.rollback()
            raise

        finally:

            db.close()


session_service = SessionService()