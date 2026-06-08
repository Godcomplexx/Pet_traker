from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.models import Pet, User, WorkspaceMember
from app.schemas import CaseOpenOut, EquipIn, PetOut, ShopBuyIn
from app.services.pet import apply_decay, pet_state, state_label
from app.services.shop import CASE_PRICE, SHOP_ITEMS, get_item, roll_case

router = APIRouter(tags=["shop"])

CATALOG_ONLY_ITEM_TYPES = {"body", "accent", "species", "character"}


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


def _item_slot(item_id: str) -> str | None:
    item = get_item(item_id)
    if item is None:
        return None
    item_data = item.get("data")
    if not isinstance(item_data, dict):
        return None
    slot = item_data.get("slot")
    return str(slot) if slot else None


def _decor_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [
        str(item_id)
        for item_id in value
        if get_item(str(item_id)) and get_item(str(item_id))["type"] == "decor"
    ]


def _decor_slots(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(item_id): str(slot)
        for item_id, slot in value.items()
        if slot in {"floor-left", "floor-right", "shelf-left", "shelf-right"}
    }


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


def _grant_food(pet: Pet, item_id: str, amount: int = 1) -> None:
    food = dict(pet.food_inventory or {})
    food[item_id] = int(food.get(item_id, 0)) + amount
    pet.food_inventory = food



@router.post("/shop/buy", response_model=PetOut)
async def shop_buy(
    data: ShopBuyIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    pet = await _get_pet(db, user.id)
    apply_decay(pet)
    item = get_item(data.item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Товар не найден")
    if item["type"] in CATALOG_ONLY_ITEM_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этот предмет можно получить только через отдельную рулетку")
    if item["type"] != "food" and data.item_id in (pet.inventory or []):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Уже куплено")
    if (pet.coins or 0) < item["price"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Недостаточно монет")
    pet.coins -= item["price"]
    if item["type"] == "food":
        _grant_food(pet, data.item_id)
    else:
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
    if item["type"] in CATALOG_ONLY_ITEM_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этот предмет нельзя купить или надеть из магазина")
    if item["type"] == "food":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Еду нельзя надеть")
    if data.item_id not in (pet.inventory or []):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Предмет не куплен")
    if item["type"] == "decor":
        decor = _decor_list(equipped.get("decor"))
        decor_slots = _decor_slots(equipped.get("decor_slots"))
        if data.slot:
            target_slot = data.slot
            for item_id in list(decor):
                if item_id != data.item_id and decor_slots.get(item_id, _item_slot(item_id)) == target_slot:
                    decor.remove(item_id)
                    decor_slots.pop(item_id, None)
            if data.item_id not in decor:
                decor.append(data.item_id)
            for item_id, slot in list(decor_slots.items()):
                if item_id == data.item_id or slot == target_slot:
                    decor_slots.pop(item_id, None)
            decor_slots[data.item_id] = target_slot
        elif data.item_id in decor:
            decor = [item_id for item_id in decor if item_id != data.item_id]
            decor_slots.pop(data.item_id, None)
        else:
            slot = (item.get("data") or {}).get("slot") if isinstance(item.get("data"), dict) else None
            if slot:
                decor = [
                    item_id for item_id in decor
                    if decor_slots.get(item_id, _item_slot(item_id)) != slot
                ]
                decor_slots = {
                    item_id: item_slot
                    for item_id, item_slot in decor_slots.items()
                    if item_id in decor and item_slot != slot
                }
                decor_slots[data.item_id] = str(slot)
            decor.append(data.item_id)
        if decor:
            equipped["decor"] = decor
            equipped["decor_slots"] = {item_id: slot for item_id, slot in decor_slots.items() if item_id in decor}
        else:
            equipped.pop("decor", None)
            equipped.pop("decor_slots", None)
        pet.equipped = equipped
        await db.commit()
        await db.refresh(pet)
        return _to_out(pet)
    # toggle: если уже надет этот предмет — снимаем, иначе надеваем
    if equipped.get(item["type"]) == data.item_id:
        equipped.pop(item["type"], None)
    else:
        equipped[item["type"]] = data.item_id
    pet.equipped = equipped
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
