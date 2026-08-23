"""Knowledge Base Semantic Search Tool (TRD Section 12, Table 31, Component #14, ADR-006)."""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.services.rag_service import RAGService
from backend.app.tools.base import BaseTool, ToolContext, ToolError, ToolMetadata

logger = logging.getLogger("sovereign_workbench.tools.kb")


class SearchKBInput(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query string")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of matches to retrieve")


class ChunkMatch(BaseModel):
    text: str
    source_document: str
    section: str
    score: float
    page: int
    citation: Optional[str] = None


class SearchKBOutput(BaseModel):
    matches: List[ChunkMatch] = Field(default_factory=list, description="Ranked chunks passing similarity threshold")


class SearchKnowledgeBaseTool(BaseTool):
    """Tool to search indexed knowledge base using local RAG (TRD Table 31)."""

    def __init__(self, rag_service: Optional[RAGService] = None):
        self._rag_service = rag_service

    def _get_rag_service(self) -> RAGService:
        if self._rag_service is None:
            self._rag_service = RAGService()
        return self._rag_service

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="search_knowledge_base",
            purpose="Semantic search over indexed knowledge base.",
            input_schema=SearchKBInput,
            output_schema=SearchKBOutput,
            allowed_task_types=["document"],
            timeout_s=10.0,
            fs_boundary="ChromaDB, read-only",
            network="none (local only)",
        )

    def execute(self, input_data: SearchKBInput, ctx: ToolContext) -> SearchKBOutput:
        rag = self._get_rag_service()
        try:
            results = rag.search(query=input_data.query, top_k=input_data.top_k)
            matches = [ChunkMatch(**r) for r in results]
            return SearchKBOutput(matches=matches)
        except Exception as e:
            raise ToolError(f"Knowledge search failed: {e}") from e
