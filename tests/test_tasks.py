import pytest
from unittest.mock import patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task(auth_client: AsyncClient):
    with patch("app.api.v1.tasks.send_task_notification.delay"):
        resp = await auth_client.post(
            "/api/v1/tasks/",
            json={"title": "Buy groceries", "priority": "high"},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Buy groceries"
    assert data["status"] == "pending"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_list_tasks(auth_client: AsyncClient):
    with patch("app.api.v1.tasks.send_task_notification.delay"):
        await auth_client.post("/api/v1/tasks/", json={"title": "Task A"})
        await auth_client.post("/api/v1/tasks/", json={"title": "Task B"})
    resp = await auth_client.get("/api/v1/tasks/")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_update_task_status(auth_client: AsyncClient):
    with patch("app.api.v1.tasks.send_task_notification.delay"):
        created = await auth_client.post("/api/v1/tasks/", json={"title": "Update me"})
    task_id = created.json()["id"]
    resp = await auth_client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_delete_task(auth_client: AsyncClient):
    with patch("app.api.v1.tasks.send_task_notification.delay"):
        created = await auth_client.post("/api/v1/tasks/", json={"title": "Delete me"})
    task_id = created.json()["id"]
    resp = await auth_client.delete(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_get_nonexistent_task(auth_client: AsyncClient):
    resp = await auth_client.get("/api/v1/tasks/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request(client: AsyncClient):
    resp = await client.get("/api/v1/tasks/")
    assert resp.status_code == 403
