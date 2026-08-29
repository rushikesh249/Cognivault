"""Unit tests for the grounded Document Analysis Service (RAG grounding fix)."""

import json
import pytest

from backend.app.models.exceptions import ProviderUnavailable
from backend.app.services.document_analysis import (
    DocumentAnalysisError,
    DocumentAnalysisService,
    build_retrieval_query,
)

SYNTHETIC_PAPER = """
NeuroGrid-7T: A Low-Power Spiking Neural Architecture for Edge Vision

Abstract
This paper presents NeuroGrid-7T, a spiking neural architecture that reduces
edge inference energy consumption by 42.7 percent on the Zebrafish-9 benchmark corpus.

Objectives
The primary objective is to reduce inference energy by 42.7 percent while
maintaining accuracy above 85 percent on embedded vision workloads.

Methodology
We trained NeuroGrid-7T on the Zebrafish-9 benchmark corpus using event-driven
sparse activation and evaluated it on Kalpana-class edge devices with 2W power budgets.

Key Findings
NeuroGrid-7T achieves 87.3 percent top-1 accuracy.
Energy consumption dropped by 42.7 percent compared to the baseline convolutional model.

Conclusions
NeuroGrid-7T is deployable on Kalpana-class edge devices and meets the 2W power budget.
"""


class FakeGroundedProvider:
    """Test double returning well-formed grounded JSON."""

    def generate(self, model_id, prompt, system=None, format=None, stream=False):
        return json.dumps({
            "main_topic": "NeuroGrid-7T spiking neural architecture for edge vision",
            "objectives": "Reduce inference energy by 42.7 percent on Zebrafish-9 while keeping accuracy above 85 percent",
            "methodology": "Event-driven sparse activation training on the Zebrafish-9 benchmark corpus evaluated on Kalpana-class edge devices",
            "key_findings": [
                "NeuroGrid-7T achieves 87.3 percent top-1 accuracy",
                "Energy consumption dropped by 42.7 percent",
            ],
            "conclusions": "NeuroGrid-7T is deployable on Kalpana-class edge devices within the 2W power budget",
            "summary": "The paper introduces NeuroGrid-7T, reducing edge inference energy by 42.7 percent on Zebrafish-9.",
        })


class FakeHallucinatingProvider:
    """Test double that injects unrelated industrial content (must be rejected)."""

    def generate(self, model_id, prompt, system=None, format=None, stream=False):
        return json.dumps({
            "main_topic": "NeuroGrid-7T spiking neural architecture",
            "objectives": "Inspect Refining Unit 02 flare header and recalibrate valve PRV-204 per hydrostatic SOP",
            "methodology": "Hydrostatic bench testing of pump P-102A mechanical seals",
            "key_findings": ["Corrosion fatigue detected on discharge flange bolts"],
            "conclusions": "Immediate depressurization required for the refining unit",
            "summary": "Compliance assessment of refining equipment against safety SOP",
        })


class FakeUnavailableProvider:
    """Test double simulating the local model daemon being unreachable."""

    def generate(self, model_id, prompt, system=None, format=None, stream=False):
        raise ProviderUnavailable("Ollama connection refused")


def test_build_retrieval_query_derived_from_document_text():
    """Retrieval query must follow the uploaded document, never a hardcoded template."""
    query = build_retrieval_query(SYNTHETIC_PAPER, "Analyze the research paper")
    assert "neurogrid" in query.lower()
    assert "zebrafish" in query.lower()
    # No trace of the old hardcoded industrial query
    assert "flange" not in query.lower()
    assert "relief valve" not in query.lower()


def test_build_retrieval_query_falls_back_to_goal_when_text_empty():
    query = build_retrieval_query("", "Analyze the uploaded research methodology document")
    assert query.strip() != ""
    assert "research" in query.lower() or "methodology" in query.lower()


