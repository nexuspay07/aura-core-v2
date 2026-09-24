"""Controlled application workflow for durable canonical Strategies."""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.strategy.capability import StrategyCapability, strategy_capability
from app.strategy.contracts import StrategyInput, StrategyResult, StrategyScope
from app.strategy.persistence import (
    PersistedStrategy,
    StrategyPersistenceConflictError,
    StrategyPersistenceError,
    StrategyPersistenceNotFoundError,
    StrategyRepository,
    normalize_strategy_title,
    strategy_repository,
)
from app.strategy.idempotency import (
    StrategyCreateClaimState,
    StrategyCreateIdempotencyRepository,
    StrategyIdempotencyCompletionError,
    StrategyIdempotencyError,
    strategy_create_idempotency_repository,
    strategy_create_request_fingerprint,
)
from app.strategy.validation import (
    StrategyValidationError,
    validate_strategy_input,
    validate_strategy_result,
)


class StrategyApplicationError(ValueError):
    """Base error for controlled Strategy persistence workflows."""


class StrategyApplicationValidationError(StrategyApplicationError):
    pass


class StrategyApplicationPersistenceError(StrategyApplicationError):
    pass


class StrategyApplicationNotFoundError(StrategyApplicationError):
    pass


class StrategyApplicationConflictError(StrategyApplicationError):
    pass


class StrategyApplicationInProgressError(StrategyApplicationConflictError):
    pass


