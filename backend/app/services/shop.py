"""Магазин и кейсы для питомца.

Каталог — статичная константа в коде (не таблица БД): набор предметов
редко меняется, поэтому незачем нагружать базу. У питомца есть `coins`
и `inventory` (список id предметов) — этого достаточно.
"""
from __future__ import annotations

import secrets

from app.services.characters import character_shop_items

CASE_EXCLUDED_TYPES = {"food", "body", "accent", "species", "character"}

# Редкость влияет на цену и шанс выпадения из кейса.
RARITY_WEIGHTS = {
    "common": 60,
    "rare": 30,
    "epic": 9,
    "legendary": 1,
}

# Каждый предмет: id, название, тип, редкость, цена (для прямой покупки), data.
#  - species/character: витрина персонажей; покупка отключена, выдача будет через отдельную рулетку
#  - hat    : косметическая «шапка» (PNG поверх питомца)
#  - bg     : фон экрана питомца
SHOP_ITEMS: list[dict] = [
    # ── шапки (PNG из assets/Small Size) ──
    {"id": "hat_01", "name": "Шапка 01", "type": "hat", "rarity": "common", "price": 35, "data": "hat_01.png"},
    {"id": "hat_02", "name": "Шапка 02", "type": "hat", "rarity": "common", "price": 35, "data": "hat_02.png"},
    {"id": "hat_03", "name": "Шапка 03", "type": "hat", "rarity": "common", "price": 35, "data": "hat_03.png"},
    {"id": "hat_04", "name": "Шапка 04", "type": "hat", "rarity": "common", "price": 35, "data": "hat_04.png"},
    {"id": "hat_05", "name": "Шапка 05", "type": "hat", "rarity": "common", "price": 35, "data": "hat_05.png"},
    {"id": "hat_06", "name": "Шапка 06", "type": "hat", "rarity": "common", "price": 45, "data": "hat_06.png"},
    {"id": "hat_07", "name": "Шапка 07", "type": "hat", "rarity": "common", "price": 45, "data": "hat_07.png"},
    {"id": "hat_08", "name": "Шапка 08", "type": "hat", "rarity": "common", "price": 45, "data": "hat_08.png"},
    {"id": "hat_09", "name": "Шапка 09", "type": "hat", "rarity": "common", "price": 45, "data": "hat_09.png"},
    {"id": "hat_10", "name": "Шапка 10", "type": "hat", "rarity": "common", "price": 45, "data": "hat_10.png"},
    {"id": "hat_11", "name": "Шапка 11", "type": "hat", "rarity": "rare", "price": 80, "data": "hat_11.png"},
    {"id": "hat_12", "name": "Шапка 12", "type": "hat", "rarity": "rare", "price": 80, "data": "hat_12.png"},
    {"id": "hat_13", "name": "Шапка 13", "type": "hat", "rarity": "rare", "price": 90, "data": "hat_13.png"},
    {"id": "hat_14", "name": "Шапка 14", "type": "hat", "rarity": "rare", "price": 90, "data": "hat_14.png"},
    {"id": "hat_15", "name": "Шапка 15", "type": "hat", "rarity": "rare", "price": 95, "data": "hat_15.png"},
    {"id": "hat_16", "name": "Шапка 16", "type": "hat", "rarity": "rare", "price": 95, "data": "hat_16.png"},
    {"id": "hat_17", "name": "Шапка 17", "type": "hat", "rarity": "rare", "price": 100, "data": "hat_17.png"},
    {"id": "hat_18", "name": "Шапка 18", "type": "hat", "rarity": "rare", "price": 100, "data": "hat_18.png"},
    {"id": "hat_19", "name": "Шапка 19", "type": "hat", "rarity": "epic", "price": 160, "data": "hat_19.png"},
    {"id": "hat_20", "name": "Шапка 20", "type": "hat", "rarity": "epic", "price": 160, "data": "hat_20.png"},
    {"id": "hat_21", "name": "Шапка 21", "type": "hat", "rarity": "epic", "price": 180, "data": "hat_21.png"},
    {"id": "hat_22", "name": "Шапка 22", "type": "hat", "rarity": "epic", "price": 180, "data": "hat_22.png"},
    {"id": "hat_23", "name": "Шапка 23", "type": "hat", "rarity": "epic", "price": 190, "data": "hat_23.png"},
    {"id": "hat_24", "name": "Шапка 24", "type": "hat", "rarity": "legendary", "price": 350, "data": "hat_24.png"},
    {"id": "hat_25", "name": "Шапка 25", "type": "hat", "rarity": "legendary", "price": 420, "data": "hat_25.png"},
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
] + character_shop_items()

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
        if it["type"] in CASE_EXCLUDED_TYPES:
            continue
        pool.extend([it] * RARITY_WEIGHTS.get(it["rarity"], 1))
    return secrets.choice(pool)
