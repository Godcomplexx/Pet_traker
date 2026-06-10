"""Generated shop entries for imported pixel assets."""

ROOM_DECOR_FILES = (
    "balloon.png",
    "banana.png",
    "batter.png",
    "battery.png",
    "bean.png",
    "beast_blood.png",
    "beast_bone.png",
    "beast_hide.png",
    "beast_meat.png",
    "belt.png",
    "bendystraw.png",
    "berry.png",
    "bird_house.png",
    "blanket.png",
    "bug.png",
    "bug_zapper.png",
    "butter.png",
    "butterfly_net.png",
    "carrot.png",
    "chocolate_bar.png",
    "chopsticks.png",
    "cinnamon.png",
    "clam.png",
    "clay.png",
    "cloth.png",
    "coconut.png",
    "coffee_beans.png",
    "copper.png",
    "corn.png",
    "cotton.png",
    "crab.png",
    "cupcake.png",
    "diamond.png",
    "dough.png",
    "egg.png",
    "excess_fur.png",
    "fish.png",
    "flour.png",
    "flower.png",
    "fruit_salad.png",
    "glass.png",
    "glue.png",
    "gold.png",
    "grass.png",
    "hammer.png",
    "handpainted_mug.png",
    "hard_candy.png",
    "herbs.png",
    "ice_cream.png",
    "integrated_circuit.png",
    "iron.png",
    "junk_parts.png",
    "knife.png",
    "lace.png",
    "lemon.png",
    "magical_powder.png",
    "markers.png",
    "melon.png",
    "metal.png",
    "milk.png",
    "mirror.png",
    "motivational_poster.png",
    "nails.png",
    "nail_polish.png",
    "nut.png",
    "oats.png",
    "octopus.png",
    "paint.png",
    "paper.png",
    "photo_frame.png",
    "picnic_basket.png",
    "pie.png",
    "plastic.png",
    "potato.png",
    "ramen.png",
    "rice_bowl.png",
    "rock.png",
    "rope.png",
    "salt.png",
    "scissors.png",
    "seashell.png",
    "seed.png",
    "shiny_stone.png",
    "silk.png",
    "silver.png",
    "steel.png",
    "stew.png",
    "stickers.png",
    "string.png",
    "sugar.png",
    "sugarcane.png",
    "sunscreen.png",
    "teabag.png",
    "tropical_juice.png",
    "umbrella.png",
    "useless_poo.png",
    "vanilla.png",
    "water.png",
    "wheat.png",
    "wood.png",
)

FOOD_ASSET_RARITIES = {
    "banana.png": "common",
    "bean.png": "common",
    "berry.png": "common",
    "carrot.png": "common",
    "corn.png": "common",
    "egg.png": "common",
    "herbs.png": "common",
    "lemon.png": "common",
    "nut.png": "common",
    "oats.png": "common",
    "potato.png": "common",
    "seed.png": "common",
    "sugar.png": "common",
    "water.png": "common",
    "wheat.png": "common",
    "batter.png": "rare",
    "beast_meat.png": "rare",
    "butter.png": "rare",
    "cinnamon.png": "rare",
    "clam.png": "rare",
    "coconut.png": "rare",
    "coffee_beans.png": "rare",
    "crab.png": "rare",
    "dough.png": "rare",
    "fish.png": "rare",
    "flour.png": "rare",
    "melon.png": "rare",
    "milk.png": "rare",
    "octopus.png": "rare",
    "rice_bowl.png": "rare",
    "salt.png": "rare",
    "sugarcane.png": "rare",
    "teabag.png": "rare",
    "vanilla.png": "rare",
    "chocolate_bar.png": "epic",
    "cupcake.png": "epic",
    "fruit_salad.png": "epic",
    "hard_candy.png": "epic",
    "ice_cream.png": "epic",
    "pie.png": "epic",
    "ramen.png": "epic",
    "stew.png": "epic",
    "tropical_juice.png": "epic",
}

FOOD_HUNGER_BY_RARITY = {
    "common": 12,
    "rare": 24,
    "epic": 38,
    "legendary": 55,
}

FOOD_PRICE_BY_RARITY = {
    "common": 14,
    "rare": 28,
    "epic": 48,
    "legendary": 80,
}

ACCESSORY_ITEMS = (
    ("accessory_bunan_black", "Bunan Black", "bunan_black_64.png", 0.5, 0.46),
    ("accessory_maru_black", "Maru Black", "maru_black_64.png", 0.46, 0.45),
    ("accessory_tsuyome_black", "Tsuyome Black", "tsuyome_black_64.png", 0.52, 0.46),
    ("accessory_yasashime_black", "Yasashime Black", "yasashime_black_64.png", 0.5, 0.46),
)


def _title_from_file(file_name: str) -> str:
    return file_name.removesuffix(".png").replace("_", " ").title()


def decor_item_shop_items() -> list[dict]:
    return [
        {
            "id": f"decor_item_{file_name.removesuffix('.png')}",
            "name": _title_from_file(file_name),
            "type": "decor",
            "rarity": "common",
            "price": 25,
            "data": {"file": f"items/{file_name}"},
        }
        for file_name in ROOM_DECOR_FILES
        if file_name not in FOOD_ASSET_RARITIES
    ]


def food_asset_shop_items() -> list[dict]:
    return [
        {
            "id": f"food_item_{file_name.removesuffix('.png')}",
            "name": _title_from_file(file_name),
            "type": "food",
            "rarity": rarity,
            "price": FOOD_PRICE_BY_RARITY[rarity],
            "data": {
                "file": f"items/{file_name}",
                "hunger": FOOD_HUNGER_BY_RARITY[rarity],
                "mood": 1 if rarity == "common" else 2 if rarity == "rare" else 4,
                "energy": 0 if rarity == "common" else 1 if rarity == "rare" else 2,
            },
        }
        for file_name, rarity in FOOD_ASSET_RARITIES.items()
    ]


def accessory_shop_items() -> list[dict]:
    return [
        {
            "id": item_id,
            "name": name,
            "type": "accessory",
            "rarity": "rare",
            "price": 70,
            "data": {
                "file": file_name,
                "anchor_x": 0.5,
                "anchor_y": anchor_y,
                "scale": scale,
            },
        }
        for item_id, name, file_name, scale, anchor_y in ACCESSORY_ITEMS
    ]
