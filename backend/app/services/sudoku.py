"""Ежедневная судоку 6×6 (блоки 2×3, цифры 1–6).

Головоломка детерминирована по дате: для каждого дня (UTC) генерируется одна
и та же задача с единственным решением. Это позволяет:
  • не хранить задачи в БД — достаточно даты;
  • проверять ответ на сервере, не доверяя клиенту;
  • показывать всем «головоломку дня».
"""
from __future__ import annotations

import random
from datetime import date

N = 6          # размер поля
BR, BC = 2, 3  # высота/ширина блока (2 строки × 3 столбца)


def _pattern(r: int, c: int) -> int:
    """Базовая корректная раскладка латинских блоков для 6×6."""
    return (BC * (r % BR) + r // BR + c) % N


def _shuffled_solution(seed: int) -> list[list[int]]:
    """Полностью заполненное корректное поле, перемешанное по seed."""
    rnd = random.Random(seed)

    n_row_bands = N // BR   # число полос строк (6/2 = 3)
    n_col_bands = N // BC   # число полос столбцов (6/3 = 2)

    rows_band = list(range(n_row_bands))
    cols_band = list(range(n_col_bands))
    rnd.shuffle(rows_band)
    rnd.shuffle(cols_band)

    # перестановка строк/столбцов внутри полос
    row_in = [list(range(BR)) for _ in range(n_row_bands)]
    col_in = [list(range(BC)) for _ in range(n_col_bands)]
    for g in row_in:
        rnd.shuffle(g)
    for g in col_in:
        rnd.shuffle(g)

    rows = [b * BR + r for b in rows_band for r in row_in[b]]
    cols = [b * BC + c for b in cols_band for c in col_in[b]]

    nums = list(range(1, N + 1))
    rnd.shuffle(nums)  # перестановка значений символов

    return [[nums[_pattern(r, c)] for c in cols] for r in rows]


def _count_solutions(grid: list[list[int]], limit: int = 2) -> int:
    """Подсчёт решений (с ранним выходом при достижении limit)."""
    # найти пустую клетку
    pos = None
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


def _make_puzzle(seed: int) -> tuple[list[list[int]], list[list[int]]]:
    """Вернуть (puzzle, solution): убираем клетки, сохраняя единственность."""
    solution = _shuffled_solution(seed)
    puzzle = [row[:] for row in solution]
    rnd = random.Random(seed ^ 0x5DEECE66)

    cells = [(r, c) for r in range(N) for c in range(N)]
    rnd.shuffle(cells)

    # пытаемся убрать как можно больше клеток, сохраняя единственное решение
    for r, c in cells:
        saved = puzzle[r][c]
        puzzle[r][c] = 0
        grid = [row[:] for row in puzzle]
        if _count_solutions(grid, limit=2) != 1:
            puzzle[r][c] = saved  # вернуть — иначе решений станет несколько
    return puzzle, solution


def _seed_for(day: date) -> int:
    return day.toordinal()


def daily_puzzle(day: date) -> dict:
    """Головоломка дня: задача с дырами + её решение."""
    puzzle, solution = _make_puzzle(_seed_for(day))
    return {
        "date": day.isoformat(),
        "size": N,
        "block_rows": BR,
        "block_cols": BC,
        "puzzle": puzzle,      # 0 = пустая клетка
        "solution": solution,
    }


def check_solution(day: date, attempt: list[list[int]]) -> bool:
    """Сверить присланное поле с решением головоломки дня."""
    if not isinstance(attempt, list) or len(attempt) != N:
        return False
    target = daily_puzzle(day)["solution"]
    for r in range(N):
        row = attempt[r]
        if not isinstance(row, list) or len(row) != N:
            return False
        for c in range(N):
            if row[c] != target[r][c]:
                return False
    return True
