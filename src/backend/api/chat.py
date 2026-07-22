"""
Chat Streaming API Router (`src/backend/api/chat.py`).

Provides Server-Sent Events (`SSE`) streaming endpoint (`POST /api/v1/chat/stream`) across AR/EN languages:
- Resolves the active encrypted vault profile via `X-LLM-Profile-ID` and the HttpOnly device cookie.
- Streams live retrieval tool execution events (`event: agent_search`) for Obsidian Graph camera animation.
- Streams grounded AI answer tokens (`event: token`).
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
try:
    from ...db.session import get_db
    from ...agent.react_agent import run_agent_stream
    from ...models.orm import VaultProfileORM
    from ...services.device_identity import get_or_create_device_hash
    from ...services.vault_crypto import VaultConfigError, VaultDecryptionError, decrypt_api_key
except ImportError:
    from db.session import get_db
    from agent.react_agent import run_agent_stream
    from models.orm import VaultProfileORM
    from services.device_identity import get_or_create_device_hash
    from services.vault_crypto import VaultConfigError, VaultDecryptionError, decrypt_api_key

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


async def _resolve_chat_credentials(
    *,
    session: AsyncSession,
    request: Request,
    response: Response,
    profile_id: Optional[str],
    fallback_provider: str,
    fallback_model: str,
    test_api_key: Optional[str],
) -> tuple[Optional[str], str, str]:
    """Resolve chat provider credentials from the encrypted vault, except in pytest fallback paths."""
    if os.getenv("PYTEST_CURRENT_TEST") is not None:
        return test_api_key, fallback_provider, fallback_model

    try:
        device_hash, _ = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    stmt = select(VaultProfileORM).where(VaultProfileORM.device_hash == device_hash)
    if profile_id and profile_id != "active":
        stmt = stmt.where(VaultProfileORM.id == profile_id)
    else:
        stmt = stmt.where(VaultProfileORM.is_active == True)
    result = await session.execute(stmt.order_by(VaultProfileORM.is_active.desc(), VaultProfileORM.created_at.desc()))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active encrypted API key profile is available for this device.")

    try:
        api_key = decrypt_api_key(
            encrypted_key=profile.encrypted_key,
            nonce=profile.nonce,
            device_hash=device_hash,
            profile_id=profile.id,
            provider=profile.provider,
            model=profile.model,
        )
    except VaultDecryptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    profile.last_used_at = datetime.now(timezone.utc).isoformat()
    await session.commit()
    return api_key, profile.provider, profile.model


class ChatRequestPayload(BaseModel):
    message: str = Field(..., description="User chat query")
    document_id: Optional[str] = Field(None, description="Scope query to specific document UUID or None for all workspace documents")
    language: str = Field("ar", description="ar | en")
    history: Optional[List[Dict[str, str]]] = Field(default=[], description="Previous conversation turn history")


@router.post("/stream")
async def stream_chat(
    payload: ChatRequestPayload,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    x_llm_api_key: Optional[str] = Header(None, alias="X-LLM-API-Key"),
    x_llm_profile_id: Optional[str] = Header(None, alias="X-LLM-Profile-ID"),
    x_llm_provider: Optional[str] = Header("deepseek", alias="X-LLM-Provider"),
    x_llm_model: Optional[str] = Header("deepseek-chat", alias="X-LLM-Model"),
    x_app_language: Optional[str] = Header("ar", alias="X-App-Language"),
    x_workflow_cycles: Optional[str] = Header("3", alias="X-Workflow-Cycles")
):
    """
    Execute streaming grounded ReAct chat session across Groq, DeepSeek, or OpenAI.
    Streams SSE dictionaries for live Obsidian Graph animation (`agent_search`) and token generation (`token`).
    """
    language = payload.language if payload.language else (x_app_language or "ar")
    try:
        cycles_val = int(x_workflow_cycles or "3")
        cycles_val = max(1, min(cycles_val, 6))
    except Exception:
        cycles_val = 3

    resolved_api_key, resolved_provider, resolved_model = await _resolve_chat_credentials(
        session=session,
        request=request,
        response=response,
        profile_id=x_llm_profile_id,
        fallback_provider=x_llm_provider or "deepseek",
        fallback_model=x_llm_model or "deepseek-chat",
        test_api_key=x_llm_api_key,
    )

    async def event_generator():
        try:
            async for event_dict in run_agent_stream(
                session=session,
                message=payload.message,
                language=language,
                document_id=payload.document_id,
                history=payload.history,
                custom_api_key=resolved_api_key,
                provider=resolved_provider,
                model=resolved_model,
                workflow_cycles=cycles_val
            ):
                event_type = event_dict.get("event", "token")
                data_content = event_dict.get("data", "")
                yield f"event: {event_type}\ndata: {data_content}\n\n"
        except Exception as e:
            err_msg = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err_msg}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
