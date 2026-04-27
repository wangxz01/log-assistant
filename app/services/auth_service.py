from typing import Any

import psycopg
from fastapi import HTTPException, status

from app.core.database import get_connection, initialize_database
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest, TokenResponse


class AuthService:
    def register(self, payload: RegisterRequest) -> MessageResponse:
        initialize_database()
        email = payload.email.lower()

        if self._find_user_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            )

        password_hash = hash_password(payload.password)

        try:
            with get_connection() as connection:
                connection.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                    (email, password_hash),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered.",
            ) from exc

        return MessageResponse(message=f"User {email} registered.")

    def login(self, payload: LoginRequest) -> TokenResponse:
        initialize_database()
        email = payload.email.lower()
        user = self._find_user_by_email(email)

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )
        return TokenResponse(access_token=access_token)

    def _find_user_by_email(self, email: str) -> User | None:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s",
                (email,),
            ).fetchone()

        if not row:
            return None

        return self._row_to_user(row)

    @staticmethod
    def _row_to_user(row: dict[str, Any]) -> User:
        return User(id=row["id"], email=row["email"], password_hash=row["password_hash"])


auth_service = AuthService()
