"""
Chat Streaming API Router (`src/backend/api/chat.py`).

Provides Server-Sent Events (`SSE`) streaming endpoint (`POST /api/v1/chat/stream`) across AR/EN languages:
- Accepts custom DeepSeek/OpenAI API keys via `X-LLM-API-Key` header.
- Streams live retrieval tool execution events (`event: agent_search`) for Obsidian Graph camera animation.
- Streams grounded AI answer tokens (`event: token`).
"""

import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from ...db.session import get_db
    from ...agent.react_agent import run_agent_stream
except ImportError:
    from db.session import get_db
    from agent.react_agent import run_agent_stream

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequestPayload(BaseModel):
    message: str = Field(..., description="User chat query")
    document_id: Optional[str] = Field(None, description="Scope query to specific document UUID or None for all workspace documents")
    language: str = Field("ar", description="ar | en")
    history: Optional[List[Dict[str, str]]] = Field(default=[], description="Previous conversation turn history")


@router.post("/stream")
async def stream_chat(
    payload: ChatRequestPayload,
    session: AsyncSession = Depends(get_db),
    x_llm_api_key: Optional[str] = Header(None, alias="X-LLM-API-Key"),
    x_app_language: Optional[str] = Header("ar", alias="X-App-Language")
):
    """
    Execute streaming grounded ReAct chat session.
    Streams SSE dictionaries for live Obsidian Graph animation (`agent_search`) and token generation (`token`).
    """
    language = payload.language if payload.language else (x_app_language or "ar")

    async def event_generator():
        try:
            async for event_dict in run_agent_stream(
                session=session,
                message=payload.message,
                language=language,
                document_id=payload.document_id,
                history=payload.history,
                custom_api_key=x_llm_api_key
            ):
                event_type = event_dict.get("event", "token")
                data_content = event_dict.get("data", "")
                yield f"event: {event_type}\ndata: {data_content}\n\n"
        except Exception as e:
            err_msg = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err_msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
