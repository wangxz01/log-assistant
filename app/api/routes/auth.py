from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, MessageResponse, RegisterRequest, TokenResponse
from app.services.auth_service import auth_service


router = APIRouter()
AUTH_COOKIE_NAME = "access_token"


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> MessageResponse:
    return auth_service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response) -> TokenResponse:
    token_response = auth_service.login(payload)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token_response.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return token_response


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=current_user.id, email=current_user.email)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", samesite="lax")
    return MessageResponse(message="Logged out.")
