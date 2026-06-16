import csv
from io import StringIO

from tests.conftest import auth_headers, register


async def _workspace(client, headers, name="Integrations Lab"):
    resp = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_api_token_can_authenticate_and_be_revoked(client):
    tokens = await register(client, "api-token@lab.ru")
    h = auth_headers(tokens)

    created = await client.post("/api-tokens", json={"name": "CI import"}, headers=h)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["token"].startswith("lm_")
    assert body["token_prefix"] == body["token"][:12]

    token_headers = {"Authorization": f"Bearer {body['token']}"}
    me = await client.get("/auth/me", headers=token_headers)
    assert me.status_code == 200
    assert me.json()["email"] == "api-token@lab.ru"

    listed = (await client.get("/api-tokens", headers=h)).json()
    assert listed[0]["last_used_at"] is not None
    assert "token" not in listed[0]

    revoked = await client.delete(f"/api-tokens/{body['id']}", headers=h)
    assert revoked.status_code == 204
    denied = await client.get("/auth/me", headers=token_headers)
    assert denied.status_code == 401


async def test_csv_import_and_exports(client):
    tokens = await register(client, "csv@lab.ru")
    h = auth_headers(tokens)
    ws = await _workspace(client, h)
    project = (
        await client.post(
            f"/workspaces/{ws['id']}/projects",
            json={"name": "Import Project"},
            headers=h,
        )
    ).json()

    csv_body = (
        "title,description,project_id,type,priority,status,due_date\n"
        f"Imported task,From CSV,{project['id']},RESEARCH,HIGH,IN_PROGRESS,2026-07-01\n"
        "Workspace task,, ,ADMIN,LOW,TODO,\n"
    )
    imported = await client.post(
        f"/workspaces/{ws['id']}/imports/tasks.csv",
        files={"file": ("tasks.csv", csv_body.encode("utf-8"), "text/csv")},
        headers=h,
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["created"] == 2

    task_export = await client.get(f"/workspaces/{ws['id']}/exports/tasks.csv", headers=h)
    assert task_export.status_code == 200
    rows = list(csv.DictReader(StringIO(task_export.text)))
    assert {row["title"] for row in rows} == {"Imported task", "Workspace task"}
    assert next(row for row in rows if row["title"] == "Imported task")["project_id"] == project["id"]

    project_export = await client.get(f"/workspaces/{ws['id']}/exports/projects.csv", headers=h)
    assert project_export.status_code == 200
    assert "Import Project" in project_export.text


async def test_webhook_delivery_is_queued_for_domain_event(client):
    tokens = await register(client, "webhook@lab.ru")
    h = auth_headers(tokens)
    ws = await _workspace(client, h)

    hook = await client.post(
        f"/workspaces/{ws['id']}/webhooks",
        json={"url": "https://example.com/labmate-hook", "events": ["TASK_COMPLETED"]},
        headers=h,
    )
    assert hook.status_code == 201, hook.text
    assert hook.json()["secret"].startswith("whsec_")

    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Notify hook"},
            headers=h,
        )
    ).json()
    done = await client.patch(f"/tasks/{task['id']}/complete", headers=h)
    assert done.status_code == 200, done.text

    deliveries = (
        await client.get(f"/workspaces/{ws['id']}/webhook-deliveries", headers=h)
    ).json()
    assert len(deliveries) == 1
    assert deliveries[0]["status"] == "queued"
    assert deliveries[0]["event_type"] == "TASK_COMPLETED"
    assert deliveries[0]["payload"]["entity_id"] == task["id"]
