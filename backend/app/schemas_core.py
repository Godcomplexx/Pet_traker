"""Pydantic request/response schemas."""
from __future__ import annotations

import re
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app import enums
from app.services.characters import CHARACTERS_BY_ID


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _validate_password(value: str) -> str:
    """Password rules: 8–72 символа, минимум одна буква и одна цифра."""
    if len(value) < 8:
        raise ValueError("Пароль должен содержать минимум 8 символов")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Пароль слишком длинный (максимум 72 байта)")
    if not re.search(r"[A-Za-zА-Яа-я]", value):
        raise ValueError("Пароль должен содержать хотя бы одну букву")
    if not re.search(r"\d", value):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")
    return value


# ── Auth / users ──
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    display_name: str = Field(max_length=120)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("display_name")
    @classmethod
    def trim_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Имя должно содержать минимум 2 символа")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeIn(BaseModel):
    email: EmailStr


class RefreshIn(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterOut(BaseModel):
    """Ответ на регистрацию: аккаунт создан, требуется подтверждение email."""
    status: str = "verification_required"
    email: EmailStr
    message: str = "Код подтверждения отправлен на вашу почту"


class UserOut(ORMModel):
    id: str
    email: EmailStr
    display_name: str
    avatar_url: str | None = None
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    avatar_url: str | None = None


# ── Pet ──
_HEX_RE = r"^#[0-9A-Fa-f]{6}$"


class PetOut(ORMModel):
    id: str
    name: str
    species: str
    body_color: str
    accent_color: str
    customized: bool
    level: int
    xp: int
    mood: int
    hunger: int
    energy: int
    coins: int = 0
    daily_claimed_on: date | None = None
    sudoku_completed_on: date | None = None
    inventory: list[str] = Field(default_factory=list)
    food_inventory: dict[str, int] = Field(default_factory=dict)
    equipped: dict = Field(default_factory=dict)
    # Производное состояние (happy/ok/sad/hungry/sleepy) и подпись для UI.
    state: str = "ok"
    state_label: str = "в порядке"


class PetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PetPlayIn(BaseModel):
    action: str = Field(pattern="^(feed|pet|ball|sleep)$")
    item_id: str | None = None


class PetSudokuSolveIn(BaseModel):
    grid: list[list[int]] = Field(min_length=6, max_length=6)
    seconds: int = Field(default=0, ge=0, le=86400)
    hints_used: int = Field(default=0, ge=0)

    @field_validator("grid")
    @classmethod
    def check_grid(cls, v: list[list[int]]) -> list[list[int]]:
        if any(len(row) != 6 for row in v):
            raise ValueError("Судоку должно быть 6x6")
        if any(cell < 1 or cell > 6 for row in v for cell in row):
            raise ValueError("В судоку можно ставить только цифры 1-6")
        return v


class SudokuCheckIn(BaseModel):
    """Промежуточная проверка (подсветка ошибок). Клетки могут быть пустыми (0)."""
    grid: list[list[int]] = Field(min_length=6, max_length=6)


class SudokuHintIn(BaseModel):
    grid: list[list[int]] = Field(min_length=6, max_length=6)


class CoinRewardOut(BaseModel):
    pet: PetOut
    coins_awarded: int
    message: str
    best_seconds: int | None = None
    seconds: int | None = None


class SudokuScoreOut(BaseModel):
    user_id: str
    name: str
    seconds: int
    hints_used: int
    is_me: bool = False


class ZipScoreOut(BaseModel):
    user_id: str
    name: str
    seconds: int
    is_me: bool = False


class PetCustomize(BaseModel):
    """Создание/настройка внешности питомца (экран после онбординга)."""
    name: str = Field(min_length=1, max_length=80)
    species: str = "capybara"
    body_color: str = Field(default="#d99a52", pattern=_HEX_RE)
    accent_color: str = Field(default="#7a3a22", pattern=_HEX_RE)

    @field_validator("species")
    @classmethod
    def check_species(cls, v: str) -> str:
        if v not in CHARACTERS_BY_ID:
            raise ValueError("Неизвестный персонаж")
        return v


class ShopBuyIn(BaseModel):
    item_id: str


class EquipIn(BaseModel):
    # item_id или null чтобы снять предмет данного типа
    item_id: str | None = None


class CaseOpenOut(BaseModel):
    """Результат открытия кейса."""
    item: dict
    is_new: bool
    coins: int


# ── Ежедневные игры (судоку) ──
class DailySudokuOut(BaseModel):
    """Головоломка дня + статус прохождения текущим пользователем."""
    date: str
    size: int
    block_rows: int
    block_cols: int
    puzzle: list[list[int]]   # 0 = пустая клетка
    reward: int               # сколько монет даётся за прохождение
    solved_today: bool        # уже пройдена сегодня этим пользователем
    best_seconds: int | None = None


class SudokuSolveIn(BaseModel):
    solution: list[list[int]]
    seconds: int = Field(default=0, ge=0, le=86400)
    hints_used: int = Field(default=0, ge=0)


class SudokuSolveOut(BaseModel):
    correct: bool
    coins_awarded: int        # 0, если неверно или уже была награда сегодня
    coins: int                # текущий баланс монет
    already_solved: bool      # награда за сегодня уже выдана ранее
    message: str
    best_seconds: int | None = None
    seconds: int | None = None


class DailyZipOut(BaseModel):
    date: str
    size: int
    markers: list[dict]
    solution_path: list[list[int]]
    reward: int
    solved_today: bool
    best_seconds: int | None = None


class ZipSolveIn(BaseModel):
    path: list[list[int]]
    seconds: int = Field(default=0, ge=0, le=86400)


class ZipSolveOut(BaseModel):
    correct: bool
    coins_awarded: int
    coins: int
    already_solved: bool
    message: str
    best_seconds: int | None = None
    seconds: int | None = None


# ── Workspace ──
class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None


class WorkspaceJoin(BaseModel):
    join_code: str = Field(min_length=4, max_length=12)

    @field_validator("join_code")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().upper()


class WorkspaceOut(ORMModel):
    id: str
    name: str
    description: str | None = None
    owner_id: str
    join_code: str
    created_at: datetime


class MemberInvite(BaseModel):
    email: EmailStr
    role: enums.WorkspaceRole = enums.WorkspaceRole.MEMBER


class MemberRoleUpdate(BaseModel):
    role: enums.WorkspaceRole


class MemberOut(ORMModel):
    id: str
    user_id: str
    role: enums.WorkspaceRole
    joined_at: datetime
    display_name: str | None = None
    email: str | None = None


# ── Project / Article members ──
class ProjectMemberAdd(BaseModel):
    user_id: str
    role: enums.ProjectRole = enums.ProjectRole.CONTRIBUTOR


class ProjectMemberOut(ORMModel):
    id: str
    user_id: str
    role: enums.ProjectRole
    display_name: str | None = None
    email: str | None = None


class ArticleMemberAdd(BaseModel):
    user_id: str
    role: enums.ArticleRole = enums.ArticleRole.CO_AUTHOR


class ArticleMemberOut(ORMModel):
    id: str
    user_id: str
    role: enums.ArticleRole
    display_name: str | None = None
    email: str | None = None


# ── Project ──
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    type: enums.ProjectType = enums.ProjectType.OTHER
    status: enums.ProjectStatus | None = None
    deadline: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    type: enums.ProjectType | None = None
    deadline: date | None = None


class ProjectStatusUpdate(BaseModel):
    status: enums.ProjectStatus


class BoardMove(BaseModel):
    """Перемещение карточки на доске: новая колонка (статус) + порядок.

    order — список id карточек в целевой колонке в нужном порядке (включая
    перемещаемую). Если задан — пересчитываем position по нему.
    """
    status: str
    order: list[str] = Field(default_factory=list)


class ProjectOut(ORMModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    type: enums.ProjectType
    status: enums.ProjectStatus
    owner_id: str
    deadline: date | None = None
    position: int = 0
    created_at: datetime
    # Богатые поля для карточек доски (заполняются в листинге).
    task_total: int | None = None
    task_done: int | None = None
    article_count: int | None = None
    member_ids: list[str] = Field(default_factory=list)
