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


async def test_sudoku_solve_records_and_improves_leaderboard_time(client):
    tokens = await register(client, "ranked-solver@lab.ru", name="Ranked Solver")
    h = auth_headers(tokens)
    ws = (await client.post("/workspaces", json={"name": "Lab"}, headers=h)).json()

    daily = await client.get("/games/sudoku/daily", headers=h)
    day = date.fromisoformat(daily.json()["date"])
    solution = sudoku.daily_puzzle(day)["solution"]

    first = await client.post(
        "/games/sudoku/solve",
        json={"solution": solution, "seconds": 180},
        headers=h,
    )
    assert first.status_code == 200, first.text
    assert first.json()["best_seconds"] == 180

    slower = await client.post(
        "/games/sudoku/solve",
        json={"solution": solution, "seconds": 240},
        headers=h,
    )
    assert slower.status_code == 200, slower.text
    assert slower.json()["coins_awarded"] == 0
    assert slower.json()["best_seconds"] == 180

    faster = await client.post(
        "/games/sudoku/solve",
        json={"solution": solution, "seconds": 95},
        headers=h,
    )
    assert faster.status_code == 200, faster.text
    assert faster.json()["best_seconds"] == 95

    board = await client.get(f"/workspaces/{ws['id']}/sudoku/leaderboard", headers=h)
    assert board.status_code == 200, board.text
    rows = board.json()
    assert rows == [
        {
            "user_id": rows[0]["user_id"],
            "name": "Ranked Solver",
            "seconds": 95,
            "hints_used": 0,
            "is_me": True,
        }
    ]


async def test_solve_wrong_no_reward(client):
    tokens = await register(client, "wrong@lab.ru")
    h = auth_headers(tokens)
    bad = [[1] * 6 for _ in range(6)]
    r = await client.post("/games/sudoku/solve", json={"solution": bad}, headers=h)
    body = r.json()
    assert body["correct"] is False
    assert body["coins_awarded"] == 0


def zip_solution_path(size: int = 7) -> list[list[int]]:
    path = []
    for r in range(size):
        cols = range(size) if r % 2 == 0 else range(size - 1, -1, -1)
        for c in cols:
            path.append([r, c])
    return path


async def test_zip_daily_endpoint(client):
    tokens = await register(client, "zip@lab.ru")
    h = auth_headers(tokens)
    r = await client.get("/games/zip/daily", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reward"] == 45
    assert body["size"] == 7
    assert body["solved_today"] is False
    assert len(body["markers"]) == 16
    assert body["markers"][0]["value"] == 1
    assert body["markers"][-1]["value"] == 16


async def test_zip_awards_once_per_day(client):
    tokens = await register(client, "zip-solve@lab.ru")
    h = auth_headers(tokens)
    coins_before = (await client.get("/pets/me", headers=h)).json()["coins"]

    first = await client.post(
        "/games/zip/solve",
        json={"path": zip_solution_path()},
        headers=h,
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["correct"] is True
    assert body["coins_awarded"] == 45
    assert body["coins"] == coins_before + 45

    second = await client.post(
        "/games/zip/solve",
        json={"path": zip_solution_path()},
        headers=h,
    )
    body = second.json()
    assert body["correct"] is True
    assert body["coins_awarded"] == 0
    assert body["already_solved"] is True


async def test_zip_wrong_no_reward(client):
    tokens = await register(client, "zip-wrong@lab.ru")
    h = auth_headers(tokens)
    r = await client.post(
        "/games/zip/solve",
        json={"path": [[0, 0], [0, 1], [0, 2]]},
        headers=h,
    )
    body = r.json()
    assert body["correct"] is False
    assert body["coins_awarded"] == 0
