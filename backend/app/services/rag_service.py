"""RAG Engine / Orchestration Service (TRD Section 16.2, Component #8, Table 37)."""

import logging
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.rag.chroma_adapter import ChromaAdapter
from backend.app.rag.embeddings import BaseEmbeddingService, get_embedding_service

logger = logging.getLogger("sovereign_workbench.services.rag")


class RAGService:
    """Orchestrates semantic retrieval and threshold filtering (TRD Table 37)."""

    def __init__(
        self,
        embedding_service: Optional[BaseEmbeddingService] = None,
        chroma_adapter: Optional[ChromaAdapter] = None,
    ):
        self.embedding_service = embedding_service or get_embedding_service()
        self.chroma_adapter = chroma_adapter or ChromaAdapter()

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge base chunks above similarity threshold.
        
        Data flow (TRD Table 37):
        Query -> Embed (symmetric BGE) -> ChromaDB Cosine Search -> Threshold Filter (score >= 0.55) -> Formatted Output.
        """
        cleaned_query = query.strip() if query else ""
        if not cleaned_query:
            raise ValueError("Query string must not be empty or whitespace only")

        if self.chroma_adapter.count() == 0:
            logger.warning("Knowledge Base index is empty. Returning 0 matches.")
            return []

        limit = top_k or settings.rag.top_k
        threshold = settings.rag.similarity_threshold

        # Step 1: Symmetric query embedding
        query_vector = self.embedding_service.embed_query(cleaned_query)

        # Step 2: Vector search in ChromaDB
        raw_matches = self.chroma_adapter.query(query_embedding=query_vector, top_k=limit)

        # Step 3: Threshold filtering (TRD Table 37: "below threshold chunk is dropped, not shown as a false citation")
        surviving_matches: List[Dict[str, Any]] = []
        for match in raw_matches:
            if match["score"] >= threshold:
                doc_title = match["source_document"]
                sec = match["section"]
                page = match["page"]
                citation = f"{doc_title} - {sec} (p.{page})"
                
                surviving_matches.append({
                    "text": match["text"],
                    "source_document": match["source_document"],
                    "section": match["section"],
                    "score": match["score"],
                    "page": match["page"],
                    "citation": citation,
                })
            else:
                logger.debug(f"Dropped chunk from '{match['source_document']}' with below-threshold score {match['score']:.4f} < {threshold}")

        logger.info(f"RAG search for '{cleaned_query[:40]}' returned {len(surviving_matches)} valid matches (out of {len(raw_matches)} candidates)")
        return surviving_matches
