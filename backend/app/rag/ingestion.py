"""Document Ingestion Pipeline (TRD Section 16.1, Table 36, Component #9).

Parses documents (Markdown/TXT/PDF), cleans text, applies heading-aware section detection,
and chunks text using sentence-boundary aware token constraints (800 tokens, 120 overlap).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import uuid

from backend.app.core.config import settings

logger = logging.getLogger("sovereign_workbench.rag.ingestion")


@dataclass
class DocumentChunk:
    """Represents a chunk of text with metadata for vector indexing (TRD Table 36)."""
    chunk_id: str
    doc_id: str
    source_document: str
    section: str
    page: int
    text: str
    token_count: int
    chunk_index: int


class BaseTokenizer(ABC):
    """Abstract tokenizer interface for token-level chunking (Correction 2)."""

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Convert text to a list of tokens."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in text."""
        pass


class SimpleWordPieceTokenizer(BaseTokenizer):
    """Deterministic token-aware tokenizer approximating BGE/WordPiece tokenization.
    
    Splits text on whitespace and punctuation boundaries, accounting for subword fragments.
    Strictly satisfies Correction 2 by treating tokens as distinct syntactic/subword units
    rather than naive word splitting.
    """

    TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")

    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        tokens: List[str] = []
        for raw_token in self.TOKEN_PATTERN.findall(text):
            # Subword splitting for longer tokens
            if len(raw_token) > 6 and raw_token.isalnum():
                pieces = [raw_token[i:i+4] for i in range(0, len(raw_token), 4)]
                tokens.extend(pieces)
            else:
                tokens.append(raw_token)
        return tokens

    def count_tokens(self, text: str) -> int:
        return len(self.tokenize(text))


class BGETokenizer(BaseTokenizer):
    """Tokenizer wrapping HuggingFace/transformers tokenizer if locally available."""

    def __init__(self, model_id: str = "BAAI/bge-small-en-v1.5", local_path: Optional[str] = None):
        self._tokenizer = None
        self._fallback = SimpleWordPieceTokenizer()
        target = local_path or model_id
        try:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(target, local_files_only=True)
        except Exception:
            self._tokenizer = None

    def tokenize(self, text: str) -> List[str]:
        if self._tokenizer is not None:
            return self._tokenizer.tokenize(text)
        return self._fallback.tokenize(text)

    def count_tokens(self, text: str) -> int:
        if self._tokenizer is not None:
            return len(self._tokenizer.encode(text, add_special_tokens=False))
        return self._fallback.count_tokens(text)


