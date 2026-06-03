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
    _character("char_angie", "Angie", "angie.png", 32, 32, 6),
    _character("char_armand", "Armand", "armand.png", 32, 32, 5),
    _character("char_ballooney", "Ballooney", "ballooney.png", 32, 32, 2),
    _character("char_barry_cherry", "Barry Cherry", "barry_cherry.png", 32, 32, 4),
    _character("char_big_red", "Big Red", "big_red.png", 32, 32, 6),
    _character("char_blankey", "Blankey", "blankey.png", 32, 32, 4),
    _character("char_blocky_bub", "Blocky Bub", "blocky_bub.png", 16, 16, 2),
    _character("char_bub", "Bub", "bub.png", 16, 16, 2),
    _character("char_bumpy_the_robot", "Bumpy the Robot", "bumpy_the_robot.png", 16, 16, 4),
    _character("char_bushly", "Bushly", "bushly.png", 16, 16, 3),
    _character("char_chi_chi_the_bird", "Chi Chi the Bird", "chi_chi_the_bird.png", 16, 16, 1),
    _character("char_daikon", "Daikon", "daikon.png", 16, 32, 2),
    _character("char_devo_the_devil", "Devo the Devil", "devo_the_devil.png", 16, 16, 1),
    _character("char_diver_the_fish", "Diver the Fish", "diver_the_fish.png", 16, 16, 4),
    _character("char_fairy", "Fairy", "fairy.png", 32, 32, 4),
    _character("char_geralt", "Geralt", "geralt.png", 32, 32, 2),
    _character("char_gloppy_slime", "Gloppy Slime", "gloppy_slime.png", 16, 16, 2),
    _character("char_grizzly", "Grizzly", "grizzly.png", 48, 32, 1),
    _character("char_gum_bot", "Gum Bot", "gum_bot.png", 32, 32, 4),
    _character("char_hermie", "Hermie", "hermie.png", 32, 32, 2),
    _character("char_jumpy_lumpy", "Jumpy Lumpy", "jumpy_lumpy.png", 32, 32, 2),
    _character("char_lil_wiz", "Lil Wiz", "lil_wiz.png", 32, 32, 5),
    _character("char_martian_red", "Martian Red", "martian_red.png", 32, 32, 2),
    _character("char_moe_scotty", "Moe Scotty", "moe_scotty.png", 32, 32, 4),
    _character("char_mr_chomps", "Mr. Chomps", "mr_chomps.png", 32, 32, 12),
    _character("char_mr_circuit", "Mr. Circuit", "mr_circuit.png", 32, 32, 2),
    _character("char_mr_man", "Mr. Man", "mr_man.png", 16, 16, 4),
    _character("char_mr_mochi", "Mr. Mochi", "mr_mochi.png", 32, 32, 2),
    _character("char_octi", "Octi", "octi.png", 16, 16, 2),
    _character("char_onion_lad", "Onion Lad", "onion_lad.png", 16, 16, 2),
    _character("char_orange", "Orange", "orange.png", 32, 32, 4),
    _character("char_orc", "Orc", "orc.png", 64, 32, 7),
    _character("char_orchid_owl", "Orchid Owl", "orchid_owl.png", 32, 32, 2),
    _character("char_penguin", "Penguin", "penguin.png", 16, 16, 5),
    _character("char_percy", "Percy", "percy.png", 32, 32, 9),
    _character("char_pokey_bub", "Pokey Bub", "pokey_bub.png", 16, 16, 2),
    _character("char_roach", "Roach", "roach.png", 32, 32, 2),
    _character("char_robo_pumpkin", "Robo Pumpkin", "robo_pumpkin.png", 16, 16, 1),
    _character("char_robo_retro", "Robo Retro", "robo_retro.png", 32, 32, 9),
    _character("char_robo_totem", "Robo Totem", "robo_totem.png", 16, 32, 1),
    _character("char_robot_j5", "Robot J5", "robot_j5.png", 32, 32, 5),
    _character("char_robot_walky", "Robot Walky", "robot_walky.png", 32, 32, 2),
    _character("char_rocket_cherry", "Rocket Cherry", "rocket_cherry.png", 16, 32, 2),
    _character("char_rolling_nero", "Rolling Nero", "rolling_nero.png", 16, 16, 6),
    _character("char_skeleton", "Skeleton", "skeleton.png", 32, 32, 9),
    _character("char_snip_snap_crab", "Snip Snap Crab", "snip_snap_crab.png", 32, 32, 1),
    _character("char_spikey_bub", "Spikey Bub", "spikey_bub.png", 16, 16, 2),
    _character("char_squirmy_wormy", "Squirmy Wormy", "squirmy_wormy.png", 32, 32, 3),
    _character("char_toggle", "Toggle", "toggle.png", 32, 32, 5),
    _character("char_twiggy", "Twiggy", "twiggy.png", 32, 32, 5),
    _character("char_vessa", "Vessa", "vessa.png", 32, 32, 10),
    _character("char_wispy_fire", "Wispy Fire", "wispy_fire.png", 32, 32, 21),
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
