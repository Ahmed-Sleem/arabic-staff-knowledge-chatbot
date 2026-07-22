"""
Database Seeding Engine for Curated Knowledge Graph (`seed_curated.py`).

Loads the active curated, high-density self-contained semantic cards from `curated_knowledge_graph.json`
into persistent relational tables (`DocumentORM`, `ChunkORM`, `ChunkConnectionORM`),
replacing any legacy fragmented line chunks (`Rule 21`, `Rule 26`).
"""

import os
import json
import asyncio
from sqlalchemy import select, delete
try:
    from ...db.session import AsyncSessionLocal, init_db
    from ...models.orm import DocumentORM, ChunkORM, ChunkConnectionORM
except ImportError:
    from db.session import AsyncSessionLocal, init_db
    from models.orm import DocumentORM, ChunkORM, ChunkConnectionORM

def get_curated_json_path() -> str:
    """Resolve built curated JSON path across local workspace or container (`/app`)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    candidates = [
        os.path.join(base_dir, "data", "curated_knowledge_graph.json"),
        os.path.abspath("src/backend/data/curated_knowledge_graph.json"),
        "/app/src/backend/data/curated_knowledge_graph.json"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(base_dir, "data", "curated_knowledge_graph.json")


async def seed_curated_knowledge_graph(session=None) -> bool:
    """Load and seed the exact golden 80-node dataset into `gpr_workspace.db`."""
    try:
        try:
            from .build_curated_knowledge import build_curated_knowledge_graph
        except ImportError:
            from services.ingestion.build_curated_knowledge import build_curated_knowledge_graph
        build_curated_knowledge_graph()
    except Exception as e:
        print(f"[GPR ERROR] Failed to build curated knowledge graph: {e}")

    curated_path = get_curated_json_path()
    if not os.path.exists(curated_path):
        print(f"[GPR ERROR] Curated JSON not found at {curated_path}")
        return False

    with open(curated_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc_meta = data["document"]
    chunks_list = data["chunks"]
    connections_list = data["connections"]

    close_session = False
    if session is None:
        await init_db()
        session = AsyncSessionLocal()
        close_session = True

    try:
        # Check if the document already exists or if we need to replace legacy fragmented records
        doc_id = doc_meta["id"]
        
        # Cleanly wipe all existing chunks and connections to guarantee 0 fragmented line chunks in the workspace
        await session.execute(delete(ChunkConnectionORM))
        await session.execute(delete(ChunkORM))
        await session.execute(delete(DocumentORM))

        # Insert official DocumentORM
        doc_orm = DocumentORM(
            id=doc_id,
            title=doc_meta["title"],
            filename=doc_meta["filename"],
            file_type=doc_meta["file_type"],
            file_size=doc_meta["file_size"],
            file_path=os.path.abspath("sample_manuals/hr_source.pdf"),
            status=doc_meta["status"],
            toc_tree_json=json.dumps(doc_meta["toc_tree"], ensure_ascii=False) if isinstance(doc_meta["toc_tree"], list) else doc_meta["toc_tree"],
            created_at=doc_meta.get("created_at", "2026-07-20T10:00:00Z")
        )
        session.add(doc_orm)
        await session.flush()

        # Insert official ChunkORM records
        for c in chunks_list:
            chunk_orm = ChunkORM(
                id=c["id"],
                document_id=doc_id,
                chunk_code=c["chunk_code"],
                title=c["title"],
                content=c["content"],
                page_number=c["page_number"],
                chunk_type=c["chunk_type"],
                parent_chunk_id=c["parent_chunk_id"],
                word_count=len(c["content"].split()),
                metadata_json=c.get("metadata_json", "{}")
            )
            session.add(chunk_orm)
        await session.flush()

        # Insert ChunkConnectionORM records
        for conn in connections_list:
            conn_orm = ChunkConnectionORM(
                id=conn["id"],
                document_id=doc_id,
                source_chunk_id=conn["source_chunk_id"],
                target_chunk_id=conn["target_chunk_id"],
                relation_type=conn.get("relationship_type") or conn.get("relation_type") or "semantic_link",
                weight=float(conn.get("strength", 1.0)),
                explanation=conn.get("explanation") or conn.get("reason") or conn.get("evidence")
            )
            session.add(conn_orm)

        await session.commit()
        print(f"[GPR INFO] Successfully seeded {len(chunks_list)} rich semantic chunks and {len(connections_list)} graph connections.")
        return True
    except Exception as e:
        await session.rollback()
        print(f"[GPR ERROR] Error seeding curated knowledge graph: {e}")
        return False
    finally:
        if close_session:
            await session.close()


if __name__ == "__main__":
    asyncio.run(seed_curated_knowledge_graph())
