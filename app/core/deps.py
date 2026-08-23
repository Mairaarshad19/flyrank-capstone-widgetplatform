"""
This is the single chokepoint that resolves "who is making this request, and
which tenant do they belong to." Every authenticated route depends on
get_current_user and uses `user.tenant_id` for every query — never a
tenant_id from a URL param, body field, or header. See DESIGN.md § 3.
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import JWTError, decode_access_token
from app.db.session import get_db
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=True)


@dataclass
class CurrentUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    raw_user_id = payload.get("sub")
    raw_tenant_id = payload.get("tenant_id")
    if not raw_user_id or not raw_tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    # Look the user up fresh rather than trusting the token's claims alone —
    # a deleted/deactivated user's old tokens stop working immediately.
    result = await db.execute(select(User).where(User.id == uuid.UUID(raw_user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return CurrentUser(id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role.value)
