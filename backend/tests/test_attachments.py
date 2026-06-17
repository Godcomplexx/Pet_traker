from app.core.config import settings

from .conftest import auth_headers, register


async def _workspace(client, headers, name="Files Lab"):
    resp = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_personal_task_attachment_is_private(client, tmp_path):
    settings.upload_dir = str(tmp_path)
    alice = await register(client, "files-alice@lab.ru")
    bob = await register(client, "files-bob@lab.ru")
    ha, hb = auth_headers(alice), auth_headers(bob)
    task = (
        await client.post("/tasks", json={"scope": "PERSONAL", "title": "Private"}, headers=ha)
    ).json()

    uploaded = await client.post(
        f"/tasks/{task['id']}/attachments",
        files={"file": ("protocol.pdf", b"%PDF-1.4\nbody", "application/pdf")},
        headers=ha,
    )
    assert uploaded.status_code == 201, uploaded.text
    attachment = uploaded.json()
    assert attachment["original_name"] == "protocol.pdf"
    assert attachment["version"] == 1
    assert attachment["download_url"].endswith(f"/attachments/{attachment['id']}/download")

    own_download = await client.get(f"/attachments/{attachment['id']}/download", headers=ha)
    assert own_download.status_code == 200
    assert own_download.content == b"%PDF-1.4\nbody"

    assert (await client.get(f"/tasks/{task['id']}/attachments", headers=hb)).status_code == 404
    assert (await client.get(f"/attachments/{attachment['id']}/download", headers=hb)).status_code == 404


async def test_team_task_attachment_versions_delete_and_validation(client, tmp_path):
    settings.upload_dir = str(tmp_path)
    owner = await register(client, "files-owner@lab.ru")
    member = await register(client, "files-member@lab.ru", "Member")
    ho, hm = auth_headers(owner), auth_headers(member)
    ws = await _workspace(client, ho)
    invited = await client.post(
        f"/workspaces/{ws['id']}/invite",
        json={"email": "files-member@lab.ru"},
        headers=ho,
    )
    assert invited.status_code == 201, invited.text
    task = (
        await client.post(
            "/tasks",
            json={"scope": "WORKSPACE", "workspace_id": ws["id"], "title": "Team files"},
            headers=ho,
        )
    ).json()

    first = await client.post(
        f"/tasks/{task['id']}/attachments",
        files={"file": ("results.csv", b"a,b\n1,2\n", "text/csv")},
        headers=hm,
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        f"/tasks/{task['id']}/attachments",
        files={"file": ("results.csv", b"a,b\n3,4\n", "text/csv")},
        headers=hm,
    )
    assert second.status_code == 201, second.text
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2

    listed = await client.get(f"/tasks/{task['id']}/attachments", headers=ho)
    assert listed.status_code == 200
    assert [item["version"] for item in listed.json()] == [2, 1]

    bad = await client.post(
        f"/tasks/{task['id']}/attachments",
        files={"file": ("run.exe", b"MZ", "application/octet-stream")},
        headers=ho,
    )
    assert bad.status_code == 400

    deleted = await client.delete(f"/attachments/{second.json()['id']}", headers=ho)
    assert deleted.status_code == 204
    remaining = (await client.get(f"/tasks/{task['id']}/attachments", headers=hm)).json()
    assert [item["id"] for item in remaining] == [first.json()["id"]]


async def test_project_and_article_attachments_follow_workspace_access(client, tmp_path):
    settings.upload_dir = str(tmp_path)
    owner = await register(client, "files-pa-owner@lab.ru")
    outsider = await register(client, "files-pa-out@lab.ru")
    ho, hx = auth_headers(owner), auth_headers(outsider)
    ws = await _workspace(client, ho, "Project Files Lab")
    project = (
        await client.post(
            f"/workspaces/{ws['id']}/projects",
            json={"name": "Project with file"},
            headers=ho,
        )
    ).json()
    article = (
        await client.post(
            f"/workspaces/{ws['id']}/articles",
            json={"title": "Article with file", "project_id": project["id"]},
            headers=ho,
        )
    ).json()

    project_upload = await client.post(
        f"/projects/{project['id']}/attachments",
        files={"file": ("plan.docx", b"doc", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=ho,
    )
    assert project_upload.status_code == 201, project_upload.text
    article_upload = await client.post(
        f"/articles/{article['id']}/attachments",
        files={"file": ("paper.pdf", b"%PDF", "application/pdf")},
        headers=ho,
    )
    assert article_upload.status_code == 201, article_upload.text

    assert (await client.get(f"/projects/{project['id']}/attachments", headers=ho)).json()[0]["project_id"] == project["id"]
    assert (await client.get(f"/articles/{article['id']}/attachments", headers=ho)).json()[0]["article_id"] == article["id"]
    assert (await client.get(f"/projects/{project['id']}/attachments", headers=hx)).status_code == 404
    assert (await client.get(f"/attachments/{article_upload.json()['id']}/download", headers=hx)).status_code == 404
