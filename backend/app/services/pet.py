"""Tamagotchi-style pet lifecycle.

The pet decays lazily whenever it is read or changed. Work events call
`reward_care`, so completing tasks keeps the pet alive without a background
tick being required for correctness.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import Pet

HUNGER_DECAY_PER_HOUR = 4
ENERGY_DECAY_PER_HOUR = 3
MOOD_DECAY_PER_HOUR = 2

FEED_ON_TEAM_TASK = 12
FEED_ON_PERSONAL_TASK = 8
ENERGY_ON_TASK = 6
MOOD_ON_TASK = 8
FEED_ON_MILESTONE = 20
MOOD_ON_MILESTONE = 18

DEATH_GRACE_HOURS = 24


def _clamp(v: float) -> int:
    return max(0, min(100, round(v)))


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def apply_decay(pet: Pet, now: datetime | None = None) -> None:
    """Apply time decay and mark death after prolonged starvation."""
    now = now or datetime.now(timezone.utc)
    if pet.is_dead:
        pet.hunger = 0
        pet.energy = 0
        pet.mood = 0
        pet.stats_updated_at = now
        return

    last = _as_aware(pet.stats_updated_at or now)
    hours = (now - last).total_seconds() / 3600.0
    if hours <= 0:
        _update_life_status(pet, now, last, pet.hunger)
        return

    previous_hunger = pet.hunger
    pet.hunger = _clamp(pet.hunger - HUNGER_DECAY_PER_HOUR * hours)
    pet.energy = _clamp(pet.energy - ENERGY_DECAY_PER_HOUR * hours)

    wellbeing = (pet.hunger + pet.energy) / 2
    if pet.mood > wellbeing:
        pet.mood = _clamp(max(wellbeing, pet.mood - MOOD_DECAY_PER_HOUR * hours))

    _update_life_status(pet, now, last, previous_hunger)
    pet.stats_updated_at = now


def _update_life_status(pet: Pet, now: datetime, last: datetime, previous_hunger: int) -> None:
    if pet.hunger > 0:
        pet.neglect_started_at = None
        return

    neglect_started = pet.neglect_started_at
    if neglect_started is not None:
        neglect_started = _as_aware(neglect_started)
    else:
        hours_to_zero = max(previous_hunger, 0) / HUNGER_DECAY_PER_HOUR if previous_hunger > 0 else 0
        neglect_started = last + timedelta(hours=hours_to_zero)
        pet.neglect_started_at = neglect_started

    if now - neglect_started >= timedelta(hours=DEATH_GRACE_HOURS):
        pet.is_dead = True
        pet.died_at = neglect_started + timedelta(hours=DEATH_GRACE_HOURS)
        pet.hunger = 0
        pet.energy = 0
        pet.mood = 0


def revive_pet(pet: Pet, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    pet.is_dead = False
    pet.died_at = None
    pet.neglect_started_at = None
    pet.hunger = 35
    pet.energy = 35
    pet.mood = 35
    pet.stats_updated_at = now


def reward_care(pet: Pet, *, scope: str, milestone: bool = False) -> None:
    """Reward real work with care. Dead pets require explicit revive first."""
    apply_decay(pet)
    if pet.is_dead:
        return

    if milestone:
        pet.hunger = _clamp(pet.hunger + FEED_ON_MILESTONE)
        pet.mood = _clamp(pet.mood + MOOD_ON_MILESTONE)
        pet.energy = _clamp(pet.energy + ENERGY_ON_TASK)
    else:
        feed = FEED_ON_PERSONAL_TASK if scope == "PERSONAL" else FEED_ON_TEAM_TASK
        pet.hunger = _clamp(pet.hunger + feed)
        pet.energy = _clamp(pet.energy + ENERGY_ON_TASK)
        pet.mood = _clamp(pet.mood + MOOD_ON_TASK)
    pet.neglect_started_at = None


def pet_state(pet: Pet) -> str:
    if pet.is_dead:
        return "dead"
    if pet.energy <= 15:
        return "sleepy"
    if pet.hunger <= 15:
        return "hungry"
    if pet.mood <= 25:
        return "sad"
    if pet.hunger >= 70 and pet.mood >= 70 and pet.energy >= 60:
        return "happy"
    return "ok"


def state_label(state: str) -> str:
    return {
        "dead": "питомец умер - оживи его",
        "sleepy": "без сил - нужен отдых",
        "hungry": "проголодался - закрой задачу или покорми",
        "sad": "загрустил - давно не было работы",
        "happy": "доволен и сыт!",
        "ok": "в порядке",
    }.get(state, "в порядке")
