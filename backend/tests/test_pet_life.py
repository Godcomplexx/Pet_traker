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
    boost = await client.post("/pets/me/play", json={"action": "test_coins"}, headers=headers)
    assert boost.status_code == 200, boost.text
    assert boost.json()["coins"] == 100

    r = await client.post("/pets/me/play", json={"action": "pet"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["coins"] == 125


async def test_pet_feed_requires_food_and_consumes_it(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "food@lab.ru")
    headers = auth_headers(tokens)

    no_food = await client.post("/pets/me/play", json={"action": "feed"}, headers=headers)
    assert no_food.status_code == 400

    await client.post("/pets/me/play", json={"action": "test_coins"}, headers=headers)
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
