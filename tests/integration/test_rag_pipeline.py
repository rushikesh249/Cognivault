"""Integration tests for the full Sovereign RAG Pipeline (TRD Section 16.1-16.3, Section 27.2, Test Plan P20-22)."""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.main import app
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.models import KnowledgeDocumentORM
from backend.app.rag.chroma_adapter import ChromaAdapter
from backend.app.rag.embeddings import DeterministicTestEmbeddingService
from backend.app.rag.ingestion import IngestionPipeline
from backend.app.services.rag_service import RAGService


@pytest.fixture(scope="module")
def setup_test_rag_environment(tmp_path_factory):
    """Set up temporary ChromaDB and ingest the 5 synthetic knowledge base documents."""
    temp_dir = tmp_path_factory.mktemp("test_rag_data")
    chroma_dir = str(temp_dir / "chroma")
    
    init_db()

    ingestion = IngestionPipeline()
    emb_service = DeterministicTestEmbeddingService(dimension=384)
    chroma = ChromaAdapter(persist_directory=chroma_dir, collection_name="test_knowledge_base")
    chroma.reset()

    kb_dir = Path("knowledge_base")
    doc_files = list(kb_dir.glob("*.md"))
    assert len(doc_files) >= 5, "Synthetic knowledge base must contain at least 5 documents"

    for file_path in doc_files:
        meta, chunks = ingestion.ingest_markdown_file(file_path)
        assert len(chunks) > 0, f"Document {file_path.name} must have chunk_count > 0"
        
        texts = [c.text for c in chunks]
        embeddings = emb_service.embed_texts(texts)
        chroma.upsert_chunks(chunks, embeddings)

        with get_db_context() as session:
            existing = session.query(KnowledgeDocumentORM).filter_by(source_path=str(file_path)).first()
            if existing:
                existing.chunk_count = len(chunks)
            else:
                doc_record = KnowledgeDocumentORM(
                    doc_id=meta["doc_id"],
                    title=meta["title"],
                    category=meta["category"],
                    source_path=str(file_path),
                    chunk_count=len(chunks),
                )
                session.add(doc_record)

    rag_service = RAGService(embedding_service=emb_service, chroma_adapter=chroma)
    return {
        "rag_service": rag_service,
        "chroma": chroma,
        "doc_count": len(doc_files),
    }


def test_synthetic_documents_ingested_and_chunk_count_positive(setup_test_rag_environment):
    """Verify all 5 synthetic documents are indexed with chunk_count > 0 (TRD Section 33.1)."""
    env = setup_test_rag_environment
    chroma = env["chroma"]
    assert chroma.count() > 0

    with get_db_context() as session:
        records = session.query(KnowledgeDocumentORM).all()
        assert len(records) >= 5
        for r in records:
            assert r.chunk_count > 0
            assert r.category in ("sop", "manual", "guideline", "standard", "approval_note")


def test_telemetry_strictly_disabled():
    """Verify ChromaDB telemetry is disabled (Sovereignty constraint)."""
    assert os.environ.get("ANONYMIZED_TELEMETRY") == "False"
    assert settings.rag.chroma.anonymized_telemetry is False


def test_api_knowledge_search_success(setup_test_rag_environment, monkeypatch):
    """Verify POST /api/knowledge/search returns 200 OK and valid matches (TRD Table 15)."""
    env = setup_test_rag_environment
    rag_service = env["rag_service"]

    from backend.app.api.knowledge import get_rag_service
    app.dependency_overrides[get_rag_service] = lambda: rag_service

    client = TestClient(app)
    response = client.post("/api/knowledge/search", json={"query": "Emergency shutdown ESD procedures", "top_k": 5})
    
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert isinstance(data["matches"], list)
    
    if data["matches"]:
        match = data["matches"][0]
        assert "text" in match
        assert "source_document" in match
        assert "section" in match
        assert "score" in match
        assert "page" in match
        assert match["page"] == 1
        assert match["score"] >= 0.55

    app.dependency_overrides.clear()


def test_api_knowledge_search_empty_query_returns_422():
    """Verify POST /api/knowledge/search returns 422 for empty query (TRD Table 15)."""
    client = TestClient(app)
    response = client.post("/api/knowledge/search", json={"query": "", "top_k": 5})
    assert response.status_code == 422

    response2 = client.post("/api/knowledge/search", json={"query": "   ", "top_k": 5})
    assert response2.status_code == 422