class StrategyApplicationService:
    """Coordinate canonical intelligence and persistence without HTTP concerns."""

    def __init__(
        self,
        capability: StrategyCapability | None = None,
        repository: StrategyRepository | None = None,
        idempotency_repository: StrategyCreateIdempotencyRepository | None = None,
    ) -> None:
        self.capability = capability or strategy_capability
        self.repository = repository or strategy_repository
        self.idempotency_repository = idempotency_repository or strategy_create_idempotency_repository

    def generate_and_persist_idempotent_direct_strategy(
        self,
        db,
        *,
        strategy_input: StrategyInput,
        title: str,
        created_by_user_id: int,
        idempotency_key: str,
    ) -> PersistedStrategy:
        """Claim, generate without an open transaction, then commit atomically."""

        normalized_title = self._title(title)
        self._creator(created_by_user_id)
        try:
            validate_strategy_input(strategy_input)
            fingerprint = strategy_create_request_fingerprint(
                title=normalized_title,
                strategy_input=strategy_input,
            )
            claim = self.idempotency_repository.claim(
                db,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                actor_user_id=created_by_user_id,
                scope=strategy_input.scope,
            )
            db.commit()
        except (StrategyValidationError, StrategyIdempotencyError) as error:
            db.rollback()
            raise StrategyApplicationValidationError("Invalid persistent Strategy request") from error
        except SQLAlchemyError as error:
            db.rollback()
            raise StrategyApplicationPersistenceError("Unable to coordinate Strategy creation") from error

        if claim.state is StrategyCreateClaimState.CONFLICT:
            raise StrategyApplicationConflictError("Idempotency key conflicts with another request")
        if claim.state is StrategyCreateClaimState.IN_PROGRESS:
            raise StrategyApplicationInProgressError("Strategy creation is already in progress")
        if claim.state is StrategyCreateClaimState.COMPLETED:
            return self._get_completed_strategy(
                db,
                strategy_id=claim.strategy_resource_id,
                scope=strategy_input.scope,
            )

        claim_token = claim.claim_token

        def renew_claim() -> None:
            try:
                renewed = self.idempotency_repository.renew_claim(
                    db,
                    idempotency_key=idempotency_key,
                    actor_user_id=created_by_user_id,
                    scope=strategy_input.scope,
                    claim_token=claim_token,
                )
                if not renewed:
                    db.rollback()
                    raise StrategyApplicationConflictError("Strategy creation claim was lost")
                db.commit()
            except StrategyApplicationConflictError:
                raise
            except (StrategyIdempotencyError, SQLAlchemyError) as error:
                db.rollback()
                raise StrategyApplicationPersistenceError("Unable to renew Strategy creation claim") from error

        try:
            result = self.capability.generate(
                strategy_input,
                before_provider_attempt=renew_claim,
            )
            validate_strategy_result(result, strategy_input)
        except Exception:
            db.rollback()
            try:
                self.idempotency_repository.abandon_claim(
                    db,
                    idempotency_key=idempotency_key,
                    actor_user_id=created_by_user_id,
                    scope=strategy_input.scope,
                    claim_token=claim_token,
                )
                db.commit()
            except Exception:
                db.rollback()
            raise

        try:
            persisted = self.idempotency_repository.complete_with_strategy(
                db,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                actor_user_id=created_by_user_id,
                scope=strategy_input.scope,
                claim_token=claim_token,
                result=result,
                title=normalized_title,
                repository=self.repository,
            )
            db.commit()
            return persisted
        except StrategyIdempotencyCompletionError as error:
            db.rollback()
            raise StrategyApplicationConflictError("Strategy creation claim could not be completed") from error
        except (StrategyIdempotencyError, StrategyPersistenceError, SQLAlchemyError) as error:
            db.rollback()
            raise StrategyApplicationPersistenceError("Unable to persist Strategy") from error

    def generate_and_persist_direct_strategy(
        self,
        db,
        *,
        strategy_input: StrategyInput,
        title: str,
        created_by_user_id: int,
    ) -> PersistedStrategy:
        normalized_title = self._title(title)
        self._creator(created_by_user_id)
        try:
            validate_strategy_input(strategy_input)
        except StrategyValidationError as error:
            raise StrategyApplicationValidationError("Invalid canonical Strategy input") from error
        if strategy_input.source_decision_id is not None:
            raise StrategyApplicationValidationError("Direct Strategy input cannot reference a source Decision")
        self._scope_shape(strategy_input.scope)

        result = self.capability.generate(strategy_input)
        try:
            validate_strategy_result(result, strategy_input)
        except StrategyValidationError as error:
            raise StrategyApplicationValidationError("Invalid canonical Strategy result") from error
        return self._persist(
            db,
            result=result,
            title=normalized_title,
            created_by_user_id=created_by_user_id,
            origin_type="direct",
        )

    def persist_existing_strategy(
        self,
        db,
        *,
        result: StrategyResult,
        title: str,
        created_by_user_id: int,
        origin_type: str,
    ) -> PersistedStrategy:
        normalized_title = self._title(title)
        self._creator(created_by_user_id)
        try:
            validate_strategy_result(result)
        except StrategyValidationError as error:
            raise StrategyApplicationValidationError("Invalid canonical Strategy result") from error
        if result.strategy_id is not None or result.version is not None:
            raise StrategyApplicationValidationError("A new Strategy cannot select durable identity or version")
        if origin_type == "direct" and result.source_decision_id is not None:
            raise StrategyApplicationValidationError("Direct Strategies cannot reference a source Decision")
        if origin_type not in {"direct", "decision_derived"}:
            raise StrategyApplicationValidationError("Unsupported Strategy origin type")
        self._scope_shape(result.scope)
        return self._persist(
            db,
            result=result,
            title=normalized_title,
            created_by_user_id=created_by_user_id,
            origin_type=origin_type,
        )

    def get_current_personal_strategy(
        self, db, *, public_id: str, scope: StrategyScope
    ) -> PersistedStrategy:
        self._personal_scope(scope)
        return self._repository_call(
            self.repository.get_personal_strategy_by_public_id,
            db,
            public_id=public_id,
            owner_user_id=scope.user_id,
        )

    def get_current_workspace_strategy(
        self, db, *, public_id: str, scope: StrategyScope
    ) -> PersistedStrategy:
        self._workspace_scope(scope)
        return self._repository_call(
            self.repository.get_workspace_strategy_by_public_id,
            db,
            public_id=public_id,
            organization_id=scope.organization_id,
            workspace_id=scope.workspace_id,
        )

    def list_personal_strategies(
        self, db, *, scope: StrategyScope, limit: int = 50
    ) -> list[PersistedStrategy]:
        self._personal_scope(scope)
        return self._repository_call(
            self.repository.list_personal_strategies,
            db,
            owner_user_id=scope.user_id,
            limit=limit,
        )

    def list_workspace_strategies(
        self, db, *, scope: StrategyScope, limit: int = 50
    ) -> list[PersistedStrategy]:
        self._workspace_scope(scope)
        return self._repository_call(
            self.repository.list_workspace_strategies,
            db,
            organization_id=scope.organization_id,
            workspace_id=scope.workspace_id,
            limit=limit,
        )

    def archive_strategy(
        self,
        db,
        *,
        public_id: str,
        scope: StrategyScope,
        expected_lock_version: int,
    ) -> PersistedStrategy:
        if scope.organization_id is None and scope.workspace_id is None:
            operation = self.repository.archive_personal_strategy
            values = {"owner_user_id": scope.user_id}
        else:
            self._workspace_scope(scope)
            operation = self.repository.archive_workspace_strategy
            values = {
                "organization_id": scope.organization_id,
                "workspace_id": scope.workspace_id,
            }
        return self._repository_call(
            operation,
            db,
            public_id=public_id,
            expected_lock_version=expected_lock_version,
            **values,
        )

    def _persist(self, db, **values) -> PersistedStrategy:
        return self._repository_call(self.repository.create_strategy, db, **values)

    def _get_completed_strategy(
        self, db, *, strategy_id: int | None, scope: StrategyScope
    ) -> PersistedStrategy:
        if not isinstance(strategy_id, int):
            raise StrategyApplicationPersistenceError("Completed Strategy linkage is invalid")
        if scope.organization_id is None:
            operation = self.repository.get_personal_strategy_by_internal_id
            values = {"owner_user_id": scope.user_id}
        else:
            self._workspace_scope(scope)
            operation = self.repository.get_workspace_strategy_by_internal_id
            values = {
                "organization_id": scope.organization_id,
                "workspace_id": scope.workspace_id,
            }
        return self._repository_call(
            operation,
            db,
            strategy_id=strategy_id,
            **values,
        )

    @staticmethod
    def _title(value: object) -> str:
        try:
            return normalize_strategy_title(value)
        except StrategyPersistenceError as error:
            raise StrategyApplicationValidationError("Invalid Strategy title") from error

    @staticmethod
    def _personal_scope(scope: StrategyScope) -> None:
        if not isinstance(scope, StrategyScope) or scope.organization_id is not None or scope.workspace_id is not None:
            raise StrategyApplicationValidationError("A personal Strategy requires personal scope")

    @staticmethod
    def _workspace_scope(scope: StrategyScope) -> None:
        if (
            not isinstance(scope, StrategyScope)
            or scope.organization_id is None
            or scope.workspace_id is None
        ):
            raise StrategyApplicationValidationError("A workspace Strategy requires organization and workspace scope")

    @staticmethod
    def _scope_shape(scope: StrategyScope) -> None:
        if not isinstance(scope, StrategyScope):
            raise StrategyApplicationValidationError("Strategy scope must be canonical")
        if (scope.organization_id is None) != (scope.workspace_id is None):
            raise StrategyApplicationValidationError("Strategy scope must be personal or a complete workspace scope")

    @staticmethod
    def _creator(created_by_user_id: int) -> None:
        if (
            not isinstance(created_by_user_id, int)
            or isinstance(created_by_user_id, bool)
            or created_by_user_id <= 0
        ):
            raise StrategyApplicationValidationError("Strategy creator must be a positive integer")

    @staticmethod
    def _repository_call(operation, db, **values):
        try:
            return operation(db, **values)
        except StrategyPersistenceNotFoundError as error:
            raise StrategyApplicationNotFoundError("Strategy not found") from error
        except StrategyPersistenceConflictError as error:
            raise StrategyApplicationConflictError("Strategy update conflict") from error
        except (StrategyPersistenceError, SQLAlchemyError) as error:
            raise StrategyApplicationPersistenceError("Unable to persist or retrieve Strategy") from error


strategy_application_service = StrategyApplicationService()
