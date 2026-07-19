"""
Automated Test Suite for Streaming ReAct Agent (`src/backend/tests/test_react_agent.py`).

Verifies `GAP-ASKC-03`:
- Server-Sent Events (`SSE`) formatting (`event: agent_search`, `event: token`, `event: done`).
- Bilingual grounding (`ar` and `en`) with exact inline citations.
- Dynamic `X-LLM-API-Key` header ingestion without hardcoded production locks.
- Obsidian Graph View camera activation IDs (`active_node_ids`) emitted during tool calls.
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport
from main import app
from db.session import init_db


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
async def setup_db():
    await init_db()


@pytest.mark.anyio
async def test_streaming_chat_arabic_with_graph_event(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        payload = {
            "message": "من المسؤول عن متابعة حوادث السلامة وكيف يتم حساب مؤشر TRIR؟",
            "language": "ar"
        }
        headers = {
            "X-LLM-API-Key": "test-api-key",
            "X-App-Language": "ar"
        }
        
        async with client.stream("POST", "/api/v1/chat/stream", json=payload, headers=headers) as response:
            assert response.status_code == 200
            events = []
            active_nodes = []
            tokens = []
            
            async for line in response.aiter_lines():
                line = line.strip()
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                elif line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    if events and events[-1] == "agent_search":
                        data_json = json.loads(data_str)
                        if "active_node_ids" in data_json:
                            active_nodes.extend(data_json["active_node_ids"])
                    elif events and events[-1] == "token":
                        tokens.append(data_str)

            assert "agent_search" in events, "Expected live Obsidian Graph camera activation SSE event"
            assert "token" in events, "Expected streaming response tokens"
            assert "done" in events, "Expected completion event"
            assert len(active_nodes) >= 1, "Expected active chunk node IDs to trigger graph panning"
            full_answer = "".join(tokens)
            assert "[المصدر:" in full_answer, "Expected Arabic inline citation format in response"


@pytest.mark.anyio
async def test_streaming_chat_english_grounding(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        payload = {
            "message": "Who does the PMO Manager report to and what are their duties?",
            "language": "en"
        }
        
        async with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
            assert response.status_code == 200
            events = []
            tokens = []
            
            async for line in response.aiter_lines():
                line = line.strip()
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                elif line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    if events and events[-1] == "token":
                        tokens.append(data_str)

            assert "token" in events
            assert "done" in events
            full_answer = "".join(tokens)
            assert "[Source:" in full_answer, "Expected English inline citation format in response"
