from fastapi import APIRouter, status

from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse
from app.services.auth_service import auth_service


router = APIRouter()


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> MessageResponse:
    return auth_service.register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    return auth_service.login(payload)

