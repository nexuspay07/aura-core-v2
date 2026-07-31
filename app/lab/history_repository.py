from typing import List, Optional

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.db.simulation_history_table import simulation_history_table


class HistoryRepository:

    def save(
        self,
        db: Session,
        organization_id: int,
        goal: str,
        scenario: dict,
        result: dict,
        workspace_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> int:

        record = db.execute(
            insert(simulation_history_table).values(
                organization_id=organization_id,
                workspace_id=workspace_id,
                user_id=user_id,
                goal=goal,
                scenario=scenario,
                result=result,
            )
        )

        db.commit()

        return record.inserted_primary_key[0]

    def get(
        self,
        db: Session,
        organization_id: int,
        limit: int = 100,
    ) -> List[dict]:

        result = db.execute(
            select(simulation_history_table)
            .where(
                simulation_history_table.c.organization_id
                == organization_id
            )
            .order_by(
                simulation_history_table.c.created_at.desc()
            )
            .limit(limit)
        )

        return result.mappings().all()


history_repository = HistoryRepository()