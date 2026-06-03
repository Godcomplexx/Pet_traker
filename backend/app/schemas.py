"""Pydantic request/response schemas."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app import enums


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
SPECIES = {"capybara", "cat", "dog", "frog", "axolotl"}


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
    inventory: list[str] = Field(default_factory=list)
    food_inventory: dict[str, int] = Field(default_factory=dict)
    equipped: dict = Field(default_factory=dict)
    # Производное состояние (happy/ok/sad/hungry/sleepy) и подпись для UI.
    state: str = "ok"
    state_label: str = "в порядке"


class PetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PetPlayIn(BaseModel):
    action: str = Field(pattern="^(feed|pet|ball|test_coins)$")
    item_id: str | None = None


class PetCustomize(BaseModel):
    """Создание/настройка внешности питомца (экран после онбординга)."""
    name: str = Field(min_length=1, max_length=80)
    species: str = "capybara"
    body_color: str = Field(default="#d99a52", pattern=_HEX_RE)
    accent_color: str = Field(default="#7a3a22", pattern=_HEX_RE)

    @field_validator("species")
    @classmethod
    def check_species(cls, v: str) -> str:
        if v not in SPECIES:
            raise ValueError(f"Неизвестный вид питомца. Доступно: {', '.join(sorted(SPECIES))}")
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


class ProjectOut(ORMModel):
    id: str
    workspace_id: str
    name: str
    description: str | None = None
    type: enums.ProjectType
    status: enums.ProjectStatus
    owner_id: str
    deadline: date | None = None
    created_at: datetime


# ── Article ──
class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    project_id: str | None = None
    target_journal: str | None = None
    document_url: str | None = None
    deadline: date | None = None


class ArticleStatusUpdate(BaseModel):
    status: enums.ArticleStatus


class ArticleOut(ORMModel):
    id: str
    workspace_id: str
    project_id: str | None = None
    title: str
    description: str | None = None
    status: enums.ArticleStatus
    owner_id: str
    target_journal: str | None = None
    document_url: str | None = None
    deadline: date | None = None
    created_at: datetime


# ── Task ──
class TaskCreate(BaseModel):
    scope: enums.TaskScope
    workspace_id: str | None = None
    project_id: str | None = None
    article_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    type: enums.TaskType = enums.TaskType.OTHER
    priority: enums.TaskPriority = enums.TaskPriority.MEDIUM
    assignee_id: str | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    type: enums.TaskType | None = None
    priority: enums.TaskPriority | None = None
    status: enums.TaskStatus | None = None
    assignee_id: str | None = None
    due_date: date | None = None


class TaskOut(ORMModel):
    id: str
    workspace_id: str | None = None
    project_id: str | None = None
    article_id: str | None = None
    owner_id: str
    title: str
    description: str | None = None
    scope: enums.TaskScope
    visibility: enums.TaskVisibility
    status: enums.TaskStatus
    type: enums.TaskType
    priority: enums.TaskPriority
    assignee_id: str | None = None
    due_date: date | None = None
    completed_at: datetime | None = None
    created_at: datetime


# ── Comment ──
class CommentCreate(BaseModel):
    text: str = Field(min_length=1)
    # Explicit mention targets (resolved against workspace members). Plus any
    # `@email` tokens found in `text` are parsed automatically.
    mention_user_ids: list[str] = Field(default_factory=list)


class CommentUpdate(BaseModel):
    text: str = Field(min_length=1)


class CommentOut(ORMModel):
    id: str
    author_id: str
    text: str
    created_at: datetime


# ── Activity / notifications / pet feed ──
class ActivityOut(ORMModel):
    id: str
    actor_id: str
    event_type: str
    entity_type: str
    entity_id: str
    text: str
    created_at: datetime


class NotificationOut(ORMModel):
    id: str
    type: enums.NotificationType
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool


class WallPostCreate(BaseModel):
    text: str = Field(default="", max_length=2000)
    image_data: str | None = Field(default=None, max_length=700_000)

    @field_validator("image_data")
    @classmethod
    def check_wall_image(cls, v: str | None) -> str | None:
        if not v:
            return None
        allowed = (
            "data:image/png;base64,",
            "data:image/jpeg;base64,",
            "data:image/webp;base64,",
            "data:image/gif;base64,",
        )
        if v.startswith(allowed):
            return v
        parsed = urlparse(v)
        if parsed.scheme == "https" and re.search(r"\.(png|jpe?g|webp|gif)(\?.*)?$", parsed.path, re.I):
            return v
        raise ValueError("Можно прикрепить только png, jpg, webp или gif")


class WallReactionIn(BaseModel):
    emoji: str = Field(min_length=1, max_length=16)

    @field_validator("emoji")
    @classmethod
    def check_emoji(cls, v: str) -> str:
        allowed = {"👍", "👎", "❤️", "😂", "🎉", "👀", "🔥"}
        if v not in allowed:
            raise ValueError("Недоступная реакция")
        return v


class WallPostOut(BaseModel):
    id: str
    author_id: str
    author_name: str
    text: str
    image_data: str | None = None
    reactions: dict[str, int] = Field(default_factory=dict)
    my_reactions: list[str] = Field(default_factory=list)
    created_at: datetime
