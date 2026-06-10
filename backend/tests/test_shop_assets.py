from app.core.database import SessionLocal
from app.models import Pet


async def test_imported_room_items_can_be_equipped_together(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "decor-items@lab.ru")
    headers = auth_headers(tokens)

    catalog = await client.get("/shop/items", headers=headers)
    assert catalog.status_code == 200, catalog.text
    imported = [item for item in catalog.json()["items"] if item["id"].startswith("decor_item_")]
    imported_food = [item for item in catalog.json()["items"] if item["id"].startswith("food_item_")]
    assert len(imported) >= 50
    assert {"decor_item_balloon", "decor_item_photo_frame"}.issubset({item["id"] for item in imported})
    assert {"food_item_banana", "food_item_fish", "food_item_ramen"}.issubset(
        {item["id"] for item in imported_food}
    )
    assert not {"decor_item_banana", "decor_item_fish", "decor_item_ramen"} & {
        item["id"] for item in imported
    }
    assert all(item["data"]["file"].startswith("items/") for item in imported)
    assert all(item["data"]["file"].startswith("items/") for item in imported_food)
    by_id = {item["id"]: item for item in imported_food}
    assert by_id["food_item_banana"]["data"]["hunger"] < by_id["food_item_fish"]["data"]["hunger"]
    assert by_id["food_item_fish"]["data"]["hunger"] < by_id["food_item_ramen"]["data"]["hunger"]

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="decor-items@lab.ru")))
        pet.coins = 200
        await db.commit()

    for item_id in ("decor_item_balloon", "decor_item_photo_frame"):
        bought = await client.post("/shop/buy", json={"item_id": item_id}, headers=headers)
        assert bought.status_code == 200, bought.text
        equipped = await client.post("/shop/equip", json={"item_id": item_id}, headers=headers)
        assert equipped.status_code == 200, equipped.text

    body = equipped.json()
    assert set(body["equipped"]["decor"]) >= {"decor_item_balloon", "decor_item_photo_frame"}


async def test_can_buy_and_equip_pet_accessory(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "accessory@lab.ru")
    headers = auth_headers(tokens)

    catalog = await client.get("/shop/items", headers=headers)
    assert catalog.status_code == 200, catalog.text
    accessories = [item for item in catalog.json()["items"] if item["type"] == "accessory"]
    assert {item["id"] for item in accessories} == {
        "accessory_bunan_black",
        "accessory_maru_black",
        "accessory_tsuyome_black",
        "accessory_yasashime_black",
    }
    assert all(item["data"]["file"].endswith("_64.png") for item in accessories)

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="accessory@lab.ru")))
        pet.coins = 200
        await db.commit()

    bought = await client.post("/shop/buy", json={"item_id": "accessory_bunan_black"}, headers=headers)
    assert bought.status_code == 200, bought.text
    assert "accessory_bunan_black" in bought.json()["inventory"]

    equipped = await client.post("/shop/equip", json={"item_id": "accessory_bunan_black"}, headers=headers)
    assert equipped.status_code == 200, equipped.text
    assert equipped.json()["equipped"]["accessory"] == "accessory_bunan_black"


async def test_imported_food_is_consumable_not_decor(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "imported-food@lab.ru")
    headers = auth_headers(tokens)

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="imported-food@lab.ru")))
        pet.coins = 100
        pet.hunger = 40
        await db.commit()

    bought = await client.post("/shop/buy", json={"item_id": "food_item_ramen"}, headers=headers)
    assert bought.status_code == 200, bought.text
    assert "food_item_ramen" not in bought.json()["inventory"]
    assert bought.json()["food_inventory"]["food_item_ramen"] == 1

    equip = await client.post("/shop/equip", json={"item_id": "food_item_ramen"}, headers=headers)
    assert equip.status_code == 400

    fed = await client.post(
        "/pets/me/play",
        json={"action": "feed", "item_id": "food_item_ramen"},
        headers=headers,
    )
    assert fed.status_code == 200, fed.text
    body = fed.json()
    assert body["hunger"] == 78
    assert body["food_inventory"].get("food_item_ramen") is None
