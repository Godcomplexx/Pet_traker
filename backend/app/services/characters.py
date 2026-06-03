"""Playable character catalog for pet appearance.

IDs are stored in `pets.species` for compatibility with the earlier pet model.
Owned extra characters are stored in `pets.inventory` as regular item ids.
"""

STARTER_CHARACTER_COUNT = 5
CHARACTER_UNLOCK_LEVEL = 5
CHARACTER_PRICE = 120

CHARACTERS: list[dict] = [
    {"id": "char_agent_mike", "name": "Agent Mike", "file": "agent_mike.png"},
    {"id": "char_martian_red", "name": "Martian Red", "file": "martian_red.png"},
    {"id": "char_robot_walky", "name": "Robot Walky", "file": "robot_walky.png"},
    {"id": "char_orchid_owl", "name": "Orchid Owl", "file": "orchid_owl.png"},
    {"id": "char_mr_circuit", "name": "Mr. Circuit", "file": "mr_circuit.png"},
    {"id": "char_penguin", "name": "Penguin", "file": "penguin.png"},
    {"id": "char_mr_mochi", "name": "Mr. Mochi", "file": "mr_mochi.png"},
    {"id": "char_twiggy", "name": "Twiggy", "file": "twiggy.png"},
    {"id": "char_fairy", "name": "Fairy", "file": "fairy.png"},
    {"id": "char_skeleton", "name": "Skeleton", "file": "skeleton.png"},
    {"id": "char_orange", "name": "Orange", "file": "orange.png"},
    {"id": "char_gloppy_slime", "name": "Gloppy Slime", "file": "gloppy_slime.png"},
]

CHARACTERS_BY_ID = {c["id"]: c for c in CHARACTERS}


def get_character(character_id: str) -> dict | None:
    return CHARACTERS_BY_ID.get(character_id)


def character_shop_items() -> list[dict]:
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "type": "character",
            "rarity": "rare",
            "price": CHARACTER_PRICE,
            "min_level": CHARACTER_UNLOCK_LEVEL,
            "data": {"file": c["file"]},
        }
        for c in CHARACTERS
    ]
