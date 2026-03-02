from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

from app.core.config import get_settings

http_bearer_scheme = HTTPBearer(
    scheme_name="BearerToken",
    description="Bearer JWT token",
    auto_error=False,
)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scheme_name="OAuth2Password",
    description="OAuth2 password flow with JWT tokens",
    auto_error=False,
)


@dataclass
class AuthContext:
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role_name: str
    role_id: uuid.UUID


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        role_name: str,
        role_id: uuid.UUID,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role_name,
        "role_id": str(role_id),
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid identity format in token"
        )


def decode_token(token: str) -> AuthContext:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing"
        )

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token"
        )

    return AuthContext(
        user_id=_parse_uuid(payload.get("sub", "")),
        tenant_id=_parse_uuid(payload.get("tenant_id", "")),
        role_name=str(payload.get("role", "")),
        role_id=_parse_uuid(payload.get("role_id", "")),
    )


async def get_current_principal(
        http_bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_scheme),
        oauth2_token: Optional[str] = Depends(oauth2_scheme),
) -> AuthContext:
    token: Optional[str] = None
    if http_bearer_credentials:
        token = http_bearer_credentials.credentials
    elif oauth2_token:
        token = oauth2_token

    return decode_token(token or "")


def require_role(*allowed_roles: str):
    async def _require_role(
            auth: AuthContext = Depends(get_current_principal),
    ) -> AuthContext:
        if auth.role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return auth

    return _require_role


require_admin = require_role("admin")
require_manager = require_role("manager")