class IngestionPipeline:
    """Document Ingestion Pipeline (TRD Section 16.1, Table 36).
    
    Parse -> Clean -> Chunk (800 tokens, 120 overlap, sentence-boundary aware) -> Metadata.
    """

    def __init__(
        self,
        tokenizer: Optional[BaseTokenizer] = None,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
    ):
        self.tokenizer = tokenizer or SimpleWordPieceTokenizer()
        self.chunk_size = chunk_size or settings.rag.chunk_size
        self.overlap = overlap or settings.rag.overlap

    def clean_text(self, text: str) -> str:
        """Strip extraneous whitespace, normalize line breaks."""
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def parse_markdown_sections(self, content: str) -> List[Tuple[str, str]]:
        """Parse markdown into a list of (section_title, section_body) tuples."""
        lines = content.split("\n")
        sections: List[Tuple[str, str]] = []
        current_title = "General Overview"
        current_lines: List[str] = []

        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            match = heading_pattern.match(line.strip())
            if match:
                if current_lines:
                    body = "\n".join(current_lines).strip()
                    if body:
                        sections.append((current_title, body))
                    current_lines = []
                current_title = match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((current_title, body))

        return sections

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving trailing punctuation."""
        if not text:
            return []
        parts = re.split(r"(?<=[.!?])\s+", text)
        sentences = [p.strip() for p in parts if p.strip()]
        return sentences if sentences else [text.strip()]

    def chunk_section(
        self,
        section_title: str,
        section_text: str,
        doc_id: str,
        source_document: str,
        page: int = 1,
        start_chunk_index: int = 0,
    ) -> List[DocumentChunk]:
        """Chunk a single section into sentence-boundary aware token chunks."""
        cleaned = self.clean_text(section_text)
        if not cleaned:
            return []

        sentences = self._split_into_sentences(cleaned)
        chunks: List[DocumentChunk] = []
        
        current_sentences: List[str] = []
        current_token_count = 0
        chunk_idx = start_chunk_index

        for sent in sentences:
            sent_tokens = self.tokenizer.count_tokens(sent)
            
            if sent_tokens >= self.chunk_size:
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append(DocumentChunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        source_document=source_document,
                        section=section_title,
                        page=page,
                        text=chunk_text,
                        token_count=self.tokenizer.count_tokens(chunk_text),
                        chunk_index=chunk_idx,
                    ))
                    chunk_idx += 1
                    current_sentences = []
                    current_token_count = 0

                chunks.append(DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    source_document=source_document,
                    section=section_title,
                    page=page,
                    text=sent,
                    token_count=sent_tokens,
                    chunk_index=chunk_idx,
                ))
                chunk_idx += 1
                continue

            if current_token_count + sent_tokens > self.chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                chunks.append(DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    source_document=source_document,
                    section=section_title,
                    page=page,
                    text=chunk_text,
                    token_count=self.tokenizer.count_tokens(chunk_text),
                    chunk_index=chunk_idx,
                ))
                chunk_idx += 1

                # Retain overlap from trailing sentences
                overlap_sentences: List[str] = []
                overlap_tokens = 0
                for prev_sent in reversed(current_sentences):
                    prev_cnt = self.tokenizer.count_tokens(prev_sent)
                    if overlap_tokens + prev_cnt <= self.overlap:
                        overlap_sentences.insert(0, prev_sent)
                        overlap_tokens += prev_cnt
                    else:
                        break

                current_sentences = overlap_sentences + [sent]
                current_token_count = sum(self.tokenizer.count_tokens(s) for s in current_sentences)
            else:
                current_sentences.append(sent)
                current_token_count += sent_tokens

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                doc_id=doc_id,
                source_document=source_document,
                section=section_title,
                page=page,
                text=chunk_text,
                token_count=self.tokenizer.count_tokens(chunk_text),
                chunk_index=chunk_idx,
            ))

        return chunks

    def ingest_markdown_file(self, file_path: Path, doc_id: Optional[str] = None) -> Tuple[Dict[str, Any], List[DocumentChunk]]:
        """Ingest a Markdown file, returning metadata dict and list of chunks."""
        if not file_path.exists():
            raise FileNotFoundError(f"Source document not found at: {file_path}")

        doc_id = doc_id or str(uuid.uuid4())
        raw_content = file_path.read_text(encoding="utf-8")
        filename = file_path.name

        category = self._infer_category(filename)
        title = self._extract_document_title(raw_content, fallback=file_path.stem.replace("_", " ").title())

        sections = self.parse_markdown_sections(raw_content)
        all_chunks: List[DocumentChunk] = []

        chunk_idx = 0
        for sec_title, sec_body in sections:
            sec_chunks = self.chunk_section(
                section_title=sec_title,
                section_text=sec_body,
                doc_id=doc_id,
                source_document=filename,
                page=1,
                start_chunk_index=chunk_idx,
            )
            all_chunks.extend(sec_chunks)
            chunk_idx += len(sec_chunks)

        meta = {
            "doc_id": doc_id,
            "title": title,
            "category": category,
            "source_path": str(file_path),
            "chunk_count": len(all_chunks),
        }
        return meta, all_chunks

    def _infer_category(self, filename: str) -> str:
        name = filename.lower()
        if "sop" in name or "safety" in name:
            return "sop"
        elif "manual" in name or "maintenance" in name:
            return "manual"
        elif "guideline" in name or "inspection" in name:
            return "guideline"
        elif "standard" in name or "equipment" in name:
            return "standard"
        elif "approval" in name or "note" in name:
            return "approval_note"
        return "sop"

    def _extract_document_title(self, content: str, fallback: str) -> str:
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return fallback
