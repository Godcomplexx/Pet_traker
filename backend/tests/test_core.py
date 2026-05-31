"""Core invariant tests (spec §20-21): pet, gamification, privacy, idempotency."""
from tests.conftest import auth_headers, register


async def _make_workspace(client, headers, name="Lab"):
    resp = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_creates_pet(client):
    tokens = await register(client, "a@lab.ru")
    resp = await client.get("/pets/me", headers=auth_headers(tokens))
    assert resp.status_code == 200
    pet = resp.json()
    assert pet["xp"] == 0 and pet["level"] == 1
    # Новый питомец ещё не настроен — фронт покажет экран создания.
    assert pet["customized"] is False


async def test_customize_pet(client):
    tokens = await register(client, "look@lab.ru")
    h = auth_headers(tokens)
    resp = await client.put(
        "/pets/me",
        json={"name": "Кодзи", "species": "frog", "body_color": "#7bA86b", "accent_color": "#33603f"},
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    pet = resp.json()
    assert pet["name"] == "Кодзи"
    assert pet["species"] == "frog"
    assert pet["body_color"] == "#7bA86b"
    assert pet["customized"] is True

    # Неизвестный вид — 422.
    bad = await client.put(
        "/pets/me",
        json={"name": "X", "species": "dragon"},
        headers=h,
    )
    assert bad.status_code == 422


async def test_team_task_completion_grants_xp_and_activity(client):
    tokens = await register(client, "owner@lab.ru")
    h = auth_headers(tokens)
    ws = await _make_workspace(client, h)

    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Ship API"},
            headers=h,
        )
    ).json()

    done = await client.patch(f"/tasks/{task['id']}/complete", headers=h)
    assert done.status_code == 200
    assert done.json()["status"] == "DONE"

    pet = (await client.get("/pets/me", headers=h)).json()
    assert pet["xp"] == 10  # base team-task reward

    feed = (await client.get(f"/workspaces/{ws['id']}/activity", headers=h)).json()
    assert len(feed) == 1 and feed[0]["entity_type"] == "task"


async def test_completion_is_idempotent(client):
    tokens = await register(client, "idem@lab.ru")
    h = auth_headers(tokens)
    ws = await _make_workspace(client, h)
    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "X"},
            headers=h,
        )
    ).json()

    await client.patch(f"/tasks/{task['id']}/complete", headers=h)
    await client.patch(f"/tasks/{task['id']}/complete", headers=h)  # second time = no-op

    pet = (await client.get("/pets/me", headers=h)).json()
    assert pet["xp"] == 10  # not doubled (EC-1 / AC-18)


async def test_personal_task_is_private(client):
    a = await register(client, "alice@lab.ru")
    b = await register(client, "bob@lab.ru")
    ha, hb = auth_headers(a), auth_headers(b)

    task = (
        await client.post(
            "/tasks",
            json={"scope": "PERSONAL", "title": "Secret diary"},
            headers=ha,
        )
    ).json()
    assert task["visibility"] == "PRIVATE"

    # Bob must not be able to see Alice's personal task (AC-11).
    assert (await client.get(f"/tasks/{task['id']}", headers=hb)).status_code == 404
    # Alice can.
    assert (await client.get(f"/tasks/{task['id']}", headers=ha)).status_code == 200


async def test_personal_task_reward_is_smaller_and_no_activity(client):
    tokens = await register(client, "p@lab.ru")
    h = auth_headers(tokens)
    ws = await _make_workspace(client, h)  # exists, but personal task is unrelated

    task = (
        await client.post("/tasks", json={"scope": "PERSONAL", "title": "Read paper"}, headers=h)
    ).json()
    await client.patch(f"/tasks/{task['id']}/complete", headers=h)

    pet = (await client.get("/pets/me", headers=h)).json()
    assert pet["xp"] == 5  # personal < team (FR-GAME-3)

    # No workspace activity for personal work (FR-PT-6 / AC-13).
    feed = (await client.get(f"/workspaces/{ws['id']}/activity", headers=h)).json()
    assert feed == []


async def test_outsider_cannot_see_workspace(client):
    owner = await register(client, "o2@lab.ru")
    outsider = await register(client, "out@lab.ru")
    ws = await _make_workspace(client, auth_headers(owner))
    resp = await client.get(f"/workspaces/{ws['id']}", headers=auth_headers(outsider))
    assert resp.status_code == 404  # NFR-4 / does not leak existence
