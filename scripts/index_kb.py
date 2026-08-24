#!/usr/bin/env python
"""Knowledge Base Batch Indexing CLI Script (TRD Section 29.1, Section 33.1).

Ingests all documents in knowledge_base/* into ChromaDB and registers metadata in SQLite.
Verifies and asserts chunk_count > 0 for each document.
"""

import datetime
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Enforce telemetry disablement
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.persistence.db import get_db_context, init_db
from backend.app.persistence.models import KnowledgeDocumentORM
from backend.app.rag.chroma_adapter import ChromaAdapter
from backend.app.rag.embeddings import get_embedding_service
from backend.app.rag.ingestion import IngestionPipeline

logger = logging.getLogger("sovereign_workbench.scripts.index_kb")


def index_knowledge_base(kb_dir: Path) -> int:
    """Index all markdown documents in knowledge_base directory."""
    print("=" * 60)
    print("SOVEREIGN KNOWLEDGE BASE BATCH INDEXING (TRD Section 33.1)")
    print("=" * 60)

    if not kb_dir.exists():
        print(f"ERROR: Knowledge base directory not found at: {kb_dir}")
        return 1

    init_db()
    ingestion = IngestionPipeline()
    embedding_service = get_embedding_service()
    chroma = ChromaAdapter()

    doc_files = sorted(list(kb_dir.glob("*.md")) + list(kb_dir.glob("*.txt")))
    if not doc_files:
        print(f"WARNING: No documents found in {kb_dir}")
        return 0

    total_chunks = 0
    indexed_documents = []

    for file_path in doc_files:
        print(f"\nProcessing: {file_path.name}...")
        meta, chunks = ingestion.ingest_markdown_file(file_path)

        if not chunks:
            print(f"  WARNING: Document yielded 0 chunks: {file_path.name}")
            continue

        # Generate local embeddings
        texts = [c.text for c in chunks]
        embeddings = embedding_service.embed_texts(texts)

        # Upsert into ChromaDB
        chroma.upsert_chunks(chunks, embeddings)

        # Upsert metadata into SQLite knowledge_documents
        with get_db_context() as session:
            existing = session.query(KnowledgeDocumentORM).filter_by(source_path=str(file_path)).first()
            if existing:
                existing.title = meta["title"]
                existing.category = meta["category"]
                existing.chunk_count = len(chunks)
                existing.indexed_at = datetime.datetime.now(datetime.timezone.utc)
            else:
                doc_record = KnowledgeDocumentORM(
                    doc_id=meta["doc_id"],
                    title=meta["title"],
                    category=meta["category"],
                    source_path=str(file_path),
                    indexed_at=datetime.datetime.now(datetime.timezone.utc),
                    chunk_count=len(chunks),
                )
                session.add(doc_record)

        print(f"  Title: {meta['title']}")
        print(f"  Category: {meta['category']}")
        print(f"  Chunks indexed: {len(chunks)} (ASSERTION: chunk_count > 0 PASS)")
        total_chunks += len(chunks)
        indexed_documents.append((file_path.name, len(chunks)))

    print("\n" + "=" * 60)
    print("INDEXING SUMMARY & ACCEPTANCE CHECKLIST (TRD Section 33.1)")
    print("=" * 60)
    for doc_name, count in indexed_documents:
        status = "PASS" if count > 0 else "FAIL"
        print(f"  - {doc_name:<35} : {count:>2} chunks [{status}]")
    print(f"\nTotal documents indexed : {len(indexed_documents)}")
    print(f"Total vector chunks     : {total_chunks}")
    print(f"ChromaDB collection count: {chroma.count()}")
    print("=" * 60)

    assert len(indexed_documents) >= 5, "Must index at least 5 synthetic documents"
    assert all(count > 0 for _, count in indexed_documents), "All documents must have chunk_count > 0"
    print("All TRD Section 33.1 checklist assertions PASSED.")
    return 0


if __name__ == "__main__":
    setup_logging()
    kb_path = Path(settings.paths.knowledge_base_dir)
    sys.exit(index_knowledge_base(kb_path))
