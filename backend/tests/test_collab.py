"""Comments, mentions, assignment & deadline notifications (spec §8.7, §8.10)."""
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import WallPost
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


async def test_wall_post_does_not_create_system_notifications(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    resp = await client.post(
        f"/workspaces/{ws['id']}/wall",
        json={"text": "Новый результат в лаборатории"},
        headers=ho,
    )
    assert resp.status_code == 201, resp.text

    bob_notifs = (await client.get("/notifications", headers=hb)).json()
    assert all(n["entity_id"] != resp.json()["id"] for n in bob_notifs)

    owner_notifs = (await client.get("/notifications", headers=ho)).json()
    assert all(n["type"] != "WALL_POST" for n in owner_notifs)


async def test_wall_images_reactions_and_daily_cleanup(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    image = "data:image/png;base64,iVBORw0KGgo="
    post_resp = await client.post(
        f"/workspaces/{ws['id']}/wall",
        json={"text": "", "image_data": image},
        headers=ho,
    )
    assert post_resp.status_code == 201, post_resp.text
    post = post_resp.json()
    assert post["image_data"] == image

    gif_url = "https://example.com/cat.gif"
    gif_resp = await client.post(
        f"/workspaces/{ws['id']}/wall",
        json={"text": "gif", "image_data": gif_url},
        headers=ho,
    )
    assert gif_resp.status_code == 201, gif_resp.text
    assert gif_resp.json()["image_data"] == gif_url

    react = await client.post(f"/wall/{post['id']}/react", json={"emoji": "👍"}, headers=hb)
    assert react.status_code == 200, react.text
    assert react.json()["reactions"]["👍"] == 1
    assert react.json()["my_reactions"] == ["👍"]

    unreact = await client.post(f"/wall/{post['id']}/react", json={"emoji": "👍"}, headers=hb)
    assert unreact.status_code == 200, unreact.text
    assert unreact.json()["reactions"].get("👍") is None

    dislike = await client.post(f"/wall/{post['id']}/react", json={"emoji": "👎"}, headers=hb)
    assert dislike.status_code == 200, dislike.text
    assert dislike.json()["reactions"]["👎"] == 1

    report_post = (
        await client.post(
            f"/workspaces/{ws['id']}/wall",
            json={"text": "Это надо убрать"},
            headers=ho,
        )
    ).json()
    report = await client.post(f"/wall/{report_post['id']}/report", json={}, headers=hb)
    assert report.status_code == 204, report.text
    visible = (await client.get(f"/workspaces/{ws['id']}/wall", headers=ho)).json()
    assert all(p["id"] != report_post["id"] for p in visible)

    async with SessionLocal() as db:
        old = await db.get(WallPost, post["id"])
        old.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        await db.commit()

    wall = (await client.get(f"/workspaces/{ws['id']}/wall", headers=ho)).json()
    assert all(p["id"] != post["id"] for p in wall)


async def test_wall_presence_controls_team_room_pets(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    empty = (await client.get(f"/workspaces/{ws['id']}/team-room", headers=ho)).json()
    assert empty["pets"] == []
    assert empty["online_count"] == 0

    heartbeat = await client.post(f"/workspaces/{ws['id']}/wall/presence", headers=hb)
    assert heartbeat.status_code == 204

    online = (await client.get(f"/workspaces/{ws['id']}/team-room", headers=ho)).json()
    assert online["online_count"] == 1
    assert len(online["pets"]) == 1
    assert online["pets"][0]["user_id"]

    leave = await client.delete(f"/workspaces/{ws['id']}/wall/presence", headers=hb)
    assert leave.status_code == 204

    empty_again = (await client.get(f"/workspaces/{ws['id']}/team-room", headers=ho)).json()
    assert empty_again["pets"] == []


async def test_wall_rps_challenge_notifies_and_rewards_winner(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    bob_me = (await client.get("/auth/me", headers=hb)).json()

    invite = await client.post(
        f"/workspaces/{ws['id']}/rps",
        json={"opponent_id": bob_me["id"], "choice": "rock"},
        headers=ho,
    )
    assert invite.status_code == 201, invite.text
    challenge = invite.json()
    assert challenge["status"] == "pending"
    assert challenge["challenger_choice"] == "rock"

    wall_before_finish = (await client.get(f"/workspaces/{ws['id']}/wall", headers=ho)).json()
    assert not any("Камень-ножницы-бумага" in post["text"] for post in wall_before_finish)
    assert not any("предложил сыграть" in post["text"] for post in wall_before_finish)

    bob_notifs = (await client.get("/notifications", headers=hb)).json()
    assert any(
        n["entity_type"] == "rps_challenge" and n["entity_id"] == challenge["id"]
        for n in bob_notifs
    )

    accepted = await client.post(
        f"/rps/challenges/{challenge['id']}/respond",
        json={"accept": True},
        headers=hb,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    finish = await client.post(
        f"/rps/challenges/{challenge['id']}/choice",
        json={"choice": "scissors"},
        headers=hb,
    )
    assert finish.status_code == 200, finish.text
    body = finish.json()
    assert body["status"] == "completed"
    assert body["winner_id"] == (await client.get("/auth/me", headers=ho)).json()["id"]

    owner_pet = (await client.get("/pets/me", headers=ho)).json()
    bob_pet = (await client.get("/pets/me", headers=hb)).json()
    assert owner_pet["coins"] == 5
    assert bob_pet["coins"] == 0

    wall = (await client.get(f"/workspaces/{ws['id']}/wall", headers=ho)).json()
    assert any("Камень-ножницы-бумага" in post["text"] and "+5" in post["text"] for post in wall)
    assert not any("предложил сыграть" in post["text"] for post in wall)


async def test_wall_rps_bot_rewards_winner(client, monkeypatch):
    from app.api.routers import wall

    ws, ho, _hb, _owner, _bob = await _workspace_with_member(client)
    monkeypatch.setattr(wall.random, "choice", lambda _choices: "scissors")

    result = await client.post(
        f"/workspaces/{ws['id']}/rps/bot",
        json={"choice": "rock"},
        headers=ho,
    )
    assert result.status_code == 200, result.text
    assert "+5" in result.json()["text"]

    owner_pet = (await client.get("/pets/me", headers=ho)).json()
    assert owner_pet["coins"] == 5

    wall_posts = (await client.get(f"/workspaces/{ws['id']}/wall", headers=ho)).json()
    assert any("+5" in post["text"] for post in wall_posts)


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


async def test_team_task_comment_notifies_assignee(client):
    ws, ho, hb, owner, bob = await _workspace_with_member(client)
    bob_id = (await client.get("/auth/me", headers=hb)).json()["id"]
    task = (
        await client.post(
            "/tasks",
            json={
                "scope": "WORKSPACE",
                "workspace_id": ws["id"],
                "title": "Discuss draft",
                "assignee_ids": [bob_id],
            },
            headers=ho,
        )
    ).json()

    await client.patch("/notifications/read-all", headers=hb)
    resp = await client.post(
        f"/tasks/{task['id']}/comments",
        json={"text": "please check the last section"},
        headers=ho,
    )
    assert resp.status_code == 201, resp.text

    notifs = (await client.get("/notifications", headers=hb)).json()
    comment_notif = next(n for n in notifs if n["type"] == "MENTION" and not n["is_read"])
    assert comment_notif["entity_type"] == "task"
    assert comment_notif["entity_id"] == task["id"]
    assert "last section" in comment_notif["body"]


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
