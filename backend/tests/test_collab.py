"""Comments, mentions, assignment & deadline notifications (spec §8.7, §8.10)."""
from app.core.database import SessionLocal
from app.services.deadlines import run_deadline_check
from tests.conftest import auth_headers, register


async def _workspace_with_member(client):
    owner = await register(client, "owner@lab.ru", "Owner")
    bob = await register(client, "bob@lab.ru", "Bob")
    ho, hb = auth_headers(owner), auth_headers(bob)
    ws = (await client.post("/workspaces", json={"name": "Lab"}, headers=ho)).json()
    await client.post(f"/workspaces/{ws['id']}/invite", json={"email": "bob@lab.ru"}, headers=ho)
    return ws, ho, hb, owner, bob


async def test_comment_grants_xp_and_mention_notifies(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    project = (
        await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "P"}, headers=ho)
    ).json()

    resp = await client.post(
        f"/projects/{project['id']}/comments",
        json={"text": "great work @bob@lab.ru"},
        headers=ho,
    )
    assert resp.status_code == 201, resp.text

    # Author earns +1 XP (capped elsewhere).
    pet = (await client.get("/pets/me", headers=ho)).json()
    assert pet["xp"] == 1

    # Bob (a member) gets a MENTION notification (FR-COM-6).
    notifs = (await client.get("/notifications", headers=hb)).json()
    assert any(n["type"] == "MENTION" for n in notifs)


async def test_mention_of_self_or_outsider_does_not_notify(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    project = (
        await client.post(f"/workspaces/{ws['id']}/projects", json={"name": "P"}, headers=ho)
    ).json()
    # Owner mentions self + a non-member email.
    await client.post(
        f"/projects/{project['id']}/comments",
        json={"text": "@owner@lab.ru note @ghost@nowhere.io"},
        headers=ho,
    )
    notifs = (await client.get("/notifications", headers=ho)).json()
    assert all(n["type"] != "MENTION" for n in notifs)


async def test_personal_task_comment_is_private(client):
    a = await register(client, "a@lab.ru")
    b = await register(client, "b@lab.ru")
    ha, hb = auth_headers(a), auth_headers(b)
    task = (
        await client.post("/tasks", json={"scope": "PERSONAL", "title": "diary"}, headers=ha)
    ).json()

    # Outsider cannot comment or read (FR-PT, EC-10).
    assert (
        await client.post(f"/tasks/{task['id']}/comments", json={"text": "hi"}, headers=hb)
    ).status_code == 404
    assert (await client.post(f"/tasks/{task['id']}/comments", json={"text": "note"}, headers=ha)).status_code == 201

    # No notifications were produced for anyone (FR-PT-9).
    assert (await client.get("/notifications", headers=hb)).json() == []
    assert (await client.get("/notifications", headers=ha)).json() == []


async def test_assignment_creates_notification(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    bob_id = (await client.get("/auth/me", headers=hb)).json()["id"]
    resp = await client.post(
        "/tasks",
        json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Do it", "assignee_id": bob_id},
        headers=ho,
    )
    assert resp.status_code == 201, resp.text

    notifs = (await client.get("/notifications", headers=hb)).json()
    assert any(n["type"] == "TASK_ASSIGNED" for n in notifs)


async def test_deadline_check_notifies_once(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    bob_id = (await client.get("/auth/me", headers=hb)).json()["id"]
    today = __import__("datetime").date.today().isoformat()
    await client.post(
        "/tasks",
        json={
            "scope": "WORKSPACE",
            "workspace_id": ws["id"],
            "title": "Due soon",
            "assignee_id": bob_id,
            "due_date": today,
        },
        headers=ho,
    )

    async with SessionLocal() as db:
        first = await run_deadline_check(db)
        second = await run_deadline_check(db)  # idempotent
    assert first == 1
    assert second == 0

    notifs = (await client.get("/notifications", headers=hb)).json()
    assert sum(1 for n in notifs if n["type"] == "DEADLINE") == 1


async def test_article_members_can_be_managed_by_elevated_workspace_member(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    bob_id = (await client.get("/auth/me", headers=hb)).json()["id"]
    article = (
        await client.post(f"/workspaces/{ws['id']}/articles", json={"title": "Paper"}, headers=ho)
    ).json()

    assert (await client.get(f"/articles/{article['id']}/members", headers=ho)).json() == []

    resp = await client.post(
        f"/articles/{article['id']}/members",
        json={"user_id": bob_id, "role": "REVIEWER"},
        headers=ho,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "REVIEWER"

    # Re-adding the same user updates their article role.
    resp = await client.post(
        f"/articles/{article['id']}/members",
        json={"user_id": bob_id, "role": "EDITOR"},
        headers=ho,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "EDITOR"

    # A regular workspace MEMBER can see article members but cannot manage them.
    assert (await client.get(f"/articles/{article['id']}/members", headers=hb)).status_code == 200
    assert (
        await client.post(
            f"/articles/{article['id']}/members",
            json={"user_id": bob_id, "role": "AUTHOR"},
            headers=hb,
        )
    ).status_code == 403

    resp = await client.delete(f"/articles/{article['id']}/members/{bob_id}", headers=ho)
    assert resp.status_code == 204, resp.text
    assert (await client.get(f"/articles/{article['id']}/members", headers=ho)).json() == []
