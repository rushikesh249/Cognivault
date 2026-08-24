"""Unit tests for RAG Retrieval, Similarity Thresholds, and Citations (TRD Section 16.2, Section 16.3, Table 37, Table 38)."""

from typing import List
import pytest
from backend.app.rag.embeddings import DeterministicTestEmbeddingService
from backend.app.rag.ingestion import DocumentChunk
from backend.app.services.rag_service import RAGService


class MockChromaAdapter:
    """In-memory mock Chroma adapter for pure unit testing without disk I/O."""

    def __init__(self, mock_matches: List[dict]):
        self._matches = mock_matches

    def count(self) -> int:
        return len(self._matches)

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[dict]:
        return self._matches[:top_k]


def test_threshold_filter_drops_below_055():
    """Verify chunks with score < 0.55 are dropped (TRD Table 37, Table 38)."""
    mock_candidates = [
        {
            "chunk_id": "c1",
            "text": "Emergency shutdown Level 1 isolates fuel valves.",
            "source_document": "safety_sop.md",
            "section": "1.1 Process Unit Emergency Shutdown",
            "page": 1,
            "score": 0.88,
        },
        {
            "chunk_id": "c2",
            "text": "ESD override requires written authorization.",
            "source_document": "safety_sop.md",
            "section": "1.2 Manual Override Requirements",
            "page": 1,
            "score": 0.55,
        },
        {
            "chunk_id": "c3",
            "text": "Centrifugal pump vibration baseline is 2.8 mm/s.",
            "source_document": "maintenance_manual.md",
            "section": "1.1 Vibration Baseline",
            "page": 1,
            "score": 0.54,
        },
        {
            "chunk_id": "c4",
            "text": "Irrelevant casual chat statement.",
            "source_document": "random.md",
            "section": "General",
            "page": 1,
            "score": 0.12,
        },
    ]

    adapter = MockChromaAdapter(mock_candidates)
    emb_service = DeterministicTestEmbeddingService(dimension=384)
    service = RAGService(embedding_service=emb_service, chroma_adapter=adapter)

    results = service.search("emergency shutdown procedures", top_k=5)
    
    assert len(results) == 2
    assert results[0]["source_document"] == "safety_sop.md"
    assert results[0]["score"] == 0.88
    assert results[1]["score"] == 0.55
    scores = [r["score"] for r in results]
    assert all(s >= 0.55 for s in scores)


def test_citation_format_matches_trd_table_38():
    """Verify citation format is '{document_title} - {section} (p.{page})' (TRD Table 38)."""
    mock_candidates = [
        {
            "chunk_id": "c1",
            "text": "Chemical handling PPE requires butyl rubber gloves.",
            "source_document": "safety_sop.md",
            "section": "2.3 Chemical Handling PPE",
            "page": 1,
            "score": 0.76,
        }
    ]

    adapter = MockChromaAdapter(mock_candidates)
    emb_service = DeterministicTestEmbeddingService(dimension=384)
    service = RAGService(embedding_service=emb_service, chroma_adapter=adapter)

    results = service.search("chemical PPE requirements", top_k=5)
    assert len(results) == 1
    assert results[0]["citation"] == "safety_sop.md - 2.3 Chemical Handling PPE (p.1)"


def test_empty_index_returns_empty_result():
    """Verify empty vector index returns empty list without exception (TRD Component #8 failure mode)."""
    adapter = MockChromaAdapter([])
    emb_service = DeterministicTestEmbeddingService(dimension=384)
    service = RAGService(embedding_service=emb_service, chroma_adapter=adapter)

    results = service.search("anything", top_k=5)
    assert results == []


def test_empty_query_raises_validation_error():
    """Verify empty or whitespace query is rejected with ValueError."""
    adapter = MockChromaAdapter([])
    emb_service = DeterministicTestEmbeddingService(dimension=384)
    service = RAGService(embedding_service=emb_service, chroma_adapter=adapter)

    with pytest.raises(ValueError):
        service.search("", top_k=5)

    with pytest.raises(ValueError):
        service.search("   ", top_k=5)
