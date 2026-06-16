from tests.conftest import auth_headers, register


async def _workspace(client, headers, name="Audit Lab"):
    resp = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _me(client, headers):
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_audit_log_is_admin_only_and_tracks_task_changes(client):
    owner = await register(client, "audit-owner@lab.ru", "Owner")
    bob = await register(client, "audit-bob@lab.ru", "Bob")
    ho, hb = auth_headers(owner), auth_headers(bob)
    ws = await _workspace(client, ho)

    invited = await client.post(
        f"/workspaces/{ws['id']}/invite",
        json={"email": "audit-bob@lab.ru"},
        headers=ho,
    )
    assert invited.status_code == 201, invited.text
    bob_id = (await _me(client, hb))["id"]

    denied = await client.get(f"/workspaces/{ws['id']}/audit-log", headers=hb)
    assert denied.status_code == 403

    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Audited task"},
            headers=ho,
        )
    ).json()
    updated = await client.patch(
        f"/tasks/{task['id']}",
        json={
            "status": "IN_PROGRESS",
            "due_date": "2026-07-01",
            "assignee_id": bob_id,
        },
        headers=ho,
    )
    assert updated.status_code == 200, updated.text

    audit = await client.get(
        f"/workspaces/{ws['id']}/audit-log",
        params={"entity_type": "task", "entity_id": task["id"]},
        headers=ho,
    )
    assert audit.status_code == 200, audit.text
    entries = audit.json()
    changed = next(entry for entry in entries if entry["action"] == "task.updated")
    assert changed["actor_id"] == (await _me(client, ho))["id"]
    assert changed["target_user_id"] == bob_id
    assert changed["after"]["status"] == "IN_PROGRESS"
    assert changed["after"]["due_date"] == "2026-07-01"
    assert changed["after"]["assignee_id"] == bob_id
    assert changed["after"]["assignees"] == [bob_id]
    assert {"status", "due_date", "assignee_id", "assignees"}.issubset(
        set(changed["details"]["changed_fields"])
    )


async def test_workspace_owner_role_cannot_be_reassigned(client):
    owner = await register(client, "owner-role@lab.ru", "Owner")
    bob = await register(client, "owner-role-bob@lab.ru", "Bob")
    ho, hb = auth_headers(owner), auth_headers(bob)
    ws = await _workspace(client, ho, "Owner Role Lab")
    owner_id = (await _me(client, ho))["id"]

    invite_owner = await client.post(
        f"/workspaces/{ws['id']}/invite",
        json={"email": "owner-role-bob@lab.ru", "role": "OWNER"},
        headers=ho,
    )
    assert invite_owner.status_code == 400

    invited = await client.post(
        f"/workspaces/{ws['id']}/invite",
        json={"email": "owner-role-bob@lab.ru"},
        headers=ho,
    )
    assert invited.status_code == 201, invited.text
    bob_id = (await _me(client, hb))["id"]

    promote_owner = await client.patch(
        f"/workspaces/{ws['id']}/members/{bob_id}",
        json={"role": "OWNER"},
        headers=ho,
    )
    assert promote_owner.status_code == 400

    demote_owner = await client.patch(
        f"/workspaces/{ws['id']}/members/{owner_id}",
        json={"role": "ADMIN"},
        headers=ho,
    )
    assert demote_owner.status_code == 400


async def test_viewer_cannot_update_project(client):
    owner = await register(client, "viewer-owner@lab.ru", "Owner")
    viewer = await register(client, "viewer-user@lab.ru", "Viewer")
    ho, hv = auth_headers(owner), auth_headers(viewer)
    ws = await _workspace(client, ho, "Viewer Lab")

    invited = await client.post(
        f"/workspaces/{ws['id']}/invite",
        json={"email": "viewer-user@lab.ru", "role": "VIEWER"},
        headers=ho,
    )
    assert invited.status_code == 201, invited.text
    project = (
        await client.post(
            f"/workspaces/{ws['id']}/projects",
            json={"name": "Protected Project"},
            headers=ho,
        )
    ).json()

    denied = await client.patch(
        f"/projects/{project['id']}",
        json={"name": "Viewer Edit"},
        headers=hv,
    )
    assert denied.status_code == 403
