import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    """Lowercase, hyphenated, plus a short random suffix so two tenants named
    the same thing never collide on the unique slug index. Good enough for
    this capstone's scope; a real product would offer the owner a rename UI
    for slug conflicts instead of a silent suffix."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    suffix = uuid.uuid4().hex[:6]
    return f"{base}-{suffix}" if base else suffix


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    tenant = Tenant(name=data.tenant_name, slug=_slugify(data.tenant_name))
    db.add(tenant)
    await db.flush()  # populate tenant.id for the user FK below, without ending the transaction

    user = User(
        tenant_id=tenant.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole.OWNER,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(subject=str(user.id), tenant_id=str(tenant.id))
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Deliberately identical error for "no such user" and "wrong password" —
    # distinguishing them lets an attacker enumerate registered emails.
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=str(user.id), tenant_id=str(user.tenant_id))
    return TokenResponse(access_token=token)
