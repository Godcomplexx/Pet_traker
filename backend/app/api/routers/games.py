"""Ежедневные мини-игры. Сейчас — судоку 6×6 с наградой +50 монет раз в день."""
from __future__ import annotations

import random
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import DailyGameCompletion, Pet, SudokuScore, User, ZipScore
from app.schemas import (
    DailySudokuOut,
    SudokuSolveIn,
    SudokuSolveOut,
    DailyZipOut,
    ZipSolveIn,
    ZipSolveOut,
)
from app.services import sudoku

router = APIRouter(tags=["games"])

GAME_SUDOKU = "sudoku"
GAME_ZIP = "zip"
SUDOKU_REWARD = 50
ZIP_REWARD = 45
ZIP_SIZE = 7
ZIP_MARKERS = 16


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


async def _my_sudoku_score(db: AsyncSession, user_id: str, day) -> SudokuScore | None:
    return await db.scalar(
        select(SudokuScore).where(
            SudokuScore.user_id == user_id,
            SudokuScore.puzzle_date == day.isoformat(),
        )
    )


async def _record_sudoku_score(
    db: AsyncSession, user_id: str, day, seconds: int, hints_used: int = 0
) -> SudokuScore | None:
    if seconds <= 0:
        return await _my_sudoku_score(db, user_id, day)

    best = await _my_sudoku_score(db, user_id, day)
    if best is None:
        best = SudokuScore(
            user_id=user_id,
            puzzle_date=day.isoformat(),
            seconds=seconds,
            hints_used=hints_used,
        )
        db.add(best)
    elif seconds < best.seconds:
        best.seconds = seconds
        best.hints_used = hints_used
    return best


async def _my_zip_score(db: AsyncSession, user_id: str, day) -> ZipScore | None:
    return await db.scalar(
        select(ZipScore).where(
            ZipScore.user_id == user_id,
            ZipScore.puzzle_date == day.isoformat(),
        )
    )


async def _record_zip_score(db: AsyncSession, user_id: str, day, seconds: int) -> ZipScore | None:
    if seconds <= 0:
        return await _my_zip_score(db, user_id, day)

    best = await _my_zip_score(db, user_id, day)
    if best is None:
        best = ZipScore(
            user_id=user_id,
            puzzle_date=day.isoformat(),
            seconds=seconds,
        )
        db.add(best)
    elif seconds < best.seconds:
        best.seconds = seconds
    return best


def _zip_neighbors(cell: tuple[int, int]) -> list[tuple[int, int]]:
    r, c = cell
    out: list[tuple[int, int]] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < ZIP_SIZE and 0 <= nc < ZIP_SIZE:
            out.append((nr, nc))
    return out


@lru_cache(maxsize=90)
def _zip_solution_cached(day_iso: str) -> tuple[tuple[int, int], ...]:
    path: list[tuple[int, int]] = []
    for r in range(ZIP_SIZE):
        cols = range(ZIP_SIZE) if r % 2 == 0 else range(ZIP_SIZE - 1, -1, -1)
        for c in cols:
            path.append((r, c))

    rng = random.Random(f"zip:{day_iso}")
    for _ in range(700):
        index = {cell: i for i, cell in enumerate(path)}
        if rng.choice((True, False)):
            endpoint = path[0]
            candidates = [n for n in _zip_neighbors(endpoint) if n in index and index[n] > 1]
            if not candidates:
                continue
            j = index[rng.choice(candidates)]
            path = list(reversed(path[:j])) + path[j:]
        else:
            endpoint = path[-1]
            candidates = [
                n for n in _zip_neighbors(endpoint) if n in index and index[n] < len(path) - 2
            ]
            if not candidates:
                continue
            j = index[rng.choice(candidates)]
            path = path[: j + 1] + list(reversed(path[j + 1 :]))

    return tuple(path)


def _zip_solution(day) -> list[list[int]]:
    return [[r, c] for r, c in _zip_solution_cached(day.isoformat())]


def _zip_markers(day) -> list[dict]:
    path = _zip_solution(day)
    last = len(path) - 1
    return [
        {"row": path[round(i * last / (ZIP_MARKERS - 1))][0],
         "col": path[round(i * last / (ZIP_MARKERS - 1))][1],
         "value": i + 1}
        for i in range(ZIP_MARKERS)
    ]


