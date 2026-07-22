"""
Domain DTO Schemas (`src/backend/models/domain.py`).

Defines Pydantic data validation and serialization schemas for Universal Relational RAG & Obsidian Graph View:
- Document metadata (`DocumentDTO`) and TOC structures (`TOCTreeNode`).
- Structural chunks (`ChunkDTO`) and extracted tables (`DocumentTableDTO`).
- Obsidian Graph nodes (`GraphNodeDTO`), links (`GraphLinkDTO`), and full view payload (`GraphViewDTO`).
"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TOCTreeNode(BaseModel):
    id: str = Field(..., description="Unique chunk/section ID")
    code: str = Field(..., description="Structural hierarchy code (e.g. '1.0', 'sec_1')")
    title: str = Field(..., description="Heading or summary title")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    children: List["TOCTreeNode"] = []


TOCTreeNode.model_rebuild()


class ChunkDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Chunk unique UUID")
    document_id: str = Field(..., description="Parent document UUID")
    chunk_code: str = Field(..., description="Hierarchy or sequence code")
    title: str = Field(..., description="Concise title or section header")
    content: str = Field(..., description="Full cleaned text/table data")
    page_number: Optional[int] = Field(None, description="Page number")
    chunk_type: str = Field(..., description="heading, text, table, kpi_row, or escalation")
    parent_chunk_id: Optional[str] = Field(None, description="Parent chunk UUID")
    word_count: int = Field(..., description="Word count")
    metadata_json: str = Field("{}", description="Enriched node metadata JSON")


class ChunkConnectionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Connection edge UUID")
    document_id: str = Field(..., description="Parent document UUID")
    source_chunk_id: str = Field(..., description="Source node chunk UUID")
    target_chunk_id: str = Field(..., description="Target node chunk UUID")
    relation_type: str = Field(..., description="parent_child, semantic_link, or cross_reference")
    weight: float = Field(1.0, description="Connection strength weight")
    explanation: Optional[str] = Field(None, description="Reason for edge connection")


class DocumentTableDTO(BaseModel):
    id: str = Field(..., description="Table UUID")
    document_id: str = Field(..., description="Parent document UUID")
    table_name: str = Field(..., description="Table title or header")
    headers: List[str] = Field(..., description="List of column headers")
    rows: List[List[str]] = Field(..., description="List of rows (each row is a list of cell strings)")


class DocumentDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Document unique UUID")
    title: str = Field(..., description="Document display title")
    filename: str = Field(..., description="Original uploaded filename")
    file_type: str = Field(..., description="pdf, docx, txt, md")
    file_size: int = Field(..., description="File size in bytes")
    status: str = Field(..., description="processing, ready, or error")
    toc_tree: List[TOCTreeNode] = Field(..., description="Hierarchical Table of Contents tree")
    created_at: str = Field(..., description="ISO creation timestamp")
    chunk_count: int = Field(0, description="Total extracted chunks")


# --- Obsidian Graph View Payload (`GraphViewDTO`) ---

class GraphNodeDTO(BaseModel):
    id: str = Field(..., description="Node UUID matching `ChunkORM.id`")
    label: str = Field(..., description="Display title on the Obsidian canvas")
    label_ar: Optional[str] = Field(None, description="Arabic display title when available")
    group: str = Field(..., description="Node group matching `chunk_type` for color coding")
    val: float = Field(..., description="Node size weight based on word count or hierarchy level")
    content_preview: str = Field(..., description="First 150 characters of chunk text for hover tooltips")
    content: str = Field("", description="Full complete protected English content of the node")
    content_ar: Optional[str] = Field(None, description="Full complete protected Arabic content of the node")
    description: Optional[str] = Field(None, description="English short description")
    description_ar: Optional[str] = Field(None, description="Arabic short description")
    aliases: List[str] = Field(default=[], description="Search aliases")
    keywords_ar: List[str] = Field(default=[], description="Arabic search keywords")
    keywords_en: List[str] = Field(default=[], description="English search keywords")
    role_profile: Optional[dict] = Field(None, description="Structured role profile metadata")
    kpis: List[dict] = Field(default=[], description="Structured KPI metadata")
    answerable_questions: List[str] = Field(default=[], description="Questions this node can answer")
    not_answered_here: List[str] = Field(default=[], description="Boundaries for unsupported questions")
    approval_status: Optional[str] = Field(None, description="Approval status")
    last_verified: Optional[str] = Field(None, description="Last verification date")
    confidence: Optional[str] = Field(None, description="Curator confidence")
    connections: List[dict | str] = Field(default=[], description="Connected target node IDs or enriched connection objects")
    page_number: Optional[int] = Field(None, description="Page number")


class GraphLinkDTO(BaseModel):
    id: str = Field(..., description="Edge UUID matching `ChunkConnectionORM.id`")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: str = Field(..., description="Relation type or explanation")
    value: float = Field(..., description="Edge thickness weight")


class GraphViewDTO(BaseModel):
    document_id: Optional[str] = Field(None, description="Filter by document or None for all-documents workspace graph")
    nodes: List[GraphNodeDTO] = []
    links: List[GraphLinkDTO] = []
