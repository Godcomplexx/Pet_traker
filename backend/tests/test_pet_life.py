"""Тамагочи-логика: decay во времени, забота от работы, состояния."""
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import Pet
from app.services.pet import apply_decay, pet_state, reward_care


def _pet(**kw) -> Pet:
    base = dict(hunger=80, energy=80, mood=80, xp=0, level=1)
    base.update(kw)
    p = Pet(**base)
    p.stats_updated_at = datetime.now(timezone.utc)
    return p


def test_decay_reduces_stats_over_time():
    pet = _pet(hunger=80, energy=80, mood=80)
    pet.stats_updated_at = datetime.now(timezone.utc) - timedelta(hours=10)
    apply_decay(pet)
    assert pet.hunger < 80  # проголодался
    assert pet.energy < 80  # устал
    assert 0 <= pet.hunger <= 100


def test_no_decay_without_time():
    pet = _pet(hunger=50)
    apply_decay(pet)  # прошло ~0 часов
    assert pet.hunger == 50


def test_work_feeds_pet():
    pet = _pet(hunger=40, energy=40, mood=40)
    reward_care(pet, scope="WORKSPACE")
    assert pet.hunger > 40 and pet.energy > 40 and pet.mood > 40


def test_personal_feeds_less_than_team():
    a = _pet(hunger=40)
    b = _pet(hunger=40)
    reward_care(a, scope="PERSONAL")
    reward_care(b, scope="WORKSPACE")
    assert b.hunger > a.hunger


def test_states():
    assert pet_state(_pet(hunger=80, energy=80, mood=80)) == "happy"
    assert pet_state(_pet(hunger=10)) == "hungry"
    assert pet_state(_pet(hunger=80, energy=10)) == "sleepy"
    assert pet_state(_pet(hunger=50, energy=50, mood=10)) == "sad"


async def test_pet_state_in_api(client):
    from tests.conftest import auth_headers, register

    tokens = await register(client, "life@lab.ru")
    r = await client.get("/pets/me", headers=auth_headers(tokens))
    body = r.json()
    assert "state" in body and "state_label" in body


async def test_pet_play_grants_coins(client):
    from tests.conftest import auth_headers, register

    tokens = await register(client, "play@lab.ru")
    headers = auth_headers(tokens)
    r = await client.post("/pets/me/play", json={"action": "pet"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["coins"] == 25


async def test_pet_feed_requires_food_and_consumes_it(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "food@lab.ru")
    headers = auth_headers(tokens)

    no_food = await client.post("/pets/me/play", json={"action": "feed"}, headers=headers)
    assert no_food.status_code == 400

    daily = await client.post("/pets/me/daily", headers=headers)
    assert daily.status_code == 200, daily.text
    bought = await client.post("/shop/buy", json={"item_id": "food_banana"}, headers=headers)
    assert bought.status_code == 200, bought.text
    assert bought.json()["food_inventory"]["food_banana"] == 1

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="food@lab.ru")))
        pet.hunger = 40
        await db.commit()

    fed = await client.post(
        "/pets/me/play", json={"action": "feed", "item_id": "food_banana"}, headers=headers
    )
    assert fed.status_code == 200, fed.text
    body = fed.json()
    assert body["hunger"] > 40
    assert "food_banana" not in body["food_inventory"]


async def test_shop_hides_body_and_accent_items(client):
    from app.services.shop import roll_case
    from tests.conftest import auth_headers, register

    tokens = await register(client, "shop-clean@lab.ru")
    headers = auth_headers(tokens)

    catalog = await client.get("/shop/items", headers=headers)
    assert catalog.status_code == 200, catalog.text
    types = {item["type"] for item in catalog.json()["items"]}
    assert "body" not in types
    assert "accent" not in types

    for _ in range(20):
        assert roll_case()["type"] not in {"body", "accent", "species", "character", "food"}


async def test_can_buy_and_equip_room_decor(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "decor@lab.ru")
    headers = auth_headers(tokens)

    catalog = await client.get("/shop/items", headers=headers)
    assert any(item["id"] == "decor_flower_pot" for item in catalog.json()["items"])

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="decor@lab.ru")))
        pet.coins = 100
        await db.commit()

    bought = await client.post("/shop/buy", json={"item_id": "decor_flower_pot"}, headers=headers)
    assert bought.status_code == 200, bought.text
    assert "decor_flower_pot" in bought.json()["inventory"]

    equipped = await client.post("/shop/equip", json={"item_id": "decor_flower_pot"}, headers=headers)
    assert equipped.status_code == 200, equipped.text
    assert equipped.json()["equipped"]["decor"] == "decor_flower_pot"


async def test_pet_play_respects_stats(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "stats@lab.ru")
    headers = auth_headers(tokens)
    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="stats@lab.ru")))
        pet.energy = 0
        pet.hunger = 80
        await db.commit()

    tired = await client.post("/pets/me/play", json={"action": "ball"}, headers=headers)
    assert tired.status_code == 400
    assert "энергии" in tired.json()["detail"]

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="stats@lab.ru")))
        pet.energy = 20
        pet.hunger = 80
        await db.commit()

    ok = await client.post("/pets/me/play", json={"action": "ball"}, headers=headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["energy"] == 8
    assert body["coins"] == 25


async def test_pet_sleep_restores_energy_without_coins(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "sleep@lab.ru")
    headers = auth_headers(tokens)
    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="sleep@lab.ru")))
        pet.energy = 35
        pet.mood = 50
        await db.commit()

    slept = await client.post("/pets/me/play", json={"action": "sleep"}, headers=headers)
    assert slept.status_code == 200, slept.text
    body = slept.json()
    assert body["energy"] == 100
    assert body["mood"] == 55
    assert body["coins"] == 0

    awake = await client.post("/pets/me/play", json={"action": "sleep"}, headers=headers)
    assert awake.status_code == 400


async def test_daily_claim_grants_coins_once_per_day(client):
    from tests.conftest import auth_headers, register

    tokens = await register(client, "daily@lab.ru")
    headers = auth_headers(tokens)

    first = await client.post("/pets/me/daily", headers=headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["coins_awarded"] == 30
    assert body["pet"]["coins"] == 30
    assert body["pet"]["daily_claimed_on"] is not None

    second = await client.post("/pets/me/daily", headers=headers)
    assert second.status_code == 400


async def test_sudoku_grants_daily_reward_after_valid_solution(client):
    from tests.conftest import auth_headers, register

    tokens = await register(client, "sudoku@lab.ru")
    headers = auth_headers(tokens)

    status = await client.get("/pets/me/sudoku", headers=headers)
    assert status.status_code == 200, status.text
    assert status.json()["reward"] == 40
    assert status.json()["completed_today"] is False

    wrong = await client.post(
        "/pets/me/sudoku",
        json={"grid": [[1, 2, 3, 4, 5, 6]] * 6},
        headers=headers,
    )
    assert wrong.status_code == 400

    from datetime import date
    from app.services import sudoku as sudoku_svc

    puzzle_date = date.fromisoformat(status.json()["puzzle_date"])
    solution = sudoku_svc.daily_solution(puzzle_date)
    solved = await client.post("/pets/me/sudoku", json={"grid": solution}, headers=headers)
    assert solved.status_code == 200, solved.text
    body = solved.json()
    assert body["coins_awarded"] == 40
    assert body["pet"]["coins"] == 40
    assert body["pet"]["sudoku_completed_on"] is not None

    again = await client.post("/pets/me/sudoku", json={"grid": solution}, headers=headers)
    assert again.status_code == 200, again.text
    assert again.json()["coins_awarded"] == 0
    assert again.json()["pet"]["coins"] == 40
