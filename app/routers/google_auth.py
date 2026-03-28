import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserRole
from app.auth import create_access_token, COOKIE_NAME, COOKIE_MAX_AGE
from app.config import get_settings, get_google_settings

router = APIRouter(prefix="/auth", tags=["Auth"])


def set_auth_cookie(response: Response, token: str):
    settings = get_settings()
    is_prod = settings.APP_ENV == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="none" if is_prod else "lax",
        max_age=COOKIE_MAX_AGE,
    )


@router.get("/google")
def google_login():
    """Redirect user to Google's OAuth2 consent screen."""
    gs = get_google_settings()
    params = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={gs.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={gs.GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&access_type=offline"
    )
    return RedirectResponse(url=params)


@router.get("/google/callback")
async def google_callback(code: str, response: Response, db: Session = Depends(get_db)):
    """
    Google redirects here with ?code=...
    1. Exchange code for tokens
    2. Fetch user info from Google
    3. Find or create user in our DB
    4. Set auth cookie and redirect to frontend
    """
    gs = get_google_settings()
    settings = get_settings()

    # ── Step 1: exchange code for access token ────────────────────────────────
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": gs.GOOGLE_CLIENT_ID,
                "client_secret": gs.GOOGLE_CLIENT_SECRET,
                "redirect_uri": gs.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange Google auth code"
        )

    google_tokens = token_resp.json()
    google_access_token = google_tokens.get("access_token")

    # ── Step 2: fetch user info from Google ───────────────────────────────────
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch Google user info"
        )

    google_user = userinfo_resp.json()
    email: str = google_user.get("email")
    full_name: str = google_user.get("name", email)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email address"
        )

    # ── Step 3: find or create user ───────────────────────────────────────────
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # First time login with Google — create account automatically
        user = User(
            full_name=full_name,
            email=email,
            password_hash="",   # no password — Google auth only
            role=UserRole.USER,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # ── Step 4: set cookie and redirect to frontend ───────────────────────────
    token = create_access_token({"sub": user.user_id})
    redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback")
    set_auth_cookie(redirect, token)
    return redirect
