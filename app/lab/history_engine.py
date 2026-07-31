from typing import Dict, List

from sqlalchemy.orm import Session

from app.lab.history_repository import history_repository


class HistoryEngine:
    """
    Coordinates simulation history operations.
    """

    def save(
        self,
        db: Session,
        organization_id: int,
        goal: str,
        scenario: Dict,
        result: Dict,
        **kwargs,
    ) -> int:

        return history_repository.save(
            db=db,
            organization_id=organization_id,
            goal=goal,
            scenario=scenario,
            result=result,
            **kwargs,
        )

    def get(
        self,
        db: Session,
        organization_id: int,
        limit: int = 100,
    ) -> List[Dict]:

        return history_repository.get(
            db=db,
            organization_id=organization_id,
            limit=limit,
        )

    def analyze_patterns(
        self,
        histories: List[Dict],
    ) -> Dict[str, int]:

        patterns = {}

        for history in histories:

            best = (
                history.get("result", {})
                .get("best_strategy", {})
            )

            name = best.get("name")

            if name:
                patterns[name] = (
                    patterns.get(name, 0) + 1
                )

        return patterns


history_engine = HistoryEngine()