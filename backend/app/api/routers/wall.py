"""Стена рабочего пространства — лёгкая лента для участников."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.enums import NotificationType
from app.models import Notification, Pet, RpsChallenge, User, WallPost, WallPresence, WallReaction, WorkspaceMember
from app.schemas import (
    RpsChallengeOut,
    RpsChoiceIn,
    RpsInviteIn,
    RpsRespondIn,
    WallPostCreate,
    WallPostOut,
    WallReactionIn,
)

router = APIRouter(tags=["wall"])
WALL_TTL = timedelta(hours=24)
PRESENCE_TTL = timedelta(seconds=75)
RPS_REWARD = 5
RPS_CHOICES = {"rock": "Камень", "paper": "Бумага", "scissors": "Ножницы"}
RPS_BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}


async def _cleanup_wall(db: AsyncSession, workspace_id: str) -> None:
    cutoff = datetime.now(timezone.utc) - WALL_TTL
    await db.execute(
        delete(WallPost)
        .where(WallPost.workspace_id == workspace_id, WallPost.created_at < cutoff)
        .execution_options(synchronize_session=False)
    )


async def _cleanup_presence(db: AsyncSession, workspace_id: str) -> None:
    cutoff = datetime.now(timezone.utc) - PRESENCE_TTL
    await db.execute(
        delete(WallPresence)
        .where(WallPresence.workspace_id == workspace_id, WallPresence.last_seen_at < cutoff)
        .execution_options(synchronize_session=False)
    )


async def _member_exists(db: AsyncSession, workspace_id: str, user_id: str) -> bool:
    row = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    return row is not None


async def _user_name(db: AsyncSession, user_id: str) -> str:
    user = await db.get(User, user_id)
    return (user and (user.display_name or user.email)) or user_id[:8]


def _rps_winner(challenger_id: str, opponent_id: str, challenger_choice: str, opponent_choice: str) -> str | None:
    if challenger_choice == opponent_choice:
        return None
    if RPS_BEATS[challenger_choice] == opponent_choice:
        return challenger_id
    return opponent_id


async def _finish_rps_if_ready(db: AsyncSession, challenge: RpsChallenge) -> None:
    if challenge.status != "accepted" or not challenge.challenger_choice or not challenge.opponent_choice:
        return
    winner_id = _rps_winner(
        challenge.challenger_id,
        challenge.opponent_id,
        challenge.challenger_choice,
        challenge.opponent_choice,
    )
    challenge.winner_id = winner_id
    challenge.status = "draw" if winner_id is None else "completed"
    challenge.completed_at = datetime.now(timezone.utc)

    challenger_name = await _user_name(db, challenge.challenger_id)
    opponent_name = await _user_name(db, challenge.opponent_id)
    if winner_id and not challenge.reward_awarded:
        pet = await db.scalar(select(Pet).where(Pet.user_id == winner_id))
        if pet is not None:
            pet.coins = int(pet.coins or 0) + RPS_REWARD
        challenge.reward_awarded = True
    winner_text = "ничья" if winner_id is None else f"победил {await _user_name(db, winner_id)} (+{RPS_REWARD} монет)"
    db.add(WallPost(
        workspace_id=challenge.workspace_id,
        author_id=challenge.challenger_id,
        text=(
            "Камень-ножницы-бумага: "
            f"{challenger_name} выбрал {RPS_CHOICES[challenge.challenger_choice]}, "
            f"{opponent_name} выбрал {RPS_CHOICES[challenge.opponent_choice]} - {winner_text}."
        ),
    ))


async def _reaction_maps(
    db: AsyncSession, post_ids: list[str], user_id: str
) -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    if not post_ids:
        return {}, {}
    count_rows = (
        await db.execute(
            select(WallReaction.post_id, WallReaction.emoji, func.count(WallReaction.id))
            .where(WallReaction.post_id.in_(post_ids))
            .group_by(WallReaction.post_id, WallReaction.emoji)
        )
    ).all()
    counts: dict[str, dict[str, int]] = {}
    for post_id, emoji, count in count_rows:
        counts.setdefault(post_id, {})[emoji] = int(count)

    mine_rows = (
        await db.execute(
            select(WallReaction.post_id, WallReaction.emoji).where(
                WallReaction.post_id.in_(post_ids),
                WallReaction.user_id == user_id,
            )
        )
    ).all()
    mine: dict[str, list[str]] = {}
    for post_id, emoji in mine_rows:
        mine.setdefault(post_id, []).append(emoji)
    return counts, mine


def _wall_out(
    post: WallPost,
    author_name: str,
    counts: dict[str, dict[str, int]] | None = None,
    mine: dict[str, list[str]] | None = None,
) -> WallPostOut:
    return WallPostOut(
        id=post.id,
        author_id=post.author_id,
        author_name=author_name,
        text=post.text,
        image_data=post.image_data,
        reactions=(counts or {}).get(post.id, {}),
        my_reactions=(mine or {}).get(post.id, []),
        created_at=post.created_at,
    )


@router.post(
    "/workspaces/{workspace_id}/rps",
    response_model=RpsChallengeOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_rps_challenge(
    workspace_id: str,
    data: RpsInviteIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    if data.opponent_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя вызвать самого себя")
    if not await _member_exists(db, workspace_id, data.opponent_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Участник не найден")
    challenge = RpsChallenge(
        workspace_id=workspace_id,
        challenger_id=user.id,
        opponent_id=data.opponent_id,
        challenger_choice=data.choice,
    )
    db.add(challenge)
    await db.flush()
    db.add(Notification(
        user_id=data.opponent_id,
        workspace_id=workspace_id,
        type=NotificationType.MENTION,
        title="Вызов: камень-ножницы-бумага",
        body=f"{user.display_name or user.email} предлагает сыграть на стене",
        entity_type="rps_challenge",
        entity_id=challenge.id,
    ))
    db.add(WallPost(
        workspace_id=workspace_id,
        author_id=user.id,
        text=f"{user.display_name or user.email} предложил сыграть в камень-ножницы-бумага.",
    ))
    await db.commit()
    await db.refresh(challenge)
    return challenge


@router.get("/rps/challenges", response_model=list[RpsChallengeOut])
async def my_rps_challenges(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(RpsChallenge)
        .where((RpsChallenge.challenger_id == user.id) | (RpsChallenge.opponent_id == user.id))
        .where(RpsChallenge.status.in_(["pending", "accepted"]))
        .order_by(RpsChallenge.created_at.desc())
    )
    return rows.all()


@router.post("/rps/challenges/{challenge_id}/respond", response_model=RpsChallengeOut)
async def respond_rps_challenge(
    challenge_id: str,
    data: RpsRespondIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    challenge = await db.get(RpsChallenge, challenge_id)
    if challenge is None or challenge.opponent_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вызов не найден")
    if challenge.status != "pending":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "На этот вызов уже ответили")
    challenge.status = "accepted" if data.accept else "declined"
    challenge.responded_at = datetime.now(timezone.utc)
    if not data.accept:
        db.add(WallPost(
            workspace_id=challenge.workspace_id,
            author_id=user.id,
            text=f"{user.display_name or user.email} отказался от игры в камень-ножницы-бумага.",
        ))
    await db.commit()
    await db.refresh(challenge)
    return challenge


@router.post("/rps/challenges/{challenge_id}/choice", response_model=RpsChallengeOut)
async def choose_rps(
    challenge_id: str,
    data: RpsChoiceIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    challenge = await db.get(RpsChallenge, challenge_id)
    if challenge is None or user.id not in {challenge.challenger_id, challenge.opponent_id}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вызов не найден")
    if challenge.status != "accepted":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Игра ещё не принята")
    if user.id == challenge.challenger_id:
        challenge.challenger_choice = data.choice
    else:
        challenge.opponent_choice = data.choice
    await _finish_rps_if_ready(db, challenge)
    await db.commit()
    await db.refresh(challenge)
    return challenge


@router.get("/workspaces/{workspace_id}/wall", response_model=list[WallPostOut])
async def list_wall(
    workspace_id: str,
    limit: int = Query(50, le=100),
    before: str | None = None,  # id поста для пагинации «загрузить ещё»
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    await _cleanup_wall(db, workspace_id)
    await db.commit()
    q = select(WallPost, User.display_name, User.email).join(
        User, User.id == WallPost.author_id
    ).where(WallPost.workspace_id == workspace_id)
    if before:
        anchor = await db.get(WallPost, before)
        if anchor is not None:
            q = q.where(WallPost.created_at < anchor.created_at)
    q = q.order_by(WallPost.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).all()
    post_ids = [p.id for (p, _name, _email) in rows]
    counts, mine = await _reaction_maps(db, post_ids, user.id)
    return [
        _wall_out(p, (name or email or p.author_id[:8]), counts, mine)
        for (p, name, email) in rows
    ]


@router.post("/workspaces/{workspace_id}/wall", response_model=WallPostOut, status_code=status.HTTP_201_CREATED)
async def create_wall_post(
    workspace_id: str,
    data: WallPostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    await _cleanup_wall(db, workspace_id)
    text = data.text.strip()
    if not text and not data.image_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Добавьте текст или картинку")
    post = WallPost(workspace_id=workspace_id, author_id=user.id, text=text, image_data=data.image_data)
    db.add(post)
    await db.flush()
    await db.commit()
    await db.refresh(post)
    return _wall_out(post, (user.display_name or user.email or user.id[:8]))


@router.post("/workspaces/{workspace_id}/wall/presence", status_code=status.HTTP_204_NO_CONTENT)
async def wall_presence(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    await _cleanup_presence(db, workspace_id)
    row = await db.scalar(
        select(WallPresence).where(
            WallPresence.workspace_id == workspace_id,
            WallPresence.user_id == user.id,
        )
    )
    if row is None:
        db.add(WallPresence(workspace_id=workspace_id, user_id=user.id))
    else:
        row.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return None


@router.delete("/workspaces/{workspace_id}/wall/presence", status_code=status.HTTP_204_NO_CONTENT)
async def leave_wall(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    await db.execute(
        delete(WallPresence)
        .where(WallPresence.workspace_id == workspace_id, WallPresence.user_id == user.id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return None


@router.post("/wall/{post_id}/react", response_model=WallPostOut)
async def react_wall_post(
    post_id: str,
    data: WallReactionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(WallPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пост не найден")
    await require_membership(post.workspace_id, db, user)
    await _cleanup_wall(db, post.workspace_id)
    existing = await db.scalar(
        select(WallReaction).where(
            WallReaction.post_id == post_id,
            WallReaction.user_id == user.id,
            WallReaction.emoji == data.emoji,
        )
    )
    if existing:
        await db.delete(existing)
    else:
        db.add(WallReaction(post_id=post_id, user_id=user.id, emoji=data.emoji))
    await db.commit()
    await db.refresh(post)
    author = await db.get(User, post.author_id)
    counts, mine = await _reaction_maps(db, [post.id], user.id)
    return _wall_out(post, ((author and (author.display_name or author.email)) or post.author_id[:8]), counts, mine)


@router.post("/wall/{post_id}/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_wall_post(
    post_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    post = await db.get(WallPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пост не найден")
    await require_membership(post.workspace_id, db, user)
    await db.delete(post)
    await db.commit()
    return None


@router.delete("/wall/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wall_post(
    post_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    post = await db.get(WallPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пост не найден")
    # удалять может только автор
    if post.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Можно удалять только свои сообщения")
    await db.delete(post)
    await db.commit()
