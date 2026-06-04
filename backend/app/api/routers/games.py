"""Ежедневные мини-игры. Сейчас — судоку 6×6 с наградой +50 монет раз в день."""
from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import DailyGameCompletion, Pet, User
from app.schemas import (
    DailyMemoryOut,
    DailySudokuOut,
    MemorySolveIn,
    MemorySolveOut,
    SudokuSolveIn,
    SudokuSolveOut,
)
from app.services import sudoku

router = APIRouter(tags=["games"])

GAME_SUDOKU = "sudoku"
GAME_MEMORY = "memory"
SUDOKU_REWARD = 50
MEMORY_REWARD = 35
MEMORY_MAX_MOVES = 18
MEMORY_PAIRS = 6
MEMORY_SYMBOLS = ["heart", "coin", "star", "flower", "crown", "ribbon"]


def _today() -> "datetime.date":
    return datetime.now(timezone.utc).date()


async def _solved_today(db: AsyncSession, user_id: str, game: str, day) -> bool:
    row = await db.scalar(
        select(DailyGameCompletion).where(
            DailyGameCompletion.user_id == user_id,
            DailyGameCompletion.game == game,
            DailyGameCompletion.day == day,
        )
    )
    return row is not None


def _daily_memory_cards(day) -> list[str]:
    cards = MEMORY_SYMBOLS[:MEMORY_PAIRS] * 2
    random.Random(day.toordinal() ^ 0xC0FFEE).shuffle(cards)
    return cards


@router.get("/games/sudoku/daily", response_model=DailySudokuOut)
async def daily_sudoku(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Головоломка дня (одна для всех) + флаг, прошёл ли её пользователь сегодня."""
    day = _today()
    puzzle = sudoku.daily_puzzle(day)
    solved = await _solved_today(db, user.id, GAME_SUDOKU, day)
    return DailySudokuOut(
        date=puzzle["date"],
        size=puzzle["size"],
        block_rows=puzzle["block_rows"],
        block_cols=puzzle["block_cols"],
        puzzle=puzzle["puzzle"],
        reward=SUDOKU_REWARD,
        solved_today=solved,
    )


@router.post("/games/sudoku/solve", response_model=SudokuSolveOut)
async def solve_sudoku(
    data: SudokuSolveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Проверить решение. Первое верное за день → +50 монет (один раз в день)."""
    day = _today()

    if not sudoku.check_solution(day, data.solution):
        pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
        return SudokuSolveOut(
            correct=False,
            coins_awarded=0,
            coins=pet.coins if pet else 0,
            already_solved=await _solved_today(db, user.id, GAME_SUDOKU, day),
            message="Решение неверное — проверь строки, столбцы и блоки.",
        )

    pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
    if pet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pet not found")

    # Уже была награда сегодня?
    if await _solved_today(db, user.id, GAME_SUDOKU, day):
        return SudokuSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=True,
            message="Верно! Но награду за сегодня ты уже получил. Возвращайся завтра 🎉",
        )

    # Записываем прохождение и начисляем монеты атомарно.
    # UNIQUE(user, game, day) защищает от двойного начисления при гонке.
    completion = DailyGameCompletion(
        user_id=user.id, game=GAME_SUDOKU, day=day, coins_awarded=SUDOKU_REWARD
    )
    db.add(completion)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
        return SudokuSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=True,
            message="Награду за сегодня ты уже получил. Возвращайся завтра 🎉",
        )

    pet.coins = (pet.coins or 0) + SUDOKU_REWARD
    await db.commit()
    await db.refresh(pet)
    return SudokuSolveOut(
        correct=True,
        coins_awarded=SUDOKU_REWARD,
        coins=pet.coins,
        already_solved=False,
        message=f"Судоку решена! +{SUDOKU_REWARD} монет 🪙",
    )


@router.get("/games/memory/daily", response_model=DailyMemoryOut)
async def daily_memory(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    day = _today()
    return DailyMemoryOut(
        date=day.isoformat(),
        cards=_daily_memory_cards(day),
        reward=MEMORY_REWARD,
        max_moves=MEMORY_MAX_MOVES,
        solved_today=await _solved_today(db, user.id, GAME_MEMORY, day),
    )


@router.post("/games/memory/solve", response_model=MemorySolveOut)
async def solve_memory(
    data: MemorySolveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    day = _today()
    pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
    if pet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pet not found")

    success = data.matched_pairs >= MEMORY_PAIRS and data.moves <= MEMORY_MAX_MOVES
    if not success:
        return MemorySolveOut(
            correct=False,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=await _solved_today(db, user.id, GAME_MEMORY, day),
            message="Попробуй ещё раз: нужно найти все пары за лимит ходов.",
        )

    if await _solved_today(db, user.id, GAME_MEMORY, day):
        return MemorySolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=True,
            message="Пары собраны. Награда за сегодня уже получена.",
        )

    completion = DailyGameCompletion(
        user_id=user.id, game=GAME_MEMORY, day=day, coins_awarded=MEMORY_REWARD
    )
    db.add(completion)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
        return MemorySolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins if pet else 0,
            already_solved=True,
            message="Награда за сегодня уже получена.",
        )

    pet.coins = (pet.coins or 0) + MEMORY_REWARD
    await db.commit()
    await db.refresh(pet)
    return MemorySolveOut(
        correct=True,
        coins_awarded=MEMORY_REWARD,
        coins=pet.coins,
        already_solved=False,
        message=f"Пары собраны! +{MEMORY_REWARD} монет",
    )
