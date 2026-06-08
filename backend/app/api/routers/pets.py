from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.models import Pet, SudokuScore, User, WorkspaceMember, ZipScore
from app.schemas import (
    CoinRewardOut,
    PetCustomize,
    PetOut,
    PetPlayIn,
    PetUpdate,
    PetSudokuSolveIn,
    SudokuCheckIn,
    SudokuHintIn,
    SudokuScoreOut,
    ZipScoreOut,
)
from app.services.pet import apply_decay, pet_state, revive_pet, state_label
from app.services.shop import get_item
from app.services import sudoku as sudoku_svc

router = APIRouter(tags=["pets"])

DAILY_LOGIN_COINS = 30
SUDOKU_REWARD_COINS = 40
SUDOKU_MAX_HINTS = 3


def _today_utc():
    return datetime.now(timezone.utc).date()


def _to_out(pet: Pet) -> PetOut:
    out = PetOut.model_validate(pet)
    st = pet_state(pet)
    out.state = st
    out.state_label = state_label(st)
    return out


async def _get_pet(db: AsyncSession, user_id: str) -> Pet:
    pet = await db.scalar(select(Pet).where(Pet.user_id == user_id))
    if pet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pet not found")
    return pet


def _play_feed(pet: Pet, data: PetPlayIn) -> int:
    if pet.hunger >= 95:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец уже сыт")
    if not data.item_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Выбери еду из рюкзака")
    item = get_item(data.item_id)
    if item is None or item["type"] != "food":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Это не еда")
    _consume_food(pet, data.item_id)
    data_map = item.get("data") or {}
    pet.hunger = min(100, pet.hunger + int(data_map.get("hunger", 0)))
    pet.mood = min(100, pet.mood + int(data_map.get("mood", 0)))
    pet.energy = min(100, pet.energy + int(data_map.get("energy", 0)))
    return 0


def _play_pet(pet: Pet, _: PetPlayIn) -> int:
    if pet.hunger <= 5:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец слишком голоден, сначала покорми")
    if pet.energy <= 5:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец спит без сил")
    pet.mood = min(100, pet.mood + 12)
    return 25


def _play_ball(pet: Pet, _: PetPlayIn) -> int:
    if pet.hunger <= 10:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец голоден и не хочет играть")
    if pet.energy < 12:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недостаточно энергии для мячика")
    pet.mood = min(100, pet.mood + 10)
    pet.energy = max(0, pet.energy - 12)
    return 25


def _play_sleep(pet: Pet, _: PetPlayIn) -> int:
    if pet.energy >= 80:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец бодрый - спать пока не хочет")
    pet.energy = 100
    pet.mood = min(100, pet.mood + 5)
    return 0


PLAY_ACTIONS = {
    "feed": _play_feed,
    "pet": _play_pet,
    "ball": _play_ball,
    "sleep": _play_sleep,
}


def _consume_food(pet: Pet, item_id: str) -> None:
    food = dict(pet.food_inventory or {})
    current = int(food.get(item_id, 0))
    if current <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этой еды нет в рюкзаке")
    if current == 1:
        food.pop(item_id, None)
    else:
        food[item_id] = current - 1
    pet.food_inventory = food



