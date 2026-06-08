from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import Pet
from app.services.pet import apply_decay, pet_state, reward_care


def _pet(**kw) -> Pet:
    base = dict(hunger=80, energy=80, mood=80, xp=0, level=1)
    base.update(kw)
    pet = Pet(**base)
    pet.stats_updated_at = datetime.now(timezone.utc)
    return pet


def test_pet_dies_after_prolonged_starvation():
    pet = _pet(hunger=70, energy=80, mood=80)
    pet.stats_updated_at = datetime.now(timezone.utc) - timedelta(hours=42)

    apply_decay(pet)

    assert pet.is_dead is True
    assert pet_state(pet) == "dead"
    assert pet.hunger == 0
    assert pet.energy == 0
    assert pet.mood == 0
    assert pet.died_at is not None


def test_task_care_prevents_death_before_grace_expires():
    pet = _pet(hunger=70, energy=80, mood=80)
    pet.stats_updated_at = datetime.now(timezone.utc) - timedelta(hours=30)

    reward_care(pet, scope="WORKSPACE")

    assert pet.is_dead is not True
    assert pet.hunger > 0
    assert pet.neglect_started_at is None


async def test_dead_pet_can_be_revived(client):
    from sqlalchemy import select
    from tests.conftest import auth_headers, register

    tokens = await register(client, "revive@lab.ru")
    headers = auth_headers(tokens)

    async with SessionLocal() as db:
        pet = await db.scalar(select(Pet).where(Pet.user.has(email="revive@lab.ru")))
        pet.hunger = 70
        pet.energy = 80
        pet.mood = 80
        pet.stats_updated_at = datetime.now(timezone.utc) - timedelta(hours=42)
        await db.commit()

    dead = await client.get("/pets/me", headers=headers)
    assert dead.status_code == 200, dead.text
    assert dead.json()["state"] == "dead"
    assert dead.json()["is_dead"] is True

    blocked = await client.post("/pets/me/play", json={"action": "pet"}, headers=headers)
    assert blocked.status_code == 400

    revived = await client.post("/pets/me/revive", headers=headers)
    assert revived.status_code == 200, revived.text
    body = revived.json()
    assert body["is_dead"] is False
    assert body["state"] == "ok"
    assert body["hunger"] == 35
    assert body["energy"] == 35
    assert body["mood"] == 35
