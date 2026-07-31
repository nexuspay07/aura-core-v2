from app.commercial.repositories import SqlAlchemyCreditNoteApplicationRepository
def test_application_repository_contract_is_available():
 assert all(hasattr(SqlAlchemyCreditNoteApplicationRepository,n) for n in ('save','get_by_id','get_by_organization_and_idempotency_key','list_by_credit_note','list_by_invoice'))
