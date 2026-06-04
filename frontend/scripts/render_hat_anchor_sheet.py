from __future__ import annotations

import math
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "app.js"
CHAR_DIR = ROOT / "assets" / "characters"
HAT_PATH = ROOT / "assets" / "hats" / "hat_16.png"
OUT_PATH = ROOT / "screenshots" / "hat-anchor-current.png"
OVERRIDES_PATH = ROOT / "hat-placement-overrides.json"
HAT_ID = "hat_16"

COLS = 5
CELL_W = 132
CELL_H = 126
BG = (240, 244, 238, 255)
GRID = (185, 196, 180, 255)
TEXT = (78, 84, 78, 255)

HAT_FIT = {"bottom": 11, "center": 0.5}


def read_catalog() -> list[dict[str, object]]:
    text = APP_JS.read_text(encoding="utf-8")
    match = re.search(r"const CHARACTER_CATALOG = \[(.*?)\];", text, re.S)
    if not match:
        raise RuntimeError("CHARACTER_CATALOG was not found in app.js")

    catalog: list[dict[str, object]] = []
    for raw in re.finditer(r"\{([^{}]+)\}", match.group(1)):
        item: dict[str, object] = {}
        for key, value, quoted in re.findall(
            r"(\w+):\s*(?:'([^']*)'|(true|false|-?\d+(?:\.\d+)?))",
            raw.group(1),
        ):
            token = value or quoted
            if token == "true":
                item[key] = True
            elif token == "false":
                item[key] = False
            else:
                try:
                    item[key] = float(token) if "." in token else int(token)
                except ValueError:
                    item[key] = token
        if item.get("file"):
            catalog.append(item)
    return catalog


def read_overrides() -> dict[str, dict[str, dict[str, object]]]:
    if not OVERRIDES_PATH.exists():
        return {}
    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


def with_hat_override(
    character: dict[str, object],
    overrides: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object]:
    override = overrides.get(str(character.get("id")), {}).get(HAT_ID)
    if not override:
        return character
    merged = dict(character)
    for key in ("opaqueTop", "opaqueCenter", "hatScale", "hatOffsetX", "hatOffsetY", "hatFlip"):
        if key in override:
            merged[key] = override[key]
    return merged


def load_font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def fmt_num(value: object) -> str:
    number = float(value or 0)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}".rstrip("0").rstrip(".")


def first_frame(character: dict[str, object]) -> Image.Image:
    path = CHAR_DIR / str(character["file"])
    sprite = Image.open(path).convert("RGBA")
    frame_w = int(character.get("frameWidth") or 32)
    frame_h = int(character.get("frameHeight") or 32)
    return sprite.crop((0, 0, frame_w, frame_h))


def draw_pixel_art(
    canvas: Image.Image,
    image: Image.Image,
    center_x: float,
    top_y: float,
    width: int,
    height: int,
) -> None:
    if width <= 0 or height <= 0:
        return
    scaled = image.resize((width, height), Image.Resampling.NEAREST)
    x = int(round(center_x - width / 2))
    y = int(round(top_y))
    canvas.alpha_composite(scaled, (x, y))


def draw_cell(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    character: dict[str, object],
    index: int,
    name_font: ImageFont.ImageFont,
    meta_font: ImageFont.ImageFont,
) -> None:
    col = index % COLS
    row = index // COLS
    x0 = col * CELL_W
    y0 = row * CELL_H

    frame = first_frame(character)
    frame_w = int(character.get("frameWidth") or frame.width)
    frame_h = int(character.get("frameHeight") or frame.height)
    sprite_scale = 64 / frame_h
    sprite_w = int(round(frame_w * sprite_scale))
    sprite_h = int(round(frame_h * sprite_scale))
    sprite_top = y0 + 34 + (64 - sprite_h) / 2
    sprite_cx = x0 + CELL_W / 2

    draw_pixel_art(canvas, frame, sprite_cx, sprite_top, sprite_w, sprite_h)

    hat = Image.open(HAT_PATH).convert("RGBA")
    fitted = 64 * float(character.get("hatScale") or 1)
    box_h = fitted * 0.72
    head_top = sprite_top + float(character.get("opaqueTop") or 0) * sprite_scale
    head_x = (
        sprite_cx
        + (float(character.get("opaqueCenter") or frame_w / 2) - frame_w / 2) * sprite_scale
        + float(character.get("hatOffsetX") or 0) * sprite_scale
    )
    head_overlap = min(7, 2.5 * sprite_scale)
    hat_top = (
        head_top
        - box_h
        + head_overlap
        + float(character.get("hatOffsetY") or 0) * sprite_scale
    )
    flip = -1 if character.get("hatFlip") else 1
    shift_x = (-HAT_FIT["center"] / 30) * fitted * flip
    shift_y = (HAT_FIT["bottom"] / 30) * fitted
    hat_img = hat.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip == -1 else hat
    hat_w = int(round(fitted))
    hat_h = int(round(fitted))
    hat_left = head_x - fitted / 2 + shift_x
    hat_img_top = hat_top + box_h - fitted + shift_y
    hat_scaled = hat_img.resize((hat_w, hat_h), Image.Resampling.NEAREST)
    canvas.alpha_composite(hat_scaled, (int(round(hat_left)), int(round(hat_img_top))))

    label_y = y0 + CELL_H - 23
    name = str(character.get("file", "")).removesuffix(".png")
    draw.text((x0 + 4, label_y), name, fill=TEXT, font=name_font)
    flip_label = "Y" if character.get("hatFlip") else "N"
    meta = (
        f"top {fmt_num(character.get('opaqueTop'))} "
        f"cx {fmt_num(character.get('opaqueCenter'))} "
        f"flip {flip_label}"
    )
    if character.get("hatOffsetX"):
        meta += f" x {fmt_num(character.get('hatOffsetX'))}"
    if character.get("hatOffsetY"):
        meta += f" y {fmt_num(character.get('hatOffsetY'))}"
    draw.text((x0 + 4, label_y + 12), meta, fill=TEXT, font=meta_font)


def main() -> None:
    catalog = read_catalog()
    overrides = read_overrides()
    rows = math.ceil(len(catalog) / COLS)
    canvas = Image.new("RGBA", (COLS * CELL_W, rows * CELL_H), BG)
    draw = ImageDraw.Draw(canvas)

    for x in range(0, canvas.width + 1, CELL_W):
        draw.line((x, 0, x, canvas.height), fill=GRID, width=1)
    for y in range(0, canvas.height + 1, CELL_H):
        draw.line((0, y, canvas.width, y), fill=GRID, width=1)

    name_font = load_font(11)
    meta_font = load_font(10)
    for idx, character in enumerate(catalog):
        draw_cell(canvas, draw, with_hat_override(character, overrides), idx, name_font, meta_font)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
