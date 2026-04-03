"""
Payment flow using Stripe:

1. Donor calls POST /payments/dreams/{dream_id}/checkout
   → Creates a Stripe Checkout Session
   → Returns a checkout URL the frontend redirects to

2. Donor pays on Stripe's hosted page

3. Stripe calls POST /payments/webhook
   → We verify the signature
   → On checkout.session.completed:
      - mark dream as completed
      - send confirmation email to dream owner
"""
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.auth import get_current_user
from app.config import get_settings, get_stripe_settings
from app.database import get_db
from app.email import send_dream_completed_email
from app.models.models import Dream, User, UserRole

router = APIRouter(prefix="/payments", tags=["Payments"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CheckoutSessionOut(BaseModel):
    checkout_url: str
    session_id:   str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_stripe_client():
    ss = get_stripe_settings()
    stripe.api_key = ss.STRIPE_SECRET_KEY
    return stripe


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/dreams/{dream_id}/checkout",
    response_model=CheckoutSessionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout_session(
    dream_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a Stripe Checkout Session for paying for a dream.
    Any authenticated user can pay — except the dream owner (can't pay for yourself).
    Returns a checkout_url to redirect the user to.
    """
    settings = get_settings()
    ss = get_stripe_settings()
    stripe_client = get_stripe_client()

    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")

    if dream.is_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dream has already been fulfilled"
        )

    if dream.owner_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot pay for your own dream"
        )

    try:
        session = stripe_client.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(dream.target_budget * 100),  # Stripe uses cents
                    "product_data": {
                        "name": dream.title,
                        "description": dream.description[:255],
                        "images": [dream.image_url] if dream.image_url else [],
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/payment/cancel?dream_id={dream_id}",
            metadata={
                "dream_id":  dream_id,
                "donor_id":  current_user.user_id,
                "donor_email": current_user.email,
            },
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Stripe error: {str(e)}"
        )

    return {"checkout_url": session.url, "session_id": session.id}


@router.get("/dreams/{dream_id}/checkout/success")
def checkout_success(
    dream_id: str,
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    Optional: verify a completed session by ID.
    Frontend can call this after redirect from Stripe success_url.
    """
    stripe_client = get_stripe_client()

    try:
        session = stripe_client.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
    if not dream:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dream not found")

    return {
        "payment_status": session.payment_status,
        "dream_id": dream_id,
        "dream_completed": dream.is_completed,
    }


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Stripe webhook endpoint.
    Must be registered in your Stripe dashboard.
    Verifies signature then handles checkout.session.completed.
    """
    ss = get_stripe_settings()
    stripe_client = get_stripe_client()

    payload = await request.body()

    # ── Verify webhook signature ──────────────────────────────────────────────
    try:
        event = stripe_client.Webhook.construct_event(
            payload, stripe_signature, ss.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # ── Handle events ─────────────────────────────────────────────────────────
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # Only process paid sessions
        if session.get("payment_status") != "paid":
            return JSONResponse({"status": "ignored"})

        dream_id  = session["metadata"].get("dream_id")
        donor_id  = session["metadata"].get("donor_id")

        dream = db.query(Dream).filter(Dream.dream_id == dream_id).first()
        if not dream:
            return JSONResponse({"status": "dream_not_found"})

        if dream.is_completed:
            return JSONResponse({"status": "already_completed"})

        # ── Mark dream as completed ───────────────────────────────────────────
        dream.is_completed = True
        db.commit()
        db.refresh(dream)

        # ── Notify dream owner by email ───────────────────────────────────────
        owner = db.query(User).filter(User.user_id == dream.owner_id).first()
        donor = db.query(User).filter(User.user_id == donor_id).first()

        if owner:
            try:
                send_dream_completed_email(
                    to_email=owner.email,
                    owner_name=owner.full_name,
                    dream_title=dream.title,
                    donor_name=donor.full_name if donor else "An anonymous donor",
                )
            except Exception:
                pass  # don't fail the webhook if email fails

    return JSONResponse({"status": "ok"})
