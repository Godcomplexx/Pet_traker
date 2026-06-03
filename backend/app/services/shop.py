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
    {"id": "body_peach",  "name": "Персик",     "type": "body", "rarity": "common", "price": 35,  "data": "#e6ad8f"},
    {"id": "body_ice",    "name": "Ледяной",    "type": "body", "rarity": "rare",   "price": 85,  "data": "#9fd8e6"},
    {"id": "body_plum",   "name": "Сливовый",   "type": "body", "rarity": "epic",   "price": 170, "data": "#8d6aa0"},
    {"id": "body_neon",   "name": "Неон",       "type": "body", "rarity": "legendary", "price": 450, "data": "#8cff6a"},
    # ── акценты ──
    {"id": "accent_leaf",  "name": "Лист",      "type": "accent", "rarity": "common", "price": 20,  "data": "#4d7c45"},
    {"id": "accent_berry", "name": "Ягода",     "type": "accent", "rarity": "common", "price": 20,  "data": "#8f3f5f"},
    {"id": "accent_ocean", "name": "Океан",     "type": "accent", "rarity": "rare",   "price": 55,  "data": "#3c7da8"},
    {"id": "accent_lava",  "name": "Лава",      "type": "accent", "rarity": "epic",   "price": 120, "data": "#b34b2e"},
    {"id": "accent_void",  "name": "Войд",      "type": "accent", "rarity": "legendary", "price": 280, "data": "#43224e"},
    # ── шапки (эмодзи) ──
    {"id": "hat_crown",   "name": "Корона",     "type": "hat", "rarity": "legendary", "price": 350, "data": "👑"},
    {"id": "hat_party",   "name": "Колпак",     "type": "hat", "rarity": "common", "price": 25,  "data": "🎉"},
    {"id": "hat_grad",    "name": "Выпускник",  "type": "hat", "rarity": "rare",   "price": 80,  "data": "🎓"},
    {"id": "hat_flower",  "name": "Цветок",     "type": "hat", "rarity": "common", "price": 25,  "data": "🌸"},
    {"id": "hat_star",    "name": "Звезда",     "type": "hat", "rarity": "epic",   "price": 160, "data": "⭐"},
    {"id": "hat_goggles", "name": "Очки",       "type": "hat", "rarity": "rare",   "price": 90,  "data": "😎"},
    {"id": "hat_lab",     "name": "Лаборатория", "type": "hat", "rarity": "epic",   "price": 180, "data": "🔬"},
    {"id": "hat_moon",    "name": "Луна",       "type": "hat", "rarity": "rare",   "price": 95,  "data": "🌙"},
    {"id": "hat_ribbon",  "name": "Бант",       "type": "hat", "rarity": "common", "price": 35,  "data": "🎀"},
    {"id": "hat_fire",    "name": "Огонь",      "type": "hat", "rarity": "epic",   "price": 190, "data": "🔥"},
    {"id": "hat_gem",     "name": "Кристалл",   "type": "hat", "rarity": "legendary", "price": 420, "data": "💎"},
    # ── фоны ──
    {"id": "bg_space",    "name": "Космос",     "type": "bg", "rarity": "epic",   "price": 140, "data": "#1b1740"},
    {"id": "bg_forest",   "name": "Лес",        "type": "bg", "rarity": "rare",   "price": 70,  "data": "#1d3a24"},
    {"id": "bg_sunset",   "name": "Закат",      "type": "bg", "rarity": "rare",   "price": 70,  "data": "#5a2f3a"},
    {"id": "bg_lab",      "name": "Лаборатория", "type": "bg", "rarity": "common", "price": 45,  "data": "#dce6df"},
    {"id": "bg_ocean",    "name": "Океан",      "type": "bg", "rarity": "rare",   "price": 75,  "data": "#244b66"},
    {"id": "bg_candy",    "name": "Конфета",    "type": "bg", "rarity": "epic",   "price": 150, "data": "#6f3d61"},
    {"id": "bg_gold",     "name": "Сокровище",  "type": "bg", "rarity": "legendary", "price": 360, "data": "#6b4b16"},
    # ── еда (расходуется при кормлении питомца) ──
    {"id": "food_banana",  "name": "Банан",      "type": "food", "rarity": "common", "price": 12, "data": {"icon": "food_banana", "hunger": 10, "mood": 1, "energy": 0}},
    {"id": "food_berry",   "name": "Ягоды",      "type": "food", "rarity": "common", "price": 10, "data": {"icon": "food_berry", "hunger": 8, "mood": 3, "energy": 0}},
    {"id": "food_carrot",  "name": "Морковь",    "type": "food", "rarity": "common", "price": 14, "data": {"icon": "food_carrot", "hunger": 12, "mood": 1, "energy": 0}},
    {"id": "food_milk",    "name": "Молоко",     "type": "food", "rarity": "rare", "price": 20, "data": {"icon": "food_milk", "hunger": 14, "mood": 1, "energy": 4}},
    {"id": "food_fish",    "name": "Рыба",       "type": "food", "rarity": "rare", "price": 24, "data": {"icon": "food_fish", "hunger": 20, "mood": 1, "energy": 2}},
    {"id": "food_rice",    "name": "Рис",        "type": "food", "rarity": "rare", "price": 25, "data": {"icon": "food_rice", "hunger": 18, "mood": 2, "energy": 0}},
    {"id": "food_cupcake", "name": "Кекс",       "type": "food", "rarity": "epic", "price": 34, "data": {"icon": "food_cupcake", "hunger": 16, "mood": 8, "energy": 0}},
    {"id": "food_ramen",   "name": "Рамен",      "type": "food", "rarity": "epic", "price": 45, "data": {"icon": "food_ramen", "hunger": 28, "mood": 4, "energy": 2}},
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
        if it["type"] == "food":
            continue
        pool.extend([it] * RARITY_WEIGHTS.get(it["rarity"], 1))
    return secrets.choice(pool)
