"""Магазин и кейсы для питомца.

Каталог — статичная константа в коде (не таблица БД): набор предметов
редко меняется, поэтому незачем нагружать базу. У питомца есть `coins`
и `inventory` (список id предметов) — этого достаточно.
"""
from __future__ import annotations

import secrets

# Редкость влияет на цену и шанс выпадения из кейса.
RARITY_WEIGHTS = {
    "common": 60,
    "rare": 30,
    "epic": 9,
    "legendary": 1,
}

# Каждый предмет: id, название, тип, редкость, цена (для прямой покупки), data.
#  - body  : цвет тела питомца
#  - accent: цвет акцента (рот/детали)
#  - hat    : косметическая «шапка» (эмодзи поверх питомца)
#  - bg     : фон экрана питомца
SHOP_ITEMS: list[dict] = [
    # ── цвета тела ──
    {"id": "body_mint",   "name": "Мятный",     "type": "body", "rarity": "common", "price": 30,  "data": "#9dbf9b"},
    {"id": "body_sky",    "name": "Небесный",   "type": "body", "rarity": "common", "price": 30,  "data": "#a8c4d4"},
    {"id": "body_rose",   "name": "Розовый",    "type": "body", "rarity": "rare",   "price": 60,  "data": "#c9a5ba"},
    {"id": "body_lav",    "name": "Лавандовый", "type": "body", "rarity": "rare",   "price": 60,  "data": "#b5acce"},
    {"id": "body_gold",   "name": "Золотой",    "type": "body", "rarity": "epic",   "price": 150, "data": "#e8c14a"},
    {"id": "body_aurora", "name": "Аврора",     "type": "body", "rarity": "legendary", "price": 400, "data": "#7af0d0"},
    # ── шапки (эмодзи) ──
    {"id": "hat_crown",   "name": "Корона",     "type": "hat", "rarity": "legendary", "price": 350, "data": "👑"},
    {"id": "hat_party",   "name": "Колпак",     "type": "hat", "rarity": "common", "price": 25,  "data": "🎉"},
    {"id": "hat_grad",    "name": "Выпускник",  "type": "hat", "rarity": "rare",   "price": 80,  "data": "🎓"},
    {"id": "hat_flower",  "name": "Цветок",     "type": "hat", "rarity": "common", "price": 25,  "data": "🌸"},
    {"id": "hat_star",    "name": "Звезда",     "type": "hat", "rarity": "epic",   "price": 160, "data": "⭐"},
    # ── фоны ──
    {"id": "bg_space",    "name": "Космос",     "type": "bg", "rarity": "epic",   "price": 140, "data": "#1b1740"},
    {"id": "bg_forest",   "name": "Лес",        "type": "bg", "rarity": "rare",   "price": 70,  "data": "#1d3a24"},
    {"id": "bg_sunset",   "name": "Закат",      "type": "bg", "rarity": "rare",   "price": 70,  "data": "#5a2f3a"},
]

ITEMS_BY_ID = {it["id"]: it for it in SHOP_ITEMS}

# Кейс: стоит фиксированно, выдаёт случайный предмет с учётом редкости.
CASE_PRICE = 50


def get_item(item_id: str) -> dict | None:
    return ITEMS_BY_ID.get(item_id)


def roll_case() -> dict:
    """Выбрать случайный предмет из каталога по весам редкости."""
    # формируем взвешенный пул один раз на вызов (каталог маленький — дёшево)
    pool: list[dict] = []
    for it in SHOP_ITEMS:
        pool.extend([it] * RARITY_WEIGHTS.get(it["rarity"], 1))
    return secrets.choice(pool)
