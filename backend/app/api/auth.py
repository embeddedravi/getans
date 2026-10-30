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
from app.config import settings

from sqlalchemy.exc import IntegrityError
from app.models.advertiser import Advertiser
from app.models.publisher import Publisher
from app.schemas.generic import MessageResponse
from app.schemas.user import SignupRequest, SignupRole, ForgotPasswordReset, ProfileUpdate, PasswordChange, AccountDeletion
from app.services.otp import verify_otp
from app.services.captcha import issue_captcha, verify_captcha

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/captcha-challenge")
async def captcha_challenge() -> dict[str, str]:
    return issue_captcha()


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
    await verify_captcha(payload.captcha_challenge, payload.captcha_answer)
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


@router.patch("/me", response_model=UserOut, summary="Update own profile")
async def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not payload.email and not current_user.mobile:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add a mobile number before removing your email")
    if payload.email and (await db.execute(select(User).where(User.email == payload.email, User.id != current_user.id))).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    current_user.first_name = payload.first_name
    current_user.last_name = payload.last_name
    current_user.email = str(payload.email) if payload.email else None
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    await db.refresh(current_user)
    return current_user


@router.post("/me/password", response_model=MessageResponse, summary="Change own password")
async def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return MessageResponse(message="Password changed successfully")


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Delete own account")
async def delete_account(
    payload: AccountDeletion,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is incorrect")
    await db.delete(current_user)
    await db.commit()

@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Self-service signup for advertisers and publishers",
)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> User:
    await verify_captcha(payload.captcha_challenge, payload.captcha_answer)
    if not settings.allow_self_signup:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")

    conditions = [User.mobile == payload.mobile]
    if payload.email:
        conditions.append(User.email == payload.email)
    if (await db.execute(select(User).where(or_(*conditions)))).scalars().first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with these details already exists")

    if payload.role == SignupRole.PUBLISHER:
        tenant = Publisher(
            name=payload.organization_name,
            site_url=str(payload.site_url),
            payout_email=payload.payout_email,
        )
        role = UserRoleModel.PUBLISHER
    else:
        tenant = Advertiser(
            name=payload.organization_name,
            billing_email=payload.billing_email or payload.email,
        )
        role = UserRoleModel.ADVERTISER

    db.add(tenant)
    await db.flush()  # assigns tenant.id

    user = User(
        mobile=payload.mobile,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=role,
        publisher_id=tenant.id if role == UserRoleModel.PUBLISHER else None,
        advertiser_id=tenant.id if role == UserRoleModel.ADVERTISER else None,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:  # lost a race on the unique mobile/email; tenant rolls back too
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with these details already exists")
    await db.refresh(user)
    return user


@router.post(
    "/forgot-password/reset",
    response_model=MessageResponse,
    summary="Reset password using OTP",
)
async def reset_password(
    payload: ForgotPasswordReset,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await verify_captcha(payload.captcha_challenge, payload.captcha_answer)
    user = (await db.execute(select(User).where(User.mobile == payload.mobile))).scalar_one_or_none()
    
    if user is None or not await verify_otp(db, payload.mobile, payload.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")
        
    user.hashed_password = hash_password(payload.password)
    user.is_verified = True
    await db.commit()
    return MessageResponse(message="Password reset successfully")
