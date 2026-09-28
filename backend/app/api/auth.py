from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.models.user import UserRole as UserRoleModel
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserOut, UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with mobile number and issue JWT",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validates mobile + password and produces a bearer access token."""
    result = await db.execute(select(User).where(User.mobile == payload.mobile))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect mobile number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended or disabled",
        )
        
    if settings.require_verified_mobile and not user.is_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Mobile number not verified")

    user.last_login_at = datetime.now(timezone.utc)
    if request.client:
        user.last_login_ip = request.client.host
    await db.commit()

    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "publisher_id": user.publisher_id,
            "advertiser_id": user.advertiser_id,
        },
    )
    return TokenResponse(access_token=token, token_type="bearer")


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a dashboard user (admin only)",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> User:
    """Creates a user identified by mobile number. Email is optional."""
    # Mirror the DB tenant-integrity constraint with a friendly error
    if payload.role == UserRole.PUBLISHER and (
        payload.publisher_id is None or payload.advertiser_id is not None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Publisher users need publisher_id only")
    if payload.role == UserRole.ADVERTISER and (
        payload.advertiser_id is None or payload.publisher_id is not None
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Advertiser users need advertiser_id only")

    conditions = [User.mobile == payload.mobile]
    if payload.email:
        conditions.append(User.email == payload.email)
    existing = (await db.execute(select(User).where(or_(*conditions)))).scalars().first()
    if existing is not None:
        field = "mobile number" if existing.mobile == payload.mobile else "email"
        raise HTTPException(status.HTTP_409_CONFLICT, f"An account with this {field} already exists")

    user = User(
        mobile=payload.mobile,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=UserRoleModel(payload.role.value),
        publisher_id=payload.publisher_id,
        advertiser_id=payload.advertiser_id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get authenticated user context",
)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Retrieves profile details for the currently authenticated identity."""
    return current_user