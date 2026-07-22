"""
Encrypted API-key vault API (`src/backend/api/vault.py`).

WHY: The frontend must not keep provider API keys in localStorage or send raw keys
on every chat request. These endpoints preserve GPR's no-login UX while storing
keys encrypted server-side and scoped to an HttpOnly device cookie.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ..db.session import get_db
    from ..models.orm import VaultProfileORM
    from ..services.device_identity import get_or_create_device_hash
    from ..services.provider_clients import check_provider_connection, default_model_for_provider
    from ..services.vault_crypto import (
        VaultConfigError,
        VaultDecryptionError,
        decrypt_api_key,
        encrypt_api_key,
    )
except ImportError:
    from db.session import get_db
    from models.orm import VaultProfileORM
    from services.device_identity import get_or_create_device_hash
    from services.provider_clients import check_provider_connection, default_model_for_provider
    from services.vault_crypto import VaultConfigError, VaultDecryptionError, decrypt_api_key, encrypt_api_key


router = APIRouter(prefix="/api/v1/vault", tags=["vault"])
ProviderName = Literal["deepseek", "groq", "openai", "gemini"]


class VaultProfileDTO(BaseModel):
    id: str
    label: str
    provider: str
    model: str
    key_hint: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    last_used_at: Optional[str] = None


class VaultBootstrapResponse(BaseModel):
    status: str = "ready"
    device_created: bool
    has_profiles: bool
    active_profile_id: Optional[str] = None


class VaultProfileCreateRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=160)
    provider: ProviderName = "deepseek"
    model: str = Field("", max_length=160)
    api_key: str = Field(..., min_length=5, max_length=4096)
    activate: bool = True
    test_before_save: bool = False


class VaultProfileTestResponse(BaseModel):
    status: str
    message: str
    preview: str = ""


class VaultCheckApiRequest(BaseModel):
    provider: ProviderName = "deepseek"
    model: str = Field("", max_length=160)
    api_key: str = Field(..., min_length=5, max_length=4096)


def _dto(profile: VaultProfileORM) -> VaultProfileDTO:
    return VaultProfileDTO(
        id=profile.id,
        label=profile.label,
        provider=profile.provider,
        model=profile.model,
        key_hint=profile.key_hint,
        is_active=bool(profile.is_active),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        last_used_at=profile.last_used_at,
    )


async def _profiles_for_device(session: AsyncSession, device_hash: str) -> List[VaultProfileORM]:
    result = await session.execute(
        select(VaultProfileORM)
        .where(VaultProfileORM.device_hash == device_hash)
        .order_by(VaultProfileORM.is_active.desc(), VaultProfileORM.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_profile_or_404(session: AsyncSession, device_hash: str, profile_id: str) -> VaultProfileORM:
    result = await session.execute(
        select(VaultProfileORM).where(
            VaultProfileORM.device_hash == device_hash,
            VaultProfileORM.id == profile_id,
        )
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault profile not found for this device.")
    return profile


async def _activate_profile(session: AsyncSession, device_hash: str, profile: VaultProfileORM) -> None:
    profiles = await _profiles_for_device(session, device_hash)
    now = datetime.now(timezone.utc).isoformat()
    for existing in profiles:
        existing.is_active = existing.id == profile.id
        existing.updated_at = now


@router.post("/bootstrap", response_model=VaultBootstrapResponse)
async def bootstrap_vault(request: Request, response: Response, session: AsyncSession = Depends(get_db)):
    """Create/read the HttpOnly device cookie and return non-secret vault status."""
    try:
        device_hash, created = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    profiles = await _profiles_for_device(session, device_hash)
    active = next((p for p in profiles if p.is_active), None)
    return VaultBootstrapResponse(device_created=created, has_profiles=bool(profiles), active_profile_id=active.id if active else None)


@router.get("/profiles", response_model=List[VaultProfileDTO])
async def list_vault_profiles(request: Request, response: Response, session: AsyncSession = Depends(get_db)):
    """List non-secret vault profile metadata for the current device."""
    try:
        device_hash, _ = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return [_dto(profile) for profile in await _profiles_for_device(session, device_hash)]




@router.post("/check-api", response_model=VaultProfileTestResponse)
async def check_raw_api_key_once(payload: VaultCheckApiRequest):
    """Test a raw key once before saving it; the key is never stored by this endpoint."""
    check = await check_provider_connection(payload.provider, payload.model, payload.api_key)
    return VaultProfileTestResponse(status=check.status, message=check.message, preview=check.preview)


@router.post("/profiles", response_model=VaultProfileDTO, status_code=status.HTTP_201_CREATED)
async def create_vault_profile(
    payload: VaultProfileCreateRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    """Encrypt and store one provider API key for the current no-login device."""
    try:
        device_hash, _ = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    provider = payload.provider.lower().strip()
    model = default_model_for_provider(provider, payload.model)
    if payload.test_before_save:
        check = await check_provider_connection(provider, model, payload.api_key)
        if check.status != "valid":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=check.message)

    profile = VaultProfileORM(
        device_hash=device_hash,
        label=payload.label.strip(),
        provider=provider,
        model=model,
        encrypted_key="pending",
        nonce="pending",
        key_fingerprint="pending",
        key_hint="",
        is_active=False,
    )
    session.add(profile)
    await session.flush()

    try:
        encrypted = encrypt_api_key(payload.api_key, device_hash=device_hash, profile_id=profile.id, provider=provider, model=model)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    profile.encrypted_key = encrypted.ciphertext
    profile.nonce = encrypted.nonce
    profile.key_fingerprint = encrypted.fingerprint
    profile.key_hint = encrypted.key_hint
    profile.updated_at = datetime.now(timezone.utc).isoformat()

    if payload.activate:
        await _activate_profile(session, device_hash, profile)
    await session.commit()
    await session.refresh(profile)
    return _dto(profile)


@router.post("/profiles/{profile_id}/activate", response_model=VaultProfileDTO)
async def activate_vault_profile(profile_id: str, request: Request, response: Response, session: AsyncSession = Depends(get_db)):
    """Make a vault profile the active provider key for the current device."""
    try:
        device_hash, _ = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    profile = await _get_profile_or_404(session, device_hash, profile_id)
    await _activate_profile(session, device_hash, profile)
    await session.commit()
    await session.refresh(profile)
    return _dto(profile)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_200_OK)
async def delete_vault_profile(profile_id: str, request: Request, response: Response, session: AsyncSession = Depends(get_db)):
    """Delete one vault profile for the current device only."""
    try:
        device_hash, _ = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    profile = await _get_profile_or_404(session, device_hash, profile_id)
    was_active = bool(profile.is_active)
    await session.delete(profile)
    await session.flush()

    if was_active:
        remaining = await _profiles_for_device(session, device_hash)
        if remaining:
            await _activate_profile(session, device_hash, remaining[0])
    await session.commit()
    return {"status": "deleted", "profile_id": profile_id}


@router.post("/profiles/{profile_id}/test", response_model=VaultProfileTestResponse)
async def test_vault_profile(profile_id: str, request: Request, response: Response, session: AsyncSession = Depends(get_db)):
    """Decrypt a vault profile server-side and verify its provider connection."""
    try:
        device_hash, _ = get_or_create_device_hash(request, response)
        profile = await _get_profile_or_404(session, device_hash, profile_id)
        api_key = decrypt_api_key(
            encrypted_key=profile.encrypted_key,
            nonce=profile.nonce,
            device_hash=device_hash,
            profile_id=profile.id,
            provider=profile.provider,
            model=profile.model,
        )
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except VaultDecryptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    check = await check_provider_connection(profile.provider, profile.model, api_key)
    return VaultProfileTestResponse(status=check.status, message=check.message, preview=check.preview)
