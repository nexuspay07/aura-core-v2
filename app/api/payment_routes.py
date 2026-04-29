import os
import stripe
from fastapi import APIRouter, HTTPException

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

        return {"checkout_url": session.url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))