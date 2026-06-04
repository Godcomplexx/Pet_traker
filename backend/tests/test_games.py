"""Ежедневная судоку: генерация, проверка, награда раз в день."""
from datetime import date

from app.services import sudoku
from tests.conftest import auth_headers, register


def test_daily_puzzle_unique_solution_and_deterministic():
    d = date(2026, 6, 3)
    p1 = sudoku.daily_puzzle(d)
    p2 = sudoku.daily_puzzle(d)
    assert p1["puzzle"] == p2["puzzle"]            # детерминирована
    grid = [row[:] for row in p1["puzzle"]]
    assert sudoku._count_solutions(grid, limit=2) == 1  # единственное решение
    assert sudoku.check_solution(d, p1["solution"]) is True


def test_check_rejects_wrong():
    d = date(2026, 6, 3)
    bad = [[1] * 6 for _ in range(6)]
    assert sudoku.check_solution(d, bad) is False


async def test_daily_endpoint(client):
    tokens = await register(client, "sudoku@lab.ru")
    h = auth_headers(tokens)
    r = await client.get("/games/sudoku/daily", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["size"] == 6
    assert body["reward"] == 50
    assert body["solved_today"] is False
    assert len(body["puzzle"]) == 6


async def test_solve_awards_coins_once_per_day(client):
    tokens = await register(client, "solver@lab.ru")
    h = auth_headers(tokens)

    # узнаём решение дня через сервис (как сделал бы корректный игрок)
    daily = await client.get("/games/sudoku/daily", headers=h)
    day = date.fromisoformat(daily.json()["date"])
    solution = sudoku.daily_puzzle(day)["solution"]

    coins_before = (await client.get("/pets/me", headers=h)).json()["coins"]

    first = await client.post("/games/sudoku/solve", json={"solution": solution}, headers=h)
    assert first.status_code == 200, first.text
    fb = first.json()
    assert fb["correct"] is True
    assert fb["coins_awarded"] == 50
    assert fb["coins"] == coins_before + 50

    # второй раз в тот же день — без награды
    second = await client.post("/games/sudoku/solve", json={"solution": solution}, headers=h)
    sb = second.json()
    assert sb["correct"] is True
    assert sb["coins_awarded"] == 0
    assert sb["already_solved"] is True
    assert sb["coins"] == coins_before + 50  # баланс не вырос


async def test_solve_wrong_no_reward(client):
    tokens = await register(client, "wrong@lab.ru")
    h = auth_headers(tokens)
    bad = [[1] * 6 for _ in range(6)]
    r = await client.post("/games/sudoku/solve", json={"solution": bad}, headers=h)
    body = r.json()
    assert body["correct"] is False
    assert body["coins_awarded"] == 0


async def test_memory_daily_endpoint(client):
    tokens = await register(client, "memory@lab.ru")
    h = auth_headers(tokens)
    r = await client.get("/games/memory/daily", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reward"] == 35
    assert body["max_moves"] == 18
    assert body["solved_today"] is False
    assert len(body["cards"]) == 12
    assert len(set(body["cards"])) == 6


async def test_memory_awards_once_per_day(client):
    tokens = await register(client, "memory-solve@lab.ru")
    h = auth_headers(tokens)
    coins_before = (await client.get("/pets/me", headers=h)).json()["coins"]

    first = await client.post(
        "/games/memory/solve",
        json={"moves": 10, "matched_pairs": 6},
        headers=h,
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["correct"] is True
    assert body["coins_awarded"] == 35
    assert body["coins"] == coins_before + 35

    second = await client.post(
        "/games/memory/solve",
        json={"moves": 10, "matched_pairs": 6},
        headers=h,
    )
    body = second.json()
    assert body["correct"] is True
    assert body["coins_awarded"] == 0
    assert body["already_solved"] is True


async def test_memory_wrong_no_reward(client):
    tokens = await register(client, "memory-wrong@lab.ru")
    h = auth_headers(tokens)
    r = await client.post(
        "/games/memory/solve",
        json={"moves": 18, "matched_pairs": 5},
        headers=h,
    )
    body = r.json()
    assert body["correct"] is False
    assert body["coins_awarded"] == 0
