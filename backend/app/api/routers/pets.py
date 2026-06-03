from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.models import Pet, User, WorkspaceMember
from app.schemas import CaseOpenOut, EquipIn, PetCustomize, PetOut, PetPlayIn, PetUpdate, ShopBuyIn
from app.services.pet import apply_decay, pet_state, state_label
from app.services.shop import CASE_PRICE, SHOP_ITEMS, get_item, roll_case

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


@router.post("/pets/me/play", response_model=PetOut)
async def play_with_pet(
    data: PetPlayIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    reward = 25
    if data.action == "feed":
        pet.hunger = min(100, pet.hunger + 12)
        pet.mood = min(100, pet.mood + 4)
    elif data.action == "pet":
        pet.mood = min(100, pet.mood + 12)
    elif data.action == "ball":
        pet.mood = min(100, pet.mood + 10)
        pet.energy = max(0, pet.energy - 4)
    else:
        reward = 100
    pet.coins = (pet.coins or 0) + reward
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


# ──────────────────────────── магазин / кейсы ────────────────────────────
@router.get("/shop/items")
async def shop_items(user: User = Depends(get_current_user)):
    """Каталог магазина (статичный, из кода)."""
    return {"items": SHOP_ITEMS, "case_price": CASE_PRICE}


def _grant_item(pet: Pet, item_id: str) -> bool:
    """Добавить предмет в инвентарь. True, если он новый."""
    inv = list(pet.inventory or [])
    if item_id in inv:
        return False
    inv.append(item_id)
    pet.inventory = inv  # переприсваиваем — иначе SQLAlchemy не заметит мутацию JSON
    return True


@router.post("/shop/buy", response_model=PetOut)
async def shop_buy(
    data: ShopBuyIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    item = get_item(data.item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
    if data.item_id in (pet.inventory or []):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Уже куплено")
    if (pet.coins or 0) < item["price"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недостаточно монет")
    pet.coins -= item["price"]
    _grant_item(pet, data.item_id)
    await db.commit()
    await db.refresh(pet)
    return _to_out(pet)


@router.post("/shop/open-case", response_model=CaseOpenOut)
async def shop_open_case(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    if (pet.coins or 0) < CASE_PRICE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недостаточно монет для кейса")
    pet.coins -= CASE_PRICE
    item = roll_case()
    is_new = _grant_item(pet, item["id"])
    # дубликат компенсируем монетами (1/4 цены), чтобы кейсы не были «пустыми»
    if not is_new:
        pet.coins += max(5, item["price"] // 4)
    await db.commit()
    await db.refresh(pet)
    return CaseOpenOut(item=item, is_new=is_new, coins=pet.coins)


@router.post("/shop/equip", response_model=PetOut)
async def shop_equip(
    data: EquipIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Надеть/снять купленный предмет. item_id=null снимает предмет своего типа."""
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    equipped = dict(pet.equipped or {})
    if data.item_id is None:
        # снять — но не знаем тип, поэтому ничего; фронт шлёт конкретный item_id
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Не указан предмет")
    item = get_item(data.item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
    if data.item_id not in (pet.inventory or []):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Предмет не куплен")
    # toggle: если уже надет этот предмет — снимаем, иначе надеваем
    if equipped.get(item["type"]) == data.item_id:
        equipped.pop(item["type"], None)
    else:
        equipped[item["type"]] = data.item_id
    pet.equipped = equipped
    # цвет тела применяем сразу (это не «шапка», а основной вид)
    if item["type"] == "body":
        pet.body_color = item["data"] if equipped.get("body") else pet.body_color
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
