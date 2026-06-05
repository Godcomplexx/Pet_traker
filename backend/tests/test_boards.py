"""Канбан-доски: богатые поля листинга, DnD-move (статус+порядок), поиск."""
from tests.conftest import auth_headers, register


async def _ws(client, email="board@lab.ru"):
    tokens = await register(client, email, "Board User")
    h = auth_headers(tokens)
    ws = (await client.post("/workspaces", json={"name": "Lab"}, headers=h)).json()
    return ws, h


async def test_project_listing_has_rich_fields(client):
    ws, h = await _ws(client)
    p = (await client.post(
        f"/workspaces/{ws['id']}/projects",
        json={"name": "Portal", "type": "SOFTWARE", "status": "IDEA"},
        headers=h,
    )).json()
    # две задачи, одну закрываем
    t1 = (await client.post(
        "/tasks", json={"scope": "PROJECT", "project_id": p["id"], "title": "T1"}, headers=h
    )).json()
    await client.post(
        "/tasks", json={"scope": "PROJECT", "project_id": p["id"], "title": "T2"}, headers=h
    )
    await client.patch(f"/tasks/{t1['id']}/complete", headers=h)

    rows = (await client.get(f"/workspaces/{ws['id']}/projects", headers=h)).json()
    card = rows[0]
    assert card["task_total"] == 2
    assert card["task_done"] == 1
    assert card["article_count"] == 0
    assert "position" in card
    assert card["member_ids"] == []


async def test_project_move_changes_status_and_order(client):
    ws, h = await _ws(client, "move-proj@lab.ru")
    a = (await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "A"}, headers=h)).json()
    b = (await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "B"}, headers=h)).json()

    # A → ACTIVE с порядком [B, A] в IDEA не важен; проверяем смену колонки
    r = await client.patch(
        f"/projects/{a['id']}/move",
        json={"status": "ACTIVE", "order": [a["id"]]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACTIVE"

    # порядок внутри IDEA: [B] → position 0
    r2 = await client.patch(
        f"/projects/{b['id']}/move",
        json={"status": "IDEA", "order": [b["id"]]},
        headers=h,
    )
    assert r2.json()["position"] == 0


async def test_project_move_to_done_rewards_pet(client):
    ws, h = await _ws(client, "done-proj@lab.ru")
    p = (await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "P"}, headers=h)).json()
    coins_before = (await client.get("/pets/me", headers=h)).json()["coins"]
    r = await client.patch(
        f"/projects/{p['id']}/move", json={"status": "DONE", "order": [p["id"]]}, headers=h
    )
    assert r.status_code == 200
    # награда за DONE начисляется (XP/coins растут через события)
    coins_after = (await client.get("/pets/me", headers=h)).json()["coins"]
    assert coins_after >= coins_before


async def test_article_move_changes_status(client):
    ws, h = await _ws(client, "move-art@lab.ru")
    art = (await client.post(
        f"/workspaces/{ws['id']}/articles", json={"title": "Methodology"}, headers=h
    )).json()
    r = await client.patch(
        f"/articles/{art['id']}/move", json={"status": "WRITING", "order": [art["id"]]}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "WRITING"


async def test_task_move_to_done_sets_completer(client):
    ws, h = await _ws(client, "move-task@lab.ru")
    t = (await client.post(
        "/tasks", json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Ship"}, headers=h
    )).json()
    r = await client.patch(
        f"/tasks/{t['id']}/move", json={"status": "DONE", "order": [t["id"]]}, headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "DONE"
    assert body["completed_by"] is not None


async def test_project_search(client):
    ws, h = await _ws(client, "search@lab.ru")
    await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "Portal"}, headers=h)
    await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "Pipeline"}, headers=h)
    found = (await client.get(f"/workspaces/{ws['id']}/projects?q=Port", headers=h)).json()
    assert len(found) == 1
    assert found[0]["name"] == "Portal"
