"""
ReAct Retrieval Tools (`src/backend/agent/tools.py`).

Provides structural relational retrieval functions for the DeepSeek ReAct agent without vector DB embeddings:
- `search_chunks`: Bilingual keyword search over `ChunkRepository`.
- `get_table`: Retrieves multi-column relational tables (`DocumentTableRepository`).
- `get_chunk_relations`: Retrieves parent-child and semantic links (`GraphRepository` / `ChunkConnectionORM`).
- `get_document_toc`: Retrieves hierarchical Table of Contents (`toc_tree`).
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
try:
    from ...db.repositories import ChunkRepository, TableRepository, DocumentRepository
    from ...models.orm import ChunkConnectionORM, ChunkORM
    from ...models.domain import ChunkDTO
except ImportError:
    from db.repositories import ChunkRepository, TableRepository, DocumentRepository
    from models.orm import ChunkConnectionORM, ChunkORM
    from models.domain import ChunkDTO


def list_agent_tools(language: str = "ar") -> List[Dict[str, Any]]:
    """Return OpenAI-compatible function tool definitions (`type: 'function'`)."""
    is_ar = language.lower() == "ar"
    return [
        {
            "type": "function",
            "function": {
                "name": "search_chunks",
                "description": "البحث بالكلمات المفتاحية في مقاطع ونصوص المستندات المعتمدة (عربي أو إنجليزي)" if is_ar else "Keyword search across approved document chunks and text sections (Arabic or English)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "كلمات البحث أو المصطلحات (مثال: 'حوادث السلامة', 'TRIR', 'صلاحيات الرئيس')" if is_ar else "Search query keywords (e.g. 'Safety incidents', 'TRIR', 'CEO authority')"
                        },
                        "document_id": {
                            "type": "string",
                            "description": "معرف المستند إن وجد، أو فارغ للبحث في جميع المستندات" if is_ar else "Document UUID if scoped, or empty to search across all workspace documents"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_table",
                "description": "استرجاع جداول البيانات أو مؤشرات الأداء (KPIs) أو مصفوفة التصعيد" if is_ar else "Retrieve extracted data tables, KPI matrices, or administrative escalation schedules",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "اسم أو جزء من عنوان الجدول (مثال: 'PMO', 'مؤشرات الأداء', 'التصعيد')" if is_ar else "Table title substring (e.g. 'PMO', 'KPI', 'Escalation')"
                        },
                        "document_id": {
                            "type": "string",
                            "description": "معرف المستند إن وجد" if is_ar else "Document UUID if scoped"
                        }
                    },
                    "required": ["table_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_chunk_relations",
                "description": "استرجاع المقاطع المرتبطة دلالياً أو هرمياً بمقطع محدد من أجل التوسعة في الفهم" if is_ar else "Retrieve connected parent, child, or semantic cross-reference chunks for a given chunk UUID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chunk_id": {
                            "type": "string",
                            "description": "معرف المقطع (UUID)" if is_ar else "Chunk UUID"
                        }
                    },
                    "required": ["chunk_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_document_toc",
                "description": "استرجاع فهرس المحتويات الكامل والهيكل الإداري للمستند" if is_ar else "Retrieve the full Table of Contents hierarchy and structural outline of a document",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "معرف المستند" if is_ar else "Document UUID"
                        }
                    },
                    "required": ["document_id"]
                }
            }
        }
    ]


async def execute_agent_tool(session: AsyncSession, tool_name: str, arguments: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Execute the requested tool against relational repositories.
    Returns `(result_json_str, active_node_ids)` where `active_node_ids` are chunk IDs activated on the Obsidian Graph!
    """
    active_node_ids: List[str] = []

    if tool_name == "search_chunks":
        query = arguments.get("query", "").strip()
        doc_id = arguments.get("document_id") or None
        chunk_repo = ChunkRepository(session)
        chunks = await chunk_repo.search_chunks(query=query, document_id=doc_id, limit=6)
        active_node_ids = [c.id for c in chunks]
        results = [
            {
                "id": c.id,
                "code": c.chunk_code,
                "title": c.title,
                "content": c.content[:600] + ("..." if len(c.content) > 600 else ""),
                "page": c.page_number
            }
            for c in chunks
        ]
        return json.dumps({"query": query, "retrieved_count": len(results), "chunks": results}, ensure_ascii=False), active_node_ids

    elif tool_name == "get_table":
        table_name = arguments.get("table_name", "").strip().lower()
        doc_id = arguments.get("document_id") or None
        table_repo = TableRepository(session)
        
        # If doc_id specified, list for that doc; otherwise search across chunks for table blocks
        stmt = select(ChunkORM).where(ChunkORM.chunk_type == "table")
        if doc_id:
            stmt = stmt.where(ChunkORM.document_id == doc_id)
        if table_name:
            stmt = stmt.where(ChunkORM.title.ilike(f"%{table_name}%"))
        
        result = await session.execute(stmt.limit(4))
        table_chunks = result.scalars().all()
        active_node_ids = [c.id for c in table_chunks]
        results = [
            {
                "id": c.id,
                "title": c.title,
                "table_content": c.content,
                "page": c.page_number
            }
            for c in table_chunks
        ]
        return json.dumps({"table_query": table_name, "tables_found": len(results), "tables": results}, ensure_ascii=False), active_node_ids

    elif tool_name == "get_chunk_relations":
        chunk_id = arguments.get("chunk_id", "").strip()
        stmt = select(ChunkConnectionORM).where(
            (ChunkConnectionORM.source_chunk_id == chunk_id) | (ChunkConnectionORM.target_chunk_id == chunk_id)
        ).limit(8)
        result = await session.execute(stmt)
        connections = result.scalars().all()
        
        connected_ids = set()
        for conn in connections:
            connected_ids.add(conn.source_chunk_id)
            connected_ids.add(conn.target_chunk_id)
        active_node_ids = list(connected_ids)

        # Fetch chunk details for connected nodes
        if connected_ids:
            chunk_stmt = select(ChunkORM).where(ChunkORM.id.in_(list(connected_ids)))
            c_result = await session.execute(chunk_stmt)
            c_items = c_result.scalars().all()
        else:
            c_items = []

        results = [
            {
                "id": c.id,
                "code": c.chunk_code,
                "title": c.title,
                "preview": c.content[:200]
            }
            for c in c_items
        ]
        return json.dumps({"chunk_id": chunk_id, "relations_count": len(results), "connected_chunks": results}, ensure_ascii=False), active_node_ids

    elif tool_name == "get_document_toc":
        doc_id = arguments.get("document_id", "").strip()
        doc_repo = DocumentRepository(session)
        doc = await doc_repo.get_document_by_id(doc_id)
        if not doc:
            return json.dumps({"error": "Document not found"}, ensure_ascii=False), []
        
        # Collect top-level TOC node IDs
        top_ids = [node.id for node in doc.toc_tree[:10]]
        return json.dumps({"document_title": doc.title, "toc_tree": [n.model_dump() for n in doc.toc_tree]}, ensure_ascii=False), top_ids

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False), []
