"""Магазин и кейсы для питомца.

Каталог — статичная константа в коде (не таблица БД): набор предметов
редко меняется, поэтому незачем нагружать базу. У питомца есть `coins`
и `inventory` (список id предметов) — этого достаточно.
"""
from __future__ import annotations

import secrets

from app.services.catalog_assets import accessory_shop_items, decor_item_shop_items, food_asset_shop_items
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
    # ── декор комнаты ──
    {"id": "decor_plant_sprout", "name": "Росток", "type": "decor", "rarity": "common", "price": 45, "data": {"file": "plant_sprout.png", "slot": "floor-left"}},
    {"id": "decor_plant_leafy", "name": "Листья", "type": "decor", "rarity": "common", "price": 55, "data": {"file": "plant_leafy.png", "slot": "floor-right"}},
    {"id": "decor_flower_pot", "name": "Цветок", "type": "decor", "rarity": "common", "price": 55, "data": {"file": "flower_pot.png", "slot": "floor-right"}},
    {"id": "decor_plant_bloom_red", "name": "Красный цветок", "type": "decor", "rarity": "common", "price": 60, "data": {"file": "plant_bloom_red.png", "slot": "floor-left"}},
    {"id": "decor_plant_bloom_orchid", "name": "Орхидея", "type": "decor", "rarity": "common", "price": 60, "data": {"file": "plant_bloom_orchid.png", "slot": "floor-right"}},
    {"id": "decor_plant_bloom_yellow", "name": "Желтый цветок", "type": "decor", "rarity": "common", "price": 60, "data": {"file": "plant_bloom_yellow.png", "slot": "floor-left"}},
    {"id": "decor_plant_bloom_small", "name": "Маленький цветок", "type": "decor", "rarity": "common", "price": 50, "data": {"file": "plant_bloom_small.png", "slot": "floor-right"}},
    {"id": "decor_plant_fern", "name": "Папоротник", "type": "decor", "rarity": "rare", "price": 75, "data": {"file": "plant_fern.png", "slot": "shelf-left"}},
    {"id": "decor_plant_round", "name": "Круглое растение", "type": "decor", "rarity": "rare", "price": 75, "data": {"file": "plant_round.png", "slot": "shelf-right"}},
    {"id": "decor_plant_orange", "name": "Оранжевый цветок", "type": "decor", "rarity": "rare", "price": 85, "data": {"file": "plant_orange.png", "slot": "shelf-left"}},
    {"id": "decor_plant_leaf_pot", "name": "Лиственный горшок", "type": "decor", "rarity": "rare", "price": 85, "data": {"file": "plant_leaf_pot.png", "slot": "shelf-right"}},
    {"id": "decor_plant_tall", "name": "Высокий цветок", "type": "decor", "rarity": "rare", "price": 95, "data": {"file": "plant_tall.png", "slot": "shelf-right"}},
    {"id": "decor_plant_single_leaf", "name": "Листок", "type": "decor", "rarity": "rare", "price": 80, "data": {"file": "plant_single_leaf.png", "slot": "shelf-left"}},
    {"id": "decor_plant_yellow_pot", "name": "Солнечный цветок", "type": "decor", "rarity": "rare", "price": 90, "data": {"file": "plant_yellow_pot.png", "slot": "shelf-right"}},
    {"id": "decor_floor_lamp", "name": "Торшер", "type": "decor", "rarity": "rare", "price": 95, "data": {"file": "decor_floor_lamp.png", "slot": "floor-right", "kind": "light"}},
    {"id": "decor_wall_light", "name": "Настенный свет", "type": "decor", "rarity": "epic", "price": 130, "data": {"file": "decor_wall_light.png", "slot": "shelf-left", "kind": "light"}},
    # ── еда (расходуется при кормлении питомца) ──
    {"id": "food_banana",  "name": "Банан",      "type": "food", "rarity": "common", "price": 12, "data": {"icon": "food_banana", "hunger": 12, "mood": 1, "energy": 0}},
    {"id": "food_berry",   "name": "Ягоды",      "type": "food", "rarity": "common", "price": 10, "data": {"icon": "food_berry", "hunger": 12, "mood": 3, "energy": 0}},
    {"id": "food_carrot",  "name": "Морковь",    "type": "food", "rarity": "common", "price": 14, "data": {"icon": "food_carrot", "hunger": 12, "mood": 1, "energy": 0}},
    {"id": "food_milk",    "name": "Молоко",     "type": "food", "rarity": "rare", "price": 22, "data": {"icon": "food_milk", "hunger": 24, "mood": 1, "energy": 4}},
    {"id": "food_fish",    "name": "Рыба",       "type": "food", "rarity": "rare", "price": 28, "data": {"icon": "food_fish", "hunger": 24, "mood": 1, "energy": 2}},
    {"id": "food_rice",    "name": "Рис",        "type": "food", "rarity": "rare", "price": 26, "data": {"icon": "food_rice", "hunger": 24, "mood": 2, "energy": 0}},
    {"id": "food_cupcake", "name": "Кекс",       "type": "food", "rarity": "epic", "price": 40, "data": {"icon": "food_cupcake", "hunger": 38, "mood": 8, "energy": 0}},
    {"id": "food_ramen",   "name": "Рамен",      "type": "food", "rarity": "epic", "price": 48, "data": {"icon": "food_ramen", "hunger": 38, "mood": 4, "energy": 2}},
] + food_asset_shop_items() + decor_item_shop_items() + accessory_shop_items() + character_shop_items()

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
