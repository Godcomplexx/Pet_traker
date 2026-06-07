from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.models import DailyGameCompletion, MinesweeperScore, Pet, User, WorkspaceMember
from app.schemas import (
    DailyMinesweeperOut,
    MinesweeperScoreOut,
    MinesweeperSolveIn,
    MinesweeperSolveOut,
)
from app.services import minesweeper

router = APIRouter(tags=["minesweeper"])


def _today():
    return datetime.now(timezone.utc).date()


async def _solved_today(db: AsyncSession, user_id: str, day) -> bool:
    row = await db.scalar(
        select(DailyGameCompletion).where(
            DailyGameCompletion.user_id == user_id,
            DailyGameCompletion.game == minesweeper.GAME_ID,
            DailyGameCompletion.day == day,
        )
    )
    return row is not None


async def _my_score(db: AsyncSession, user_id: str, day) -> MinesweeperScore | None:
    return await db.scalar(
        select(MinesweeperScore).where(
            MinesweeperScore.user_id == user_id,
            MinesweeperScore.puzzle_date == day.isoformat(),
        )
    )


async def _record_score(db: AsyncSession, user_id: str, day, seconds: int) -> MinesweeperScore | None:
    if seconds <= 0:
        return await _my_score(db, user_id, day)
    best = await _my_score(db, user_id, day)
    if best is None:
        best = MinesweeperScore(user_id=user_id, puzzle_date=day.isoformat(), seconds=seconds)
        db.add(best)
    elif seconds < best.seconds:
        best.seconds = seconds
    return best


@router.get("/games/minesweeper/daily", response_model=DailyMinesweeperOut)
async def daily_minesweeper(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    day = _today()
    best = await _my_score(db, user.id, day)
    return DailyMinesweeperOut(
        **minesweeper.daily_board(day),
        solved_today=await _solved_today(db, user.id, day),
        best_seconds=best.seconds if best else None,
    )


@router.post("/games/minesweeper/solve", response_model=MinesweeperSolveOut)
async def solve_minesweeper(
    data: MinesweeperSolveIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    day = _today()
    pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
    if pet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pet not found")

    if not minesweeper.is_solved(day, data.revealed):
        return MinesweeperSolveOut(
            correct=False,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=await _solved_today(db, user.id, day),
            message="Поле ещё не очищено: открой все безопасные клетки и не открывай мины.",
        )

    best = await _record_score(db, user.id, day, data.seconds)
    if await _solved_today(db, user.id, day):
        await db.commit()
        if best is not None:
            await db.refresh(best)
        return MinesweeperSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins or 0,
            already_solved=True,
            message="Сапёр пройден. Награда за сегодня уже получена, время записано в рейтинг.",
            best_seconds=best.seconds if best else None,
            seconds=data.seconds or None,
        )

    completion = DailyGameCompletion(
        user_id=user.id,
        game=minesweeper.GAME_ID,
        day=day,
        coins_awarded=minesweeper.REWARD,
    )
    db.add(completion)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        pet = await db.scalar(select(Pet).where(Pet.user_id == user.id))
        return MinesweeperSolveOut(
            correct=True,
            coins_awarded=0,
            coins=pet.coins if pet else 0,
            already_solved=True,
            message="Награда за сегодня уже получена.",
        )

    pet.coins = (pet.coins or 0) + minesweeper.REWARD
    await db.commit()
    await db.refresh(pet)
    if best is not None:
        await db.refresh(best)
    return MinesweeperSolveOut(
        correct=True,
        coins_awarded=minesweeper.REWARD,
        coins=pet.coins,
        already_solved=False,
        message=f"Сапёр пройден! +{minesweeper.REWARD} монет",
        best_seconds=best.seconds if best else None,
        seconds=data.seconds or None,
    )


@router.get("/workspaces/{workspace_id}/minesweeper/leaderboard", response_model=list[MinesweeperScoreOut])
async def minesweeper_leaderboard(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    day = _today().isoformat()
    member_ids = (
        await db.scalars(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).all()
    if not member_ids:
        return []
    rows = (
        await db.execute(
            select(MinesweeperScore, User.display_name, User.email)
            .join(User, User.id == MinesweeperScore.user_id)
            .where(
                MinesweeperScore.puzzle_date == day,
                MinesweeperScore.user_id.in_(member_ids),
            )
            .order_by(MinesweeperScore.seconds.asc())
        )
    ).all()
    return [
        MinesweeperScoreOut(
            user_id=sc.user_id,
            name=(name or email or sc.user_id[:6]),
            seconds=sc.seconds,
            is_me=sc.user_id == user.id,
        )
        for (sc, name, email) in rows
    ]
