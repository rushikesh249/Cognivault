"""ChromaDB Persistent Client Adapter (TRD Section 16.1, Component #11, ADR-006).

Strictly enforces local persistence at data/chroma/ and zero telemetry transmission.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Enforce telemetry disablement before importing chromadb
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings as ChromaClientSettings

from backend.app.core.config import settings
from backend.app.rag.ingestion import DocumentChunk

logger = logging.getLogger("sovereign_workbench.rag.chroma")


class ChromaAdapter:
    """Persistent local ChromaDB adapter (TRD Section 16.1, Table 36)."""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        self.persist_directory = persist_directory or str(settings.paths.data_dir / "chroma")
        self.collection_name = collection_name or settings.rag.collection_name
        
        # Ensure persistence directory exists
        path = Path(self.persist_directory)
        path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB PersistentClient at: {self.persist_directory}")
        
        # Initialize client with telemetry disabled
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=ChromaClientSettings(
                anonymized_telemetry=False,
                is_persistent=True,
            ),
        )
        self._collection = None

    def get_collection(self):
        """Retrieve or create the knowledge_base collection with cosine distance."""
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def upsert_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> int:
        """Upsert a list of document chunks and their embedding vectors into ChromaDB."""
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) and embedding count ({len(embeddings)}) mismatch")

        collection = self.get_collection()
        
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "source_document": c.source_document,
                "section": c.section,
                "page": c.page,
                "token_count": c.token_count,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Upserted {len(chunks)} chunks into collection '{self.collection_name}'")
        return len(chunks)

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform cosine similarity query against the vector index."""
        collection = self.get_collection()
        count = collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            include=["documents", "metadatas", "distances"],
        )

        matches: List[Dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return matches

        ids = results["ids"][0]
        docs = results["documents"][0] if results["documents"] else [""] * len(ids)
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
        distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)

        for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
            score = max(0.0, min(1.0, 1.0 - float(dist)))
            matches.append({
                "chunk_id": chunk_id,
                "text": text,
                "source_document": meta.get("source_document", "Unknown"),
                "section": meta.get("section", "General"),
                "page": int(meta.get("page", 1)),
                "doc_id": meta.get("doc_id", ""),
                "distance": float(dist),
                "score": round(score, 4),
            })

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    def count(self) -> int:
        """Return total number of chunks stored in the collection."""
        return self.get_collection().count()

    def reset(self):
        """Reset and clear collection."""
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = None