def _valid_zip_path(path: list[list[int]], day) -> bool:
    if len(path) != ZIP_SIZE * ZIP_SIZE:
        return False
    markers = {(m["row"], m["col"]): m["value"] for m in _zip_markers(day)}
    seen: set[tuple[int, int]] = set()
    marker_value = 1
    prev: tuple[int, int] | None = None
    for cell in path:
        if not isinstance(cell, list) or len(cell) != 2:
            return False
        r, c = cell
        if not isinstance(r, int) or not isinstance(c, int):
            return False
        if r < 0 or r >= ZIP_SIZE or c < 0 or c >= ZIP_SIZE:
            return False
        pos = (r, c)
        if pos in seen:
            return False
        if prev is not None and abs(prev[0] - r) + abs(prev[1] - c) != 1:
            return False
        if pos in markers:
            if markers[pos] != marker_value:
                return False
            marker_value += 1
        seen.add(pos)
        prev = pos
    return marker_value == ZIP_MARKERS + 1


@router.get("/games/sudoku/daily", response_model=DailySudokuOut)
async def daily_sudoku(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Головоломка дня (одна для всех) + флаг, прошёл ли её пользователь сегодня."""
    day = _today()
    puzzle = sudoku.daily_puzzle(day)
    solved = await _solved_today(db, user.id, GAME_SUDOKU, day)
    best = await _my_sudoku_score(db, user.id, day)
    return DailySudokuOut(
        date=puzzle["date"],
        size=puzzle["size"],
        block_rows=puzzle["block_rows"],
        block_cols=puzzle["block_cols"],
        puzzle=puzzle["puzzle"],
        reward=SUDOKU_REWARD,
        solved_today=solved,
        best_seconds=best.seconds if best else None,
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

    best = await _record_sudoku_score(db, user.id, day, data.seconds, data.hints_used)

    # Уже была награда сегодня?
    if await _solved_today(db, user.id, GAME_SUDOKU, day):
        await db.commit()
        if best is not None:
            await db.refresh(best)
        return SudokuSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=True,
            message="Верно! Награда за сегодня уже получена, время записано в рейтинг.",
            best_seconds=best.seconds if best else None,
            seconds=data.seconds or None,
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
    if best is not None:
        await db.refresh(best)
    return SudokuSolveOut(
        correct=True,
        coins_awarded=SUDOKU_REWARD,
        coins=pet.coins,
        already_solved=False,
        message=f"Судоку решена! +{SUDOKU_REWARD} монет 🪙",
        best_seconds=best.seconds if best else None,
        seconds=data.seconds or None,
    )


@router.get("/games/zip/daily", response_model=DailyZipOut)
async def daily_zip(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    day = _today()
    best = await _my_zip_score(db, user.id, day)
    return DailyZipOut(
        date=day.isoformat(),
        size=ZIP_SIZE,
        markers=_zip_markers(day),
        solution_path=_zip_solution(day),
        reward=ZIP_REWARD,
        solved_today=await _solved_today(db, user.id, GAME_ZIP, day),
        best_seconds=best.seconds if best else None,
    )


@router.post("/games/zip/solve", response_model=ZipSolveOut)
async def solve_zip(
    data: ZipSolveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    day = _today()
    pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
    if pet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pet not found")

    if not _valid_zip_path(data.path, day):
        return ZipSolveOut(
            correct=False,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=await _solved_today(db, user.id, GAME_ZIP, day),
            message="Путь неверный: соединяй числа по порядку и заполни все клетки.",
        )

    best = await _record_zip_score(db, user.id, day, data.seconds)

    if await _solved_today(db, user.id, GAME_ZIP, day):
        await db.commit()
        if best is not None:
            await db.refresh(best)
        return ZipSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=True,
            message="Zip пройден. Награда за сегодня уже получена, время записано в рейтинг.",
            best_seconds=best.seconds if best else None,
            seconds=data.seconds or None,
        )

    completion = DailyGameCompletion(
        user_id=user.id, game=GAME_ZIP, day=day, coins_awarded=ZIP_REWARD
    )
    db.add(completion)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
        return ZipSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins if pet else 0,
            already_solved=True,
            message="Награда за сегодня уже получена.",
        )

    pet.coins = (pet.coins or 0) + ZIP_REWARD
    await db.commit()
    await db.refresh(pet)
    if best is not None:
        await db.refresh(best)
    return ZipSolveOut(
        correct=True,
        coins_awarded=ZIP_REWARD,
        coins=pet.coins,
        already_solved=False,
        message=f"Zip пройден! +{ZIP_REWARD} монет",
        best_seconds=best.seconds if best else None,
        seconds=data.seconds or None,
    )
