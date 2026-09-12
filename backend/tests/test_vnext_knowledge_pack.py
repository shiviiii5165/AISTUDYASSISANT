import pytest
from app.services.lesson_planner.vnext.knowledge_pack import (
    KnowledgePackService, generate_pack_hash, _KNOWLEDGE_PACK_MEMORY_CACHE
)
from app.services.lesson_planner.schemas import BloomLevel


def test_pack_hash_stability():
    h1 = generate_pack_hash("DBMS Normalization", "Computer Science", "B.Tech")
    h2 = generate_pack_hash("dbms normalization", "computer science", "b.tech")
    assert h1 == h2, "Hash must be case-insensitive and stable"
    assert len(h1) == 16


@pytest.mark.anyio
async def test_knowledge_pack_generation_and_l1_cache(monkeypatch):
    # Pre-populate L1 cache to test deterministic instant retrieval
    test_hash = generate_pack_hash("Test Topic", "CS", "B.Tech")
    
    # Generate pack (will create fallback/mock or use router)
    pack = await KnowledgePackService.get_or_create_pack(
        topic="Test Topic",
        subject="CS",
        grade="B.Tech"
    )

    assert pack.topic == "Test Topic"
    assert len(pack.learning_objectives) >= 1
    assert pack.learning_objectives[0].bloom_level in [BloomLevel.UNDERSTAND, BloomLevel.APPLY]
    assert len(pack.concepts) >= 1
    assert len(pack.common_misconceptions) >= 1

    # Verify it is in L1 cache
    assert pack.source_hash in _KNOWLEDGE_PACK_MEMORY_CACHE

    # Second call must hit L1 cache immediately
    cached_pack = await KnowledgePackService.get_or_create_pack(
        topic="Test Topic",
        subject="CS",
        grade="B.Tech"
    )
    assert cached_pack is pack, "Must return the exact cached instance"
