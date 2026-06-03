"""Тамагочи-логика: decay во времени, забота от работы, состояния."""
from datetime import datetime, timedelta, timezone

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
    r = await client.post("/pets/me/play", json={"action": "feed"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["coins"] == 25

    boost = await client.post("/pets/me/play", json={"action": "test_coins"}, headers=headers)
    assert boost.status_code == 200, boost.text
    assert boost.json()["coins"] == 125
