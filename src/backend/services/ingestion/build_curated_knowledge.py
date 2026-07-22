"""
Master Curated Knowledge Graph Builder (`build_curated_knowledge.py`).

WHY: The production GPR graph is generated from Ahmed's manually curated JSON
source. The source schema now supports bilingual content, structured role/KPI
metadata, and typed graph connections, while older string-only connections must
remain backward-compatible for historical files.
"""

import os
import json
import uuid
from typing import List, Dict, Any, Iterable, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CURATED_OUT_PATH = os.path.join(DATA_DIR, "curated_knowledge_graph.json")
ACTIVE_SOURCE_FILENAME = "deepseek_json_20260722_6a33e9.json"
LEGACY_SOURCE_FILENAME = "deepseek_json_20260720_7bf464.json"


def _candidate_paths(filename: str) -> List[str]:
    return [
        os.path.join(DATA_DIR, filename),
        os.path.abspath(os.path.join("uploads", filename)),
        os.path.abspath(os.path.join("src", "backend", "data", filename)),
        os.path.join("/app", "src", "backend", "data", filename),
        os.path.join("/app", "seed_data", "backend_data", filename),
    ]


def get_source_json_path() -> str:
    """Resolve the active enriched source JSON path across local workspace or container (`/app`)."""
    for filename in (ACTIVE_SOURCE_FILENAME, LEGACY_SOURCE_FILENAME):
        for candidate in _candidate_paths(filename):
            if os.path.exists(candidate):
                return candidate
    return os.path.join(DATA_DIR, ACTIVE_SOURCE_FILENAME)


def generate_stable_uuid(code: str) -> str:
    """Generate a deterministic UUID v5 from unique edge code."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"gpr.workspace.sample.{code}"))


def _load_nodes(source_path: str) -> List[Dict[str, Any]]:
    with open(source_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    if isinstance(raw, dict) and isinstance(raw.get("nodes"), list):
        raw_items = raw["nodes"]
    elif isinstance(raw, list):
        raw_items = raw
    else:
        raise ValueError("Golden dataset must be a list or an object with a `nodes` list.")
    return [item for item in raw_items if isinstance(item, dict) and item.get("id")]


def _normalize_connections(node_id: str, raw_connections: Any, valid_ids: set[str], parent_id: str | None) -> Iterable[Tuple[str, str, float, str]]:
    """Yield `(target_id, relation_type, strength, explanation)` for old and enriched connection schemas."""
    if isinstance(raw_connections, str):
        try:
            raw_connections = json.loads(raw_connections)
        except Exception:
            raw_connections = []
    if not isinstance(raw_connections, list):
        raw_connections = []

    for conn in raw_connections:
        if isinstance(conn, dict):
            target_id = str(conn.get("target_id") or conn.get("target") or conn.get("id") or "").strip()
            relation_type = str(conn.get("relation_type") or conn.get("relationship_type") or "semantic_link").strip() or "semantic_link"
            reason = str(conn.get("reason") or conn.get("evidence") or conn.get("explanation") or "").strip()
            try:
                strength = float(conn.get("strength", 1.0))
            except Exception:
                strength = 1.0
        else:
            target_id = str(conn).strip()
            relation_type = "parent_child" if target_id == parent_id else "semantic_link"
            reason = "Legacy connection from curated source."
            strength = 1.0
        if target_id and target_id in valid_ids and target_id != node_id:
            yield target_id, relation_type, max(0.0, min(strength, 1.0)), reason


def _metadata_for_node(item: Dict[str, Any]) -> Dict[str, Any]:
    """Preserve enriched node metadata for graph API, search, drawer, and prompts."""
    metadata_fields = [
        "name_ar",
        "short_description",
        "short_description_ar",
        "content_ar",
        "section_path",
        "aliases",
        "keywords_ar",
        "keywords_en",
        "connections",
        "answerable_questions",
        "not_answered_here",
        "role_profile",
        "kpis",
        "approval_status",
        "last_verified",
        "confidence",
    ]
    return {field: item.get(field) for field in metadata_fields if item.get(field) is not None}


def build_curated_knowledge_graph() -> Dict[str, Any]:
    source_path = get_source_json_path()
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source golden dataset not found at {source_path}")

    raw_items = _load_nodes(source_path)
    doc_id = "HR-MANUAL-V1"
    document_meta = {
        "id": doc_id,
        "title": "Sample Organization Approved Organizational Structure Guide v1.0",
        "filename": "hr_source.pdf",
        "file_type": "pdf",
        "file_size": 1828800,
        "status": "ready",
        "created_at": "2026-07-20T10:00:00Z",
        "source_json": os.path.basename(source_path),
    }

    chunks: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []
    toc_tree: List[Dict[str, Any]] = []
    valid_ids = {str(item.get("id")).strip() for item in raw_items if item.get("id")}

    for item in raw_items:
        node_id = str(item.get("id")).strip()
        if not node_id:
            continue

        name = str(item.get("name") or node_id).strip()
        short_desc = str(item.get("short_description") or "").strip()
        section_path = item.get("section_path", []) if isinstance(item.get("section_path"), list) else []
        content = str(item.get("content") or "").strip()
        metadata = _metadata_for_node(item)

        parent_id = None
        if "." in node_id:
            candidate_parent = ".".join(node_id.split(".")[:-1])
            if candidate_parent in valid_ids:
                parent_id = candidate_parent

        page_num = 1
        try:
            page_num = int(node_id.split(".")[0])
        except Exception:
            pass

        chunks.append({
            "id": node_id,
            "document_id": doc_id,
            "chunk_code": node_id,
            "title": name,
            "content": content,
            "page_number": page_num,
            "chunk_type": "text" if "." in node_id else "heading",
            "parent_chunk_id": parent_id,
            "word_count": len(content.split()),
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        })

        toc_tree.append({
            "id": node_id,
            "name": name,
            "name_ar": item.get("name_ar"),
            "short_description": short_desc,
            "short_description_ar": item.get("short_description_ar"),
            "section_path": section_path,
            "connections": item.get("connections", []),
            "aliases": item.get("aliases", []),
            "keywords_ar": item.get("keywords_ar", []),
            "keywords_en": item.get("keywords_en", []),
            "approval_status": item.get("approval_status"),
            "last_verified": item.get("last_verified"),
            "confidence": item.get("confidence"),
        })

        for target_id, relation_type, strength, reason in _normalize_connections(node_id, item.get("connections", []), valid_ids, parent_id):
            connections.append({
                "id": generate_stable_uuid(f"CONN-{node_id}-{target_id}-{relation_type}"),
                "source_chunk_id": node_id,
                "target_chunk_id": target_id,
                "relationship_type": relation_type,
                "strength": strength,
                "explanation": reason,
            })

    document_meta["chunk_count"] = len(chunks)
    document_meta["toc_tree"] = toc_tree

    result = {
        "document": document_meta,
        "chunks": chunks,
        "connections": connections,
        "summary": {
            "total_nodes": len(chunks),
            "total_connections": len(connections),
            "toc_tree_size": len(toc_tree),
            "source_json": os.path.basename(source_path),
        }
    }

    os.makedirs(os.path.dirname(CURATED_OUT_PATH), exist_ok=True)
    with open(CURATED_OUT_PATH, "w", encoding="utf-8") as f_out:
        json.dump(result, f_out, ensure_ascii=False, indent=2)

    print(f"[GPR INFO] Successfully built golden curated graph from {source_path}")
    print(f"[GPR INFO] Summary: {result['summary']}")
    return result


if __name__ == "__main__":
    build_curated_knowledge_graph()