def test_analyze_grounded_model_output_is_used():
    svc = DocumentAnalysisService(provider=FakeGroundedProvider())
    result = svc.analyze(
        extracted_text=SYNTHETIC_PAPER,
        source_document="synthetic_paper.pdf",
        goal="Analyze the uploaded research paper",
    )
    assert result["analysis_model"] == "local-general-model"
    assert result["source_document"] == "synthetic_paper.pdf"
    sv = result["section_values"]
    assert "NeuroGrid-7T" in sv["main_topic"]
    assert "42.7" in sv["objectives"]
    assert any("87.3" in f for f in result["key_findings"])
    headings = [s["heading"] for s in result["sections"]]
    assert headings[:5] == ["Main Topic", "Objectives", "Methodology", "Key Findings", "Conclusions"]
    assert headings[-1] == "Overall Summary"


def test_analyze_rejects_ungrounded_hallucinated_sections():
    """Industrial content invented by the model must be discarded by the grounding check."""
    svc = DocumentAnalysisService(provider=FakeHallucinatingProvider())
    result = svc.analyze(
        extracted_text=SYNTHETIC_PAPER,
        source_document="synthetic_paper.pdf",
        goal="Analyze the uploaded research paper",
    )
    sections_text = json.dumps(result["sections"])
    assert "PRV-204" not in sections_text
    assert "Refining Unit 02" not in sections_text
    assert "P-102A" not in sections_text
    assert "hydrostatic" not in sections_text.lower()
    # Grounded main topic survives
    assert "NeuroGrid-7T" in result["section_values"]["main_topic"]
    # Rejected objectives fall back to deterministic extraction or explicit not-found
    assert "42.7" in result["section_values"]["objectives"] or result["section_values"]["objectives"].startswith("Not found")


def test_analyze_falls_back_to_rule_based_when_model_unavailable():
    svc = DocumentAnalysisService(provider=FakeUnavailableProvider())
    result = svc.analyze(
        extracted_text=SYNTHETIC_PAPER,
        source_document="synthetic_paper.pdf",
        goal="Analyze the uploaded research paper",
    )
    assert result["analysis_model"] == "rule-based-extraction"
    assert "NeuroGrid-7T" in result["section_values"]["main_topic"]
    assert "42.7" in result["section_values"]["objectives"]
    assert "Zebrafish-9" in result["section_values"]["methodology"]
    assert result["key_findings"], "Rule-based extraction must surface key findings"


def test_analyze_without_source_text_raises():
    svc = DocumentAnalysisService(provider=FakeGroundedProvider())
    with pytest.raises(DocumentAnalysisError):
        svc.analyze(
            extracted_text="   ",
            source_document="empty.pdf",
            goal="Analyze the uploaded research paper",
        )


class FakeListSummaryProvider:
    """Test double that returns summary as a list of strings instead of a single string."""

    def generate(self, model_id, prompt, system=None, format=None, stream=False):
        return json.dumps({
            "main_topic": "NeuroGrid-7T spiking neural architecture for edge vision",
            "objectives": "Reduce inference energy by 42.7 percent on Zebrafish-9",
            "methodology": "Event-driven sparse activation training on Zebrafish-9",
            "key_findings": ["87.3 percent top-1 accuracy achieved"],
            "conclusions": "Deployable on Kalpana-class edge devices",
            "summary": ["Point 1: NeuroGrid-7T architecture.", "Point 2: 42.7 percent energy reduction on Zebrafish-9."],
        })


def test_analyze_handles_list_format_summary():
    """Verify that a summary returned as a list of strings is safely parsed without AttributeError."""
    svc = DocumentAnalysisService(provider=FakeListSummaryProvider())
    result = svc.analyze(
        extracted_text=SYNTHETIC_PAPER,
        source_document="synthetic_paper.pdf",
        goal="Analyze the uploaded research paper",
    )
    assert result["summary"]
    assert "NeuroGrid-7T" in result["summary"] or "42.7" in result["summary"]
    assert isinstance(result["summary"], str)

