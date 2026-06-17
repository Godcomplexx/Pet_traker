from .conftest import auth_headers, register


async def _workspace(client, headers, name="Checklist Lab"):
    resp = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_personal_task_checklist_is_private(client):
    alice = await register(client, "check-alice@lab.ru")
    bob = await register(client, "check-bob@lab.ru")
    ha, hb = auth_headers(alice), auth_headers(bob)
    task = (
        await client.post("/tasks", json={"scope": "PERSONAL", "title": "Private"}, headers=ha)
    ).json()

    created = await client.post(
        f"/tasks/{task['id']}/checklist",
        json={"title": "Read source", "kind": "CHECK"},
        headers=ha,
    )
    assert created.status_code == 201, created.text
    item = created.json()

    own_list = await client.get(f"/tasks/{task['id']}/checklist", headers=ha)
    assert own_list.status_code == 200
    assert own_list.json()[0]["title"] == "Read source"

    assert (await client.get(f"/tasks/{task['id']}/checklist", headers=hb)).status_code == 404
    assert (
        await client.patch(
            f"/task-checklist/{item['id']}",
            json={"is_done": True},
            headers=hb,
        )
    ).status_code == 404


async def test_team_task_checklist_crud_and_reorder(client):
    owner = await register(client, "check-owner@lab.ru")
    bob = await register(client, "check-member@lab.ru", "Bob")
    ho, hb = auth_headers(owner), auth_headers(bob)
    ws = await _workspace(client, ho)
    invited = await client.post(
        f"/workspaces/{ws['id']}/invite",
        json={"email": "check-member@lab.ru"},
        headers=ho,
    )
    assert invited.status_code == 201, invited.text
    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Team task"},
            headers=ho,
        )
    ).json()

    first = (
        await client.post(
            f"/tasks/{task['id']}/checklist",
            json={"title": "Prepare protocol", "kind": "SUBTASK"},
            headers=hb,
        )
    ).json()
    assert first["kind"] == "SUBTASK"
    second = (
        await client.post(
            f"/tasks/{task['id']}/checklist",
            json={"title": "Attach results", "kind": "CHECK"},
            headers=hb,
        )
    ).json()
    assert second["kind"] == "CHECK"

    done = await client.patch(
        f"/task-checklist/{first['id']}",
        json={"is_done": True, "title": "Prepare final protocol"},
        headers=ho,
    )
    assert done.status_code == 200, done.text
    assert done.json()["is_done"] is True
    assert done.json()["title"] == "Prepare final protocol"

    reordered = await client.patch(
        f"/tasks/{task['id']}/checklist/reorder",
        json={"order": [second["id"], first["id"]]},
        headers=hb,
    )
    assert reordered.status_code == 200, reordered.text
    assert [item["id"] for item in reordered.json()] == [second["id"], first["id"]]

    deleted = await client.delete(f"/task-checklist/{second['id']}", headers=ho)
    assert deleted.status_code == 204
    remaining = (await client.get(f"/tasks/{task['id']}/checklist", headers=hb)).json()
    assert [item["id"] for item in remaining] == [first["id"]]
