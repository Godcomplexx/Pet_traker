from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Pet, User
from app.schemas import (
    LoginIn,
    RefreshIn,
    RegisterIn,
    RegisterOut,
    ResendCodeIn,
    TokenPair,
    UserOut,
    UserUpdate,
    VerifyEmailIn,
)
from app.services.verification import issue_code, verify_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user_id: str) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post(
    "/register",
    response_model=RegisterOut,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(User).where(User.email == data.email))
    if exists:
        if settings.require_email_verification and not exists.email_verified:
            await issue_code(db, exists.id, exists.email)
            await db.commit()
            return RegisterOut(email=exists.email)
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        email_verified=not settings.require_email_verification,
    )
    db.add(user)
    await db.flush()
    # FR-USER-2 / FR-PET-1: every user has exactly one pet, created on sign-up.
    db.add(Pet(user_id=user.id, name="Питомец"))

    if not settings.require_email_verification:
        await db.commit()
        # Подтверждение отключено — сразу выдаём токены.
        return RegisterOut(
            status="ok",
            email=data.email,
            message="Регистрация завершена",
        )

    await issue_code(db, user.id, user.email)
    await db.commit()
    return RegisterOut(email=data.email)


@router.post("/verify", response_model=TokenPair)
async def verify_email(data: VerifyEmailIn, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    if user.email_verified:
        # Уже подтверждён — просто выдаём токены.
        return _tokens(user.id)

    ok, err = await verify_code(db, user.id, data.code)
    if not ok:
        await db.commit()  # сохраняем счётчик попыток
        raise HTTPException(status.HTTP_400_BAD_REQUEST, err)

    user.email_verified = True
    await db.commit()
    return _tokens(user.id)


@router.post("/resend-code", status_code=status.HTTP_200_OK)
async def resend_code(data: ResendCodeIn, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == data.email))
    # Не раскрываем, существует ли email.
    if user is None or user.email_verified:
        return {"message": "Если аккаунт существует и не подтверждён, код отправлен"}
    await issue_code(db, user.id, user.email)
    await db.commit()
    return {"message": "Код отправлен повторно"}


@router.post("/login", response_model=TokenPair)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if settings.require_email_verification and not user.email_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Email не подтверждён. Проверьте почту и введите код.",
        )
    return _tokens(user.id)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshIn, db: AsyncSession = Depends(get_db)):
    try:
        user_id = decode_token(data.refresh_token, REFRESH)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if await db.get(User, user_id) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return _tokens(user_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: User = Depends(get_current_user)):
    # Stateless JWT: client discards tokens. (Revocation list is future work.)
    return None


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    await db.commit()
    await db.refresh(user)
    return user
