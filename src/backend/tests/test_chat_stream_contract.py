"""
Chat SSE contract tests.

WHY: The frontend depends on no-buffer SSE headers and typed delta events for real
provider streaming. This file tests the HTTP stream contract pieces that do not
require external provider calls.
"""

import base64
import os

os.environ["GPR_VAULT_MASTER_KEY"] = base64.urlsafe_b64encode(b"v" * 32).decode("ascii").rstrip("=")
os.environ["GPR_COOKIE_SECURE"] = "false"

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from tests.conftest import seed_curated_fixture


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def setup_db():
    await seed_curated_fixture()


@pytest.mark.anyio
async def test_chat_stream_has_no_buffer_headers(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/v1/chat/stream", json={"message": "Hello", "language": "en"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache, no-transform"
        assert response.headers["x-accel-buffering"] == "no"
