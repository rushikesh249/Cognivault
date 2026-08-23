"""Unit tests for Document Chunking and Tokenization (TRD Section 16.1, Section 16.3, Table 38, Test Plan P20)."""

import pytest
from backend.app.rag.ingestion import (
    DocumentChunk,
    IngestionPipeline,
    SimpleWordPieceTokenizer,
)


@pytest.fixture
def tokenizer():
    return SimpleWordPieceTokenizer()


@pytest.fixture
def pipeline(tokenizer):
    return IngestionPipeline(tokenizer=tokenizer, chunk_size=800, overlap=120)


def test_tokenizer_token_counting(tokenizer):
    text = "Emergency shutdown system activated for Unit 101."
    tokens = tokenizer.tokenize(text)
    assert len(tokens) > 0
    assert tokenizer.count_tokens(text) == len(tokens)


def test_chunk_size_and_overlap_constraints(pipeline):
    sentences = [f"Clause {i}: Process unit safety parameter must not exceed {100 + i * 5} degrees Celsius." for i in range(150)]
    long_text = " ".join(sentences)

    chunks = pipeline.chunk_section(
        section_title="Thermal Limits",
        section_text=long_text,
        doc_id="test-doc-001",
        source_document="safety_sop.md",
        page=1,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 800
        assert chunk.section == "Thermal Limits"
        assert chunk.source_document == "safety_sop.md"
        assert chunk.page == 1
        assert chunk.doc_id == "test-doc-001"


def test_sentence_boundary_integrity(pipeline):
    text = "Sentence one is here. Sentence two follows immediately! Does sentence three work? Yes it does."
    chunks = pipeline.chunk_section(
        section_title="Testing",
        section_text=text,
        doc_id="test-doc-002",
        source_document="test.md",
        page=1,
    )

    assert len(chunks) == 1
    chunk_text = chunks[0].text
    assert "Sentence one is here." in chunk_text
    assert "Sentence two follows immediately!" in chunk_text
    assert "Does sentence three work?" in chunk_text


def test_markdown_heading_section_extraction(pipeline):
    md_content = """# Main Document Title

## 1. Safety Systems
Safety interlocks are active.

### 1.1 ESD Activation
The ESD shuts down all fuel valves immediately.

## 2. Maintenance Procedures
Routine inspection occurs weekly.
"""
    sections = pipeline.parse_markdown_sections(md_content)
    assert len(sections) == 3
    assert sections[0][0] == "1. Safety Systems"
    assert "Safety interlocks are active." in sections[0][1]
    assert sections[1][0] == "1.1 ESD Activation"
    assert "ESD shuts down all fuel valves" in sections[1][1]
    assert sections[2][0] == "2. Maintenance Procedures"


def test_empty_document_produces_zero_chunks(pipeline):
    chunks = pipeline.chunk_section(
        section_title="Empty Section",
        section_text="",
        doc_id="empty-doc",
        source_document="empty.md",
        page=1,
    )
    assert len(chunks) == 0


def test_single_short_document_produces_one_chunk(pipeline):
    short_text = "Standard atmospheric pressure is 101.325 kPa at sea level."
    chunks = pipeline.chunk_section(
        section_title="Standards",
        section_text=short_text,
        doc_id="short-doc",
        source_document="standards.md",
        page=1,
    )
    assert len(chunks) == 1
    assert chunks[0].text == short_text
    assert chunks[0].token_count < 800
