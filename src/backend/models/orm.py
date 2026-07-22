"""
Relational ORM Models (`src/backend/models/orm.py`).

Defines multi-document persistence tables for Universal Relational RAG & Obsidian Graph View:
- `DocumentORM` (`documents`): Persistent files, status, and Table of Contents (`toc_tree_json`).
- `ChunkORM` (`chunks`): Dynamic structural sections, headings, text blocks, and table rows.
- `ChunkConnectionORM` (`chunk_connections`): Force-directed Obsidian graph edges linking nodes semantically or hierarchically.
- `DocumentTableORM` (`document_tables`): Structured multi-column relational tables (KPIs, schedules, matrices).
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    """Generate a clean UUID string for primary keys."""
    return str(uuid.uuid4())


class DocumentORM(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), index=True, nullable=False)
    filename = Column(String(255), index=True, nullable=False)
    file_type = Column(String(50), index=True, nullable=False)  # pdf, docx, txt, md
    file_size = Column(Integer, default=0)
    file_path = Column(String(512), nullable=False)
    status = Column(String(50), index=True, default="processing")  # processing, ready, error
    toc_tree_json = Column(Text, default="[]")
    created_at = Column(String(64), default=lambda: datetime.now(timezone.utc).isoformat())

    chunks = relationship("ChunkORM", back_populates="document", cascade="all, delete-orphan")
    connections = relationship("ChunkConnectionORM", back_populates="document", cascade="all, delete-orphan")
    tables = relationship("DocumentTableORM", back_populates="document", cascade="all, delete-orphan")


class ChunkORM(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_code = Column(String(100), index=True, nullable=False)  # e.g., "1.0", "sec_2", "table_row_5"
    title = Column(String(512), index=True, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_type = Column(String(50), index=True, nullable=False)  # heading, text, table, kpi_row, escalation
    parent_chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True, index=True)
    word_count = Column(Integer, default=0)
    metadata_json = Column(Text, default="{}")

    document = relationship("DocumentORM", back_populates="chunks")
    parent = relationship("ChunkORM", remote_side=[id], backref="children")


class ChunkConnectionORM(Base):
    """
    Obsidian Graph Edges (`chunk_connections` table).
    Stores force-directed network links between chunks (parent-child hierarchical edges and semantic concept cross-references).
    """
    __tablename__ = "chunk_connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    source_chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="CASCADE"), index=True, nullable=False)
    target_chunk_id = Column(String(36), ForeignKey("chunks.id", ondelete="CASCADE"), index=True, nullable=False)
    relation_type = Column(String(50), index=True, nullable=False)  # parent_child, semantic_link, cross_reference
    weight = Column(Float, default=1.0)
    explanation = Column(String(512), nullable=True)

    document = relationship("DocumentORM", back_populates="connections")
    source = relationship("ChunkORM", foreign_keys=[source_chunk_id])
    target = relationship("ChunkORM", foreign_keys=[target_chunk_id])


class DocumentTableORM(Base):
    """Structured Multi-Column Tables (`document_tables` table)."""
    __tablename__ = "document_tables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False)
    table_name = Column(String(255), index=True, nullable=False)
    headers_json = Column(Text, default="[]")
    rows_json = Column(Text, default="[]")

    document = relationship("DocumentORM", back_populates="tables")

class VaultProfileORM(Base):
    """
    Device-only encrypted API-key vault profiles.

    WHY: GPR intentionally keeps a no-login UX, so API keys are encrypted server-side
    and scoped to a high-entropy device secret stored in an HttpOnly cookie. The
    database stores only encrypted key material plus non-secret display metadata.
    """
    __tablename__ = "vault_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    device_hash = Column(String(128), index=True, nullable=False)
    label = Column(String(160), nullable=False)
    provider = Column(String(32), index=True, nullable=False)
    model = Column(String(160), nullable=False)
    encrypted_key = Column(Text, nullable=False)
    nonce = Column(String(64), nullable=False)
    key_fingerprint = Column(String(128), index=True, nullable=False)
    key_hint = Column(String(16), nullable=True)
    is_active = Column(Boolean, default=False, index=True)
    created_at = Column(String(64), default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String(64), default=lambda: datetime.now(timezone.utc).isoformat())
    last_used_at = Column(String(64), nullable=True)
