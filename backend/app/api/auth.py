from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validates user credentials and produces a bearer access token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended or disabled",
        )

    # Track user login activity
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


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get authenticated user context",
)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Retrieves profile details for the currently authenticated identity."""
    return current_user