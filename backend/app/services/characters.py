"""Playable character catalog for pet appearance.

IDs are stored in `pets.species` for compatibility with the earlier pet model.
Owned extra characters are stored in `pets.inventory` as regular item ids.
"""

STARTER_CHARACTER_COUNT = 5
CHARACTER_UNLOCK_LEVEL = 5
CHARACTER_PRICE = 120

def _character(
    character_id: str,
    name: str,
    file: str,
    frame_width: int,
    frame_height: int,
    frames: int,
) -> dict:
    return {
        "id": character_id,
        "name": name,
        "file": file,
        "frame_width": frame_width,
        "frame_height": frame_height,
        "frames": frames,
    }


CHARACTERS: list[dict] = [
    _character("char_agent_mike", "Agent Mike", "agent_mike.png", 32, 32, 2),
    _character("char_martian_red", "Martian Red", "martian_red.png", 32, 32, 2),
    _character("char_robot_walky", "Robot Walky", "robot_walky.png", 32, 32, 2),
    _character("char_orchid_owl", "Orchid Owl", "orchid_owl.png", 32, 32, 2),
    _character("char_mr_circuit", "Mr. Circuit", "mr_circuit.png", 32, 32, 2),
    _character("char_penguin", "Penguin", "penguin.png", 16, 16, 5),
    _character("char_mr_mochi", "Mr. Mochi", "mr_mochi.png", 32, 32, 2),
    _character("char_twiggy", "Twiggy", "twiggy.png", 32, 32, 5),
    _character("char_fairy", "Fairy", "fairy.png", 32, 32, 4),
    _character("char_skeleton", "Skeleton", "skeleton.png", 32, 32, 9),
    _character("char_orange", "Orange", "orange.png", 32, 32, 4),
    _character("char_gloppy_slime", "Gloppy Slime", "gloppy_slime.png", 16, 16, 2),
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
            "data": {
                "file": c["file"],
                "frame_width": c["frame_width"],
                "frame_height": c["frame_height"],
                "frames": c["frames"],
            },
        }
        for c in CHARACTERS
    ]
