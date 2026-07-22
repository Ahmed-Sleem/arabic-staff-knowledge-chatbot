"""
Tests for Ahmed's enriched curated JSON schema.

WHY: The app now needs to preserve bilingual content, structured connections,
role profiles, KPIs, and trust metadata from the source JSON all the way through
curated graph build, database seeding, repository search, and graph API DTOs.
"""

import json
from pathlib import Path

import pytest

from db.session import init_db, AsyncSessionLocal
from db.repositories import ChunkRepository, GraphRepository
from services.ingestion.build_curated_knowledge import build_curated_knowledge_graph, get_source_json_path
from services.ingestion.seed_curated import seed_curated_knowledge_graph


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_enriched_curated_json_build_and_seed_round_trip():
    source_path = Path(get_source_json_path())
    assert source_path.name == "deepseek_json_20260722_6a33e9.json"

    built = build_curated_knowledge_graph()
    assert built["summary"]["total_nodes"] == 80
    assert built["summary"]["total_connections"] >= 250

    first_chunk = built["chunks"][0]
    metadata = json.loads(first_chunk["metadata_json"])
    assert metadata["name_ar"]
    assert metadata["content_ar"]
    assert isinstance(metadata["connections"], list)

    relation_types = {conn["relationship_type"] for conn in built["connections"]}
    assert "reports_to" in relation_types
    assert "parent_child" in relation_types
    assert "manages" in relation_types

    await init_db()
    async with AsyncSessionLocal() as session:
        assert await seed_curated_knowledge_graph(session) is True

    async with AsyncSessionLocal() as session:
        graph = await GraphRepository(session).get_document_graph()
        assert len(graph.nodes) == 80
        node = next(item for item in graph.nodes if item.id == "10.1")
        assert node.label == "Business Development Manager"
        assert node.label_ar == "مدير تطوير الأعمال"
        assert node.content_ar and "تطوير الأعمال" in node.content_ar
        assert node.role_profile and node.role_profile["reports_to"] == "CEO"
        assert len(node.kpis) >= 1
        assert node.approval_status == "approved"

        ar_results = await ChunkRepository(session).search_chunks("مدير تطوير الأعمال", limit=20)
        assert any(result.chunk_code == "10.1" for result in ar_results)

        kpi_results = await ChunkRepository(session).search_chunks("Opportunity-to-Contract", limit=20)
        assert any(result.chunk_code == "10.1" for result in kpi_results)
