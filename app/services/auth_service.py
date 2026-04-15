from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse


class AuthService:
    def register(self, payload: RegisterRequest) -> MessageResponse:
        return MessageResponse(message=f"User {payload.email} registered (placeholder).")

    def login(self, payload: LoginRequest) -> TokenResponse:
        fake_token = f"demo-token-for-{payload.email}"
        return TokenResponse(access_token=fake_token)


auth_service = AuthService()

