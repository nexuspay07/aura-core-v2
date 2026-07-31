from app.commercial.repositories import SqlAlchemyRefundRepository
def test_refund_repository_contract():
 assert all(hasattr(SqlAlchemyRefundRepository,n) for n in ('save','get_by_id','get_by_organization_and_number','get_by_organization_and_idempotency_key','list_by_invoice','list_by_payment_attempt','list_by_credit_note','list_by_organization'))
