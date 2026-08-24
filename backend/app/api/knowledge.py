"""Knowledge Base REST API Router (TRD Section 9, Table 15)."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.app.services.rag_service import RAGService

logger = logging.getLogger("sovereign_workbench.api.knowledge")

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KBSearch(BaseModel):
    """Knowledge search request schema (TRD Table 15)."""
    query: str = Field(..., description="Search query string")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of matches to return")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query string must not be empty or whitespace only")
        return v.strip()


class KBMatch(BaseModel):
    """Knowledge match schema (TRD Table 15)."""
    text: str
    source_document: str
    section: str
    score: float
    page: int
    citation: Optional[str] = None


class KBResult(BaseModel):
    """Knowledge search response schema (TRD Table 15)."""
    matches: List[KBMatch] = Field(default_factory=list)


def get_rag_service() -> RAGService:
    return RAGService()


@router.post("/search", response_model=KBResult, status_code=status.HTTP_200_OK)
async def search_knowledge_base(
    payload: KBSearch,
    rag_service: RAGService = Depends(get_rag_service),
) -> KBResult:
    """Query the sovereign knowledge base using local semantic retrieval (TRD Table 15)."""
    try:
        results = rag_service.search(query=payload.query, top_k=payload.top_k)
        matches = [KBMatch(**r) for r in results]
        return KBResult(matches=matches)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        logger.error(f"Error executing knowledge search: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Knowledge search failed")
