"""Daily 6x6 Sudoku service.

The public contract is shared by two API surfaces:
- /games/sudoku/* needs a puzzle payload with metadata and solution checking.
- /pets/me/sudoku* needs the same daily puzzle plus hints/error highlighting.
"""
from __future__ import annotations

import random
from datetime import date

N = 6
BR, BC = 2, 3


def _pattern(r: int, c: int) -> int:
    return (BC * (r % BR) + r // BR + c) % N


def _shuffled_solution(seed: int) -> list[list[int]]:
    rnd = random.Random(seed)

    row_bands = list(range(N // BR))
    col_bands = list(range(N // BC))
    rnd.shuffle(row_bands)
    rnd.shuffle(col_bands)

    row_in = [list(range(BR)) for _ in row_bands]
    col_in = [list(range(BC)) for _ in col_bands]
    for group in row_in:
        rnd.shuffle(group)
    for group in col_in:
        rnd.shuffle(group)

    rows = [band * BR + r for band in row_bands for r in row_in[band]]
    cols = [band * BC + c for band in col_bands for c in col_in[band]]

    nums = list(range(1, N + 1))
    rnd.shuffle(nums)

    return [[nums[_pattern(r, c)] for c in cols] for r in rows]


def _valid(grid: list[list[int]], r: int, c: int, v: int) -> bool:
    for i in range(N):
        if grid[r][i] == v or grid[i][c] == v:
            return False
    br, bc = (r // BR) * BR, (c // BC) * BC
    for i in range(br, br + BR):
        for j in range(bc, bc + BC):
            if grid[i][j] == v:
                return False
    return True


def _count_solutions(grid: list[list[int]], limit: int = 2) -> int:
    pos: tuple[int, int] | None = None
    for r in range(N):
        for c in range(N):
            if grid[r][c] == 0:
                pos = (r, c)
                break
        if pos:
            break
    if pos is None:
        return 1

    r, c = pos
    count = 0
    for v in range(1, N + 1):
        if _valid(grid, r, c, v):
            grid[r][c] = v
            count += _count_solutions(grid, limit)
            grid[r][c] = 0
            if count >= limit:
                break
    return count


def _make_puzzle(seed: int) -> tuple[list[list[int]], list[list[int]]]:
    solution = _shuffled_solution(seed)
    puzzle = [row[:] for row in solution]
    rnd = random.Random(seed ^ 0x5DEECE66)

    cells = [(r, c) for r in range(N) for c in range(N)]
    rnd.shuffle(cells)
    for r, c in cells:
        saved = puzzle[r][c]
        puzzle[r][c] = 0
        if _count_solutions([row[:] for row in puzzle], limit=2) != 1:
            puzzle[r][c] = saved
    return puzzle, solution


def _seed_for(day: date) -> int:
    return day.toordinal()


def daily_puzzle(day: date) -> dict:
    puzzle, solution = _make_puzzle(_seed_for(day))
    return {
        "date": day.isoformat(),
        "size": N,
        "block_rows": BR,
        "block_cols": BC,
        "puzzle": puzzle,
        "solution": solution,
    }


def daily_solution(day: date) -> list[list[int]]:
    return [row[:] for row in daily_puzzle(day)["solution"]]


def check_solution(day: date, attempt: list[list[int]]) -> bool:
    if not isinstance(attempt, list) or len(attempt) != N:
        return False
    target = daily_solution(day)
    for r in range(N):
        row = attempt[r]
        if not isinstance(row, list) or len(row) != N:
            return False
        for c in range(N):
            if row[c] != target[r][c]:
                return False
    return True


def find_errors(day: date, grid: list[list[int]]) -> list[list[int]]:
    target = daily_solution(day)
    errors: list[list[int]] = []
    for r in range(N):
        row = grid[r] if isinstance(grid, list) and r < len(grid) and isinstance(grid[r], list) else []
        for c in range(N):
            value = row[c] if c < len(row) else 0
            if value and value != target[r][c]:
                errors.append([r, c])
    return errors


def hint_for(day: date, grid: list[list[int]]) -> dict | None:
    target = daily_solution(day)
    for r in range(N):
        row = grid[r] if isinstance(grid, list) and r < len(grid) and isinstance(grid[r], list) else []
        for c in range(N):
            value = row[c] if c < len(row) else 0
            if value != target[r][c]:
                return {"row": r, "col": c, "value": target[r][c]}
    return None
