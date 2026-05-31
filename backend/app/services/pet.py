"""Тамагочи-логика питомца.

Идея: питомец «живёт» во времени. Без заботы (= без выполненной работы) его
сытость, энергия и настроение постепенно падают. Реальная работа кормит и
бодрит питомца. XP/level по-прежнему меняются только через награды (FR-PET-4),
пользователь не управляет показателями напрямую.

Decay считается «лениво»: при каждом чтении/изменении питомца мы смотрим, сколько
прошло с `stats_updated_at`, и применяем убыль. Это не требует постоянного воркера
(хотя фоновый тик тоже поддержан — см. worker.tick_pets).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models import Pet

# Сколько единиц теряется в час без заботы.
HUNGER_DECAY_PER_HOUR = 4   # сытость падает (питомец проголодался)
ENERGY_DECAY_PER_HOUR = 3   # энергия падает (устаёт)
# Настроение тянется к среднему от сытости и энергии.
MOOD_DECAY_PER_HOUR = 2

# Прибавки за выполненную работу (забота).
FEED_ON_TEAM_TASK = 12
FEED_ON_PERSONAL_TASK = 8
ENERGY_ON_TASK = 6
MOOD_ON_TASK = 8
# Крупные события (статья опубликована, проект завершён).
FEED_ON_MILESTONE = 20
MOOD_ON_MILESTONE = 18


def _clamp(v: float) -> int:
    return max(0, min(100, round(v)))


def apply_decay(pet: Pet, now: datetime | None = None) -> None:
    """Уменьшить показатели соответственно прошедшему времени. Идемпотентно по now."""
    now = now or datetime.now(timezone.utc)
    last = pet.stats_updated_at or now
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    hours = (now - last).total_seconds() / 3600.0
    if hours <= 0:
        return

    pet.hunger = _clamp(pet.hunger - HUNGER_DECAY_PER_HOUR * hours)
    pet.energy = _clamp(pet.energy - ENERGY_DECAY_PER_HOUR * hours)
    # Настроение дрейфует к «самочувствию» (среднее сытости и энергии).
    wellbeing = (pet.hunger + pet.energy) / 2
    if pet.mood > wellbeing:
        pet.mood = _clamp(max(wellbeing, pet.mood - MOOD_DECAY_PER_HOUR * hours))
    pet.stats_updated_at = now


def reward_care(pet: Pet, *, scope: str, milestone: bool = False) -> None:
    """Питомец получает заботу за выполненную работу. Сначала применяем decay."""
    apply_decay(pet)
    if milestone:
        pet.hunger = _clamp(pet.hunger + FEED_ON_MILESTONE)
        pet.mood = _clamp(pet.mood + MOOD_ON_MILESTONE)
        pet.energy = _clamp(pet.energy + ENERGY_ON_TASK)
    else:
        feed = FEED_ON_PERSONAL_TASK if scope == "PERSONAL" else FEED_ON_TEAM_TASK
        pet.hunger = _clamp(pet.hunger + feed)
        pet.energy = _clamp(pet.energy + ENERGY_ON_TASK)
        pet.mood = _clamp(pet.mood + MOOD_ON_TASK)


def pet_state(pet: Pet) -> str:
    """Текстовое состояние для UI/реакций."""
    if pet.energy <= 15:
        return "sleepy"      # без сил
    if pet.hunger <= 15:
        return "hungry"      # голодный
    if pet.mood <= 25:
        return "sad"         # грустит
    if pet.hunger >= 70 and pet.mood >= 70 and pet.energy >= 60:
        return "happy"       # доволен
    return "ok"


def state_label(state: str) -> str:
    return {
        "sleepy": "без сил — нужен отдых",
        "hungry": "проголодался — закрой задачу",
        "sad": "загрустил — давно не было работы",
        "happy": "доволен и сыт!",
        "ok": "в порядке",
    }.get(state, "в порядке")
