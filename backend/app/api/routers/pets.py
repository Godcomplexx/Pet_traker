from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.models import Pet, User, WorkspaceMember
from app.schemas import PetCustomize, PetOut, PetUpdate
from app.services.pet import apply_decay, pet_state, state_label

router = APIRouter(tags=["pets"])


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


@router.get("/workspaces/{workspace_id}/pets", response_model=list[PetOut])
async def workspace_pets(
    workspace_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await require_membership(workspace_id, db, user)
    member_ids = (
        await db.scalars(
            select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
        )
    ).all()
    pets = (await db.scalars(select(Pet).where(Pet.user_id.in_(member_ids)))).all()
    for p in pets:
        apply_decay(p)
    await db.commit()
    return [_to_out(p) for p in pets]
