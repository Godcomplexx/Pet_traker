from __future__ import annotations

import random
from functools import lru_cache

from app.services.gamification import MINESWEEPER_COINS

SIZE = 9
MINE_COUNT = 10
REWARD = MINESWEEPER_COINS
GAME_ID = "minesweeper"


def _neighbors(row: int, col: int) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < SIZE and 0 <= nc < SIZE:
                cells.append((nr, nc))
    return cells


@lru_cache(maxsize=90)
def _mines_cached(day_iso: str) -> tuple[tuple[int, int], ...]:
    rng = random.Random(f"minesweeper:{day_iso}")
    cells = [(row, col) for row in range(SIZE) for col in range(SIZE)]
    return tuple(sorted(rng.sample(cells, MINE_COUNT)))


def mines(day) -> list[list[int]]:
    return [[row, col] for row, col in _mines_cached(day.isoformat())]


def counts(day) -> list[list[int]]:
    mine_set = set(_mines_cached(day.isoformat()))
    grid: list[list[int]] = []
    for row in range(SIZE):
        grid_row: list[int] = []
        for col in range(SIZE):
            grid_row.append(sum(cell in mine_set for cell in _neighbors(row, col)))
        grid.append(grid_row)
    return grid


def daily_board(day) -> dict:
    return {
        "date": day.isoformat(),
        "size": SIZE,
        "mine_count": MINE_COUNT,
        "mines": mines(day),
        "counts": counts(day),
        "reward": REWARD,
    }


def is_solved(day, revealed: list[list[int]]) -> bool:
    mine_set = set(_mines_cached(day.isoformat()))
    revealed_set: set[tuple[int, int]] = set()
    for cell in revealed:
        if not isinstance(cell, list) or len(cell) != 2:
            return False
        row, col = cell
        if not isinstance(row, int) or not isinstance(col, int):
            return False
        if row < 0 or row >= SIZE or col < 0 or col >= SIZE:
            return False
        pos = (row, col)
        if pos in mine_set:
            return False
        revealed_set.add(pos)
    return len(revealed_set) == SIZE * SIZE - MINE_COUNT
