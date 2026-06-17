import asyncio

from app.services.realtime import can_receive, hub
from tests.conftest import auth_headers, register


async def _workspace_with_member(client):
    owner = await register(client, "rt-owner@lab.ru", "Owner")
    bob = await register(client, "rt-bob@lab.ru", "Bob")
    ho, hb = auth_headers(owner), auth_headers(bob)
    ws = (await client.post("/workspaces", json={"name": "Live Lab"}, headers=ho)).json()
    await client.post(f"/workspaces/{ws['id']}/invite", json={"email": "rt-bob@lab.ru"}, headers=ho)
    return ws, ho, hb


async def _next_event(queue, type_, timeout=1):
    while True:
        event = await asyncio.wait_for(queue.get(), timeout=timeout)
        if event["type"] == type_:
            return event


async def _events_until(queue, wanted, timeout=1):
    seen = {}
    deadline = asyncio.get_running_loop().time() + timeout
    while not set(wanted).issubset(seen):
        remaining = deadline - asyncio.get_running_loop().time()
        assert remaining > 0, f"Missing live events: {set(wanted) - set(seen)}"
        event = await asyncio.wait_for(queue.get(), timeout=remaining)
        seen.setdefault(event["type"], event)
    return seen


async def test_live_endpoint_rejects_bad_token(client):
    resp = await client.get("/live/events?token=bad")
    assert resp.status_code == 401


async def test_task_assignment_and_comment_publish_live_events(client):
    ws, ho, hb = await _workspace_with_member(client)
    bob = (await client.get("/auth/me", headers=hb)).json()
    queue = hub.subscribe()
    try:
        task_resp = await client.post(
            "/tasks",
            json={
                "scope": "WORKSPACE",
                "workspace_id": ws["id"],
                "title": "Live task",
                "assignee_ids": [bob["id"]],
            },
            headers=ho,
        )
        assert task_resp.status_code == 201, task_resp.text
        events = await _events_until(queue, {"task.created", "notification.created"})
        created = events["task.created"]
        assert can_receive(created, user_id=bob["id"], workspace_ids={ws["id"]})

        notification = events["notification.created"]
        assert notification["payload"]["entity_type"] == "task"
        assert notification["target_user_ids"] == [bob["id"]]

        task = task_resp.json()
        comment_resp = await client.post(
            f"/tasks/{task['id']}/comments",
            json={"text": "live note"},
            headers=hb,
        )
        assert comment_resp.status_code == 201, comment_resp.text
        comment = await _next_event(queue, "comment.created")
        assert comment["payload"]["entity_type"] == "task"
        assert comment["payload"]["entity_id"] == task["id"]
        assert comment["payload"]["text"] == "live note"
    finally:
        hub.unsubscribe(queue)


async def test_task_typing_publishes_workspace_event(client):
    ws, ho, hb = await _workspace_with_member(client)
    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Typing"},
            headers=ho,
        )
    ).json()
    queue = hub.subscribe()
    try:
        resp = await client.post(f"/tasks/{task['id']}/typing", headers=hb)
        assert resp.status_code == 204, resp.text
        event = await _next_event(queue, "task.typing")
        assert event["workspace_id"] == ws["id"]
        assert event["payload"]["task_id"] == task["id"]
        assert event["payload"]["display_name"] == "Bob"
    finally:
        hub.unsubscribe(queue)
