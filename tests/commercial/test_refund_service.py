from app.commercial.refund_service import RefundService
def test_refund_service_public_lifecycle_contract():
 assert all(hasattr(RefundService,n) for n in ('create_refund','mark_processing','mark_succeeded','mark_failed','cancel_refund'))
