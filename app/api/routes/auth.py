from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_connection, initialize_database
from app.core.security import create_access_token, decode_refresh_token
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, MessageResponse, RegisterRequest, TokenResponse
from app.services.auth_service import auth_service


router = APIRouter()
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> MessageResponse:
    return auth_service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response) -> TokenResponse:
    token_response = auth_service.login(payload)
    _set_auth_cookies(response, token_response)
    return token_response


@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, refresh_token: str | None = Cookie(default=None)) -> TokenResponse:
    payload = decode_refresh_token(refresh_token or "")

    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    initialize_database()

    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE id = %s",
            (payload["sub"],),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists.")

    token_response = TokenResponse(
        access_token=create_access_token(subject=str(row["id"]), extra_claims={"email": row["email"]}),
        refresh_token=refresh_token or "",
    )
    _set_auth_cookies(response, token_response)
    return token_response


def _set_auth_cookies(response: Response, token_response: TokenResponse) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token_response.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token_response.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=current_user.id, email=current_user.email)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/", samesite="lax")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/", samesite="lax")
    return MessageResponse(message="Logged out.")
