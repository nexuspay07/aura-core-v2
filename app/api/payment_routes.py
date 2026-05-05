import os
import stripe
from fastapi import APIRouter, HTTPException
from app.core.payment_tracker import payment_tracker


router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://aura-ai-frontend-on0e.onrender.com"
)


@router.post("/create-checkout-session")
def create_checkout_session():
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="Stripe secret key not configured")

    payment_tracker.log_event("unlock_clicked")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "cad",
                        "product_data": {
                            "name": "AURA Pro Decision Report",
                            "description": "Full AI business decision analysis report",
                        },
                        "unit_amount": 500,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{FRONTEND_URL}?payment=success",
            cancel_url=f"{FRONTEND_URL}?payment=cancelled",
        )

        payment_tracker.log_event("checkout_created", {
            "checkout_url": session.url
        })

        return {"checkout_url": session.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track-payment-success")
def track_payment_success(data: dict):
    event = payment_tracker.log_event("payment_success", data)

    return {
        "success": True,
        "event": event
    }


@router.get("/payment-stats")
def payment_stats():
    return payment_tracker.get_stats()