@router.get("/pets/me", response_model=PetOut)
async def my_pet(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Тамагочи: при каждом чтении «доживаем» показатели до текущего момента.
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


@router.patch("/pets/me", response_model=PetOut)
async def rename_pet(
    data: PetUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    # FR-PET-4: only `name` is mutable; XP/level/mood/hunger/energy are backend-only.
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    pet.name = data.name
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


@router.put("/pets/me", response_model=PetOut)
async def customize_pet(
    data: PetCustomize, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Создать/настроить внешность питомца. Игровые показатели не трогаем (FR-PET-4)."""
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    pet.name = data.name
    pet.species = data.species
    pet.body_color = data.body_color
    pet.accent_color = data.accent_color
    pet.customized = True
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


@router.post("/pets/me/play", response_model=PetOut)
async def play_with_pet(
    data: PetPlayIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    if pet.is_dead:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец умер. Сначала оживи его.")
    handler = PLAY_ACTIONS.get(data.action)
    if handler is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown action")
    reward = handler(pet, data)
    pet.coins = (pet.coins or 0) + reward
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


@router.post("/pets/me/revive", response_model=PetOut)
async def revive_my_pet(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    if not pet.is_dead:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Питомец жив")
    revive_pet(pet)
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


@router.post("/pets/me/daily", response_model=CoinRewardOut)
async def claim_daily_coins(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    today = _today_utc()
    if pet.daily_claimed_on == today:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ежедневный бонус уже получен")
    pet.daily_claimed_on = today
    pet.coins = (pet.coins or 0) + DAILY_LOGIN_COINS
    await db.commit()
    await db.refresh(pet)
    return CoinRewardOut(
        pet=_to_out(pet),
        coins_awarded=DAILY_LOGIN_COINS,
        message="Ежедневный бонус получен",
    )


async def _my_best(db: AsyncSession, user_id: str, day: str) -> SudokuScore | None:
    return await db.scalar(
        select(SudokuScore).where(
            SudokuScore.user_id == user_id, SudokuScore.puzzle_date == day
        )
    )


@router.get("/pets/me/sudoku")
async def sudoku_status(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pet = await _get_pet(db, user.id)
    today = _today_utc()
    day = today.isoformat()
    best = await _my_best(db, user.id, day)
    puzzle = sudoku_svc.daily_puzzle(today)
    return {
        "puzzle": puzzle["puzzle"],
        "reward": SUDOKU_REWARD_COINS,
        "max_hints": SUDOKU_MAX_HINTS,
        "completed_today": pet.sudoku_completed_on == today,  # награда за сегодня уже взята
        "best_seconds": best.seconds if best else None,
        "puzzle_date": day,
    }


@router.post("/pets/me/sudoku/check")
async def sudoku_check(
    data: SudokuCheckIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Подсветка ошибок: вернуть конфликтующие клетки (без сохранения)."""
    today = _today_utc()
    return {"errors": sudoku_svc.find_errors(today, data.grid)}


@router.post("/pets/me/sudoku/hint")
async def sudoku_hint(
    data: SudokuHintIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Подсказка: правильная цифра для первой неверной/пустой клетки."""
    today = _today_utc()
    hint = sudoku_svc.hint_for(today, data.grid)
    if hint is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Подсказывать нечего — всё верно")
    return hint


@router.post("/pets/me/sudoku", response_model=CoinRewardOut)
async def solve_sudoku(
    data: PetSudokuSolveIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    today = _today_utc()
    day = today.isoformat()
    if not sudoku_svc.check_solution(today, data.grid):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "В судоку есть ошибка")

    # Монеты — только за первое прохождение в сутки. Перерешать можно (для рейтинга).
    awarded = 0
    first_today = pet.sudoku_completed_on != today
    if first_today:
        pet.sudoku_completed_on = today
        awarded = SUDOKU_REWARD_COINS
        pet.coins = (pet.coins or 0) + awarded
        if not pet.is_dead:
            pet.mood = min(100, pet.mood + 4)

    # Рейтинг: сохраняем лучшее (минимальное) время за день.
    best = await _my_best(db, user.id, day)
    if best is None:
        best = SudokuScore(
            user_id=user.id, puzzle_date=day, seconds=data.seconds, hints_used=data.hints_used
        )
        db.add(best)
    elif data.seconds and data.seconds < best.seconds:
        best.seconds = data.seconds
        best.hints_used = data.hints_used

    await db.commit()
    await db.refresh(pet)
    await db.refresh(best)
    return CoinRewardOut(
        pet=_to_out(pet),
        coins_awarded=awarded,
        message="Судоку пройдено" if first_today else "Время записано в рейтинг",
        best_seconds=best.seconds,
        seconds=data.seconds,
    )


@router.get("/workspaces/{workspace_id}/sudoku/leaderboard", response_model=list[SudokuScoreOut])
async def sudoku_leaderboard(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Рейтинг участников лаборатории по сегодняшней судоку (по времени)."""
    await require_membership(workspace_id, db, user)
    day = _today_utc().isoformat()
    member_ids = (
        await db.scalars(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).all()
    if not member_ids:
        return []
    rows = (
        await db.execute(
            select(SudokuScore, User.display_name, User.email)
            .join(User, User.id == SudokuScore.user_id)
            .where(
                SudokuScore.puzzle_date == day,
                SudokuScore.user_id.in_(member_ids),
            )
            .order_by(SudokuScore.seconds.asc())
        )
    ).all()
    return [
        SudokuScoreOut(
            user_id=sc.user_id,
            name=(name or email or sc.user_id[:6]),
            seconds=sc.seconds,
            hints_used=sc.hints_used,
            is_me=sc.user_id == user.id,
        )
        for (sc, name, email) in rows
    ]


@router.get("/workspaces/{workspace_id}/zip/leaderboard", response_model=list[ZipScoreOut])
async def zip_leaderboard(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Workspace leaderboard for today's Zip puzzle, sorted by best time."""
    await require_membership(workspace_id, db, user)
    day = _today_utc().isoformat()
    member_ids = (
        await db.scalars(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).all()
    if not member_ids:
        return []
    rows = (
        await db.execute(
            select(ZipScore, User.display_name, User.email)
            .join(User, User.id == ZipScore.user_id)
            .where(
                ZipScore.puzzle_date == day,
                ZipScore.user_id.in_(member_ids),
            )
            .order_by(ZipScore.seconds.asc())
        )
    ).all()
    return [
        ZipScoreOut(
            user_id=sc.user_id,
            name=(name or email or sc.user_id[:6]),
            seconds=sc.seconds,
            is_me=sc.user_id == user.id,
        )
        for (sc, name, email) in rows
    ]
