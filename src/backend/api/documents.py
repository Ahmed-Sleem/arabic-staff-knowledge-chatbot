"""
Documents API Router (`src/backend/api/documents.py`).

Provides endpoints for universal multi-document ingestion, TOC fetching, deletion, and Obsidian Graph queries:
- `POST /api/v1/documents/upload`: Uploads any file (`pdf`, `docx`, `txt`, `md`) and triggers LLM semantic pipeline.
- `GET /api/v1/documents`: Lists persistent workspace documents.
- `GET /api/v1/documents/{id}`: Retrieves document details and Table of Contents (`toc_tree`).
- `DELETE /api/v1/documents/{id}`: Deletes file from disk and wipes relational records.
- `GET /api/v1/documents/graph`: Retrieves force-directed node-link dataset (`GraphViewDTO`).
"""

import os
import uuid
import aiofiles
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, UploadFile, File, Form, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
try:
    from ...db.session import get_db
    from ...db.repositories import DocumentRepository, GraphRepository
    from ...models.domain import DocumentDTO, GraphViewDTO
    from ...models.orm import VaultProfileORM
    from ...services.device_identity import get_or_create_device_hash
    from ...services.vault_crypto import decrypt_api_key, VaultConfigError, VaultDecryptionError
    from ...services.ingestion.universal_pipeline import process_document_pipeline
except ImportError:
    from db.session import get_db
    from db.repositories import DocumentRepository, GraphRepository
    from models.domain import DocumentDTO, GraphViewDTO
    from models.orm import VaultProfileORM
    from services.device_identity import get_or_create_device_hash
    from services.vault_crypto import decrypt_api_key, VaultConfigError, VaultDecryptionError
    from services.ingestion.universal_pipeline import process_document_pipeline

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _resolve_optional_upload_key(
    session: AsyncSession,
    request: Request,
    response: Response,
    profile_id: Optional[str],
) -> Optional[str]:
    """Resolve an optional encrypted vault profile for LLM-assisted ingestion."""
    if not profile_id:
        return None
    try:
        device_hash, _ = get_or_create_device_hash(request, response)
    except VaultConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    result = await session.execute(
        select(VaultProfileORM).where(VaultProfileORM.device_hash == device_hash, VaultProfileORM.id == profile_id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault profile not found for this device.")
    try:
        return decrypt_api_key(
            encrypted_key=profile.encrypted_key,
            nonce=profile.nonce,
            device_hash=device_hash,
            profile_id=profile.id,
            provider=profile.provider,
            model=profile.model,
        )
    except VaultDecryptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/upload", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_db),
    x_llm_profile_id: Optional[str] = Header(None, alias="X-LLM-Profile-ID"),
    x_llm_provider: Optional[str] = Header("deepseek", alias="X-LLM-Provider"),
    x_llm_model: Optional[str] = Header("deepseek-chat", alias="X-LLM-Model")
):
    """Upload and ingest any document into persistent relational storage using LLM semantic reasoning."""
    filename = file.filename or "uploaded_document.txt"
    doc_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{filename}")

    async with aiofiles.open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    display_title = title if title and title.strip() else os.path.splitext(filename)[0].replace("_", " ")
    
    upload_api_key = await _resolve_optional_upload_key(session, request, response, x_llm_profile_id)
    success, message = await process_document_pipeline(
        session=session,
        doc_id=doc_id,
        title=display_title,
        filename=filename,
        file_path=save_path,
        api_key=upload_api_key,
        provider=x_llm_provider or "deepseek",
        model=x_llm_model or "deepseek-chat"
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    doc_repo = DocumentRepository(session)
    doc_dto = await doc_repo.get_document_by_id(doc_id)
    return {"status": "success", "message": message, "document": doc_dto.model_dump() if doc_dto else {}}


@router.get("", response_model=List[DocumentDTO])
async def list_documents(session: AsyncSession = Depends(get_db)):
    """List all persistent uploaded workspace documents and chunk counts."""
    doc_repo = DocumentRepository(session)
    return await doc_repo.list_documents()


@router.get("/graph", response_model=GraphViewDTO)
async def get_workspace_graph(document_id: Optional[str] = None, session: AsyncSession = Depends(get_db)):
    """Retrieve force-directed node-link network graph across all or scoped documents for Obsidian Graph View."""
    graph_repo = GraphRepository(session)
    return await graph_repo.get_document_graph(document_id=document_id)


@router.get("/{document_id}", response_model=DocumentDTO)
async def get_document(document_id: str, session: AsyncSession = Depends(get_db)):
    """Retrieve specific document metadata and Table of Contents (`toc_tree`)."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.get("/{document_id}/graph", response_model=GraphViewDTO)
async def get_single_document_graph(document_id: str, session: AsyncSession = Depends(get_db)):
    """Retrieve Obsidian Graph nodes and edges for a specific document."""
    graph_repo = GraphRepository(session)
    return await graph_repo.get_document_graph(document_id=document_id)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(document_id: str, session: AsyncSession = Depends(get_db)):
    """Delete a document from persistent database tables and disk storage."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        await doc_repo.delete_document(document_id)
        for f in os.listdir(UPLOAD_DIR):
            if f.startswith(document_id):
                os.remove(os.path.join(UPLOAD_DIR, f))
    except Exception as e:
        print(f"[WARN] Error during file deletion for {document_id}: {e}")

    return {"status": "deleted", "document_id": document_id}
