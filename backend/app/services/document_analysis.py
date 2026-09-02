"""Grounded Document Analysis Service (TRD Section 16, ADR-002, ADR-006).

Analyzes extracted uploaded-document text with the local general model and
produces a structured report (main topic, objectives, methodology, key
findings, conclusions, summary).

Grounding invariants enforced here:
- The uploaded document's extracted text is the PRIMARY source. Knowledge-base
  chunks are supplementary context only and are never substituted for it.
- Every generated section must be grounded in the source text (token-overlap
  check); ungrounded model output is discarded and replaced with a
  deterministic extraction from the source or an explicit
  "Not found in the source document." marker.
- If the local model is unavailable, a deterministic rule-based extraction
  from the source text is used instead of fabricating content.
- Strictly local inference (Ollama). No cloud egress.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.exceptions import ModelLoadError, ModelUnavailable, ProviderUnavailable
from backend.app.models.model_registry import ModelRegistry
from backend.app.models.ollama_adapter import OllamaAdapter

logger = logging.getLogger("sovereign_workbench.services.document_analysis")

NOT_FOUND = "Not found in the source document."

# Ordered report sections required for structured document analysis.
SECTION_ORDER: List[Tuple[str, str]] = [
    ("main_topic", "Main Topic"),
    ("objectives", "Objectives"),
    ("methodology", "Methodology"),
    ("key_findings", "Key Findings"),
    ("conclusions", "Conclusions"),
]

# Max chars of extracted document text injected into the model prompt.
MAX_SOURCE_CHARS = 12000
MAX_KB_CHUNK_CHARS = 800
MAX_KB_CHUNKS = 2

_STOPWORDS = {
    "and", "the", "is", "in", "at", "of", "a", "to", "for", "with", "on",
    "this", "that", "by", "from", "are", "was", "were", "be", "been", "as",
    "it", "its", "an", "or", "we", "our", "their", "which", "when", "where",
    "into", "over", "under", "between", "using", "used", "use", "can", "will",
    "based", "via", "such", "than", "then", "these", "those", "has", "have",
}

_HEADING_PATTERNS: Dict[str, List[str]] = {
    "objectives": ["objectives", "objective", "aims", "aim", "goals", "research questions", "purpose"],
    "methodology": ["methodology", "methods", "method", "materials and methods", "approach", "experimental setup", "design"],
    "key_findings": ["key findings", "findings", "results", "results and discussion", "observations", "evaluation results"],
    "conclusions": ["conclusions", "conclusion", "concluding remarks", "summary and conclusions", "discussion"],
}


class DocumentAnalysisError(Exception):
    """Raised when document analysis cannot be performed at all."""
    pass


def _tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric token extraction for grounding checks and queries."""
    return [t for t in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower()) if t not in _STOPWORDS]


def build_retrieval_query(extracted_text: str, goal: str, max_terms: int = 8) -> str:
    """
    Derive a knowledge-base retrieval query from the uploaded document's own
    extracted text (primary) and the task goal (secondary). This replaces any
    hardcoded query so retrieval relevance follows the actual document.
    """
    tokens = _tokenize(extracted_text or "")
    freq: Dict[str, int] = {}
    for tok in tokens:
        if len(tok) >= 5:
            freq[tok] = freq.get(tok, 0) + 1

    ranked = sorted(freq.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
    terms = [w for w, _ in ranked[:max_terms]]

    if not terms:
        goal_tokens = [t for t in _tokenize(goal or "") if len(t) >= 5]
        terms = list(dict.fromkeys(goal_tokens))[:max_terms]

    return " ".join(terms) if terms else (goal or "document analysis")


def _extract_heading_sections(text: str) -> Dict[str, str]:
    """
    Deterministic rule-based section extraction from the source document.
    Locates common academic/technical headings and captures the paragraph
    text that follows them (up to the next heading or a size cap).
    """
    lines = [ln.strip() for ln in text.splitlines()]
    captured: Dict[str, str] = {}

    heading_regexes: List[Tuple[str, re.Pattern]] = []
    for key, variants in _HEADING_PATTERNS.items():
        alt = "|".join(re.escape(v) for v in variants)
        pattern = re.compile(rf"^(?:\d+[\.\)]?\s*)?(?:{alt})\s*:?\s*$", re.IGNORECASE)
        heading_regexes.append((key, pattern))

    def is_any_heading(line: str) -> bool:
        if len(line) > 80:
            return False
        return any(p.match(line) for _, p in heading_regexes) or re.match(
            r"^(?:\d+[\.\)]?\s*)?[A-Z][A-Za-z &\-]{2,60}$", line
        ) is not None

    for idx, line in enumerate(lines):
        if not line or len(line) > 80:
            continue
        for key, pattern in heading_regexes:
            if pattern.match(line) and key not in captured:
                buf: List[str] = []
                for follow in lines[idx + 1: idx + 30]:
                    if is_any_heading(follow) and buf:
                        break
                    if follow:
                        buf.append(follow)
                    if sum(len(b) for b in buf) > 700:
                        break
                if buf:
                    captured[key] = " ".join(buf)[:700]
                break
    return captured


def _main_topic_from_text(text: str) -> str:
    """Derive the main topic from the document's leading lines."""
    for line in text.splitlines():
        candidate = line.strip()
        if candidate and len(candidate) > 8 and not candidate.startswith(("http", "www.", "doi:")):
            return candidate[:250]
    return NOT_FOUND


def _is_grounded(section_text: str, source_tokens: set, kb_tokens: set) -> bool:
    """
    Grounding check: a model-generated section is accepted only if at least
    one of its significant tokens also appears in the source document or the
    retrieved knowledge-base context. Sections made of entirely foreign
    terminology (e.g. invented equipment or facilities) are rejected.
    Exact token matching avoids substring false positives (e.g. "bench"
    inside "benchmark").
    """
    tokens = [t for t in _tokenize(section_text) if len(t) >= 4]
    if not tokens:
        return False
    for tok in tokens:
        if tok in source_tokens or tok in kb_tokens:
            return True
    return False


class DocumentAnalysisService:
    """Structured, source-grounded document analysis using the local general model."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        provider: Optional[OllamaAdapter] = None,
    ):
        self._registry = registry or ModelRegistry()
        self._provider = provider

    def _get_provider(self) -> OllamaAdapter:
        if self._provider is None:
            import httpx
            # Generation on a local 7B model can take minutes; use a generous
            # HTTP timeout distinct from the short availability-probe timeout.
            self._provider = OllamaAdapter(http_client=httpx.Client(timeout=600.0))
        return self._provider

    def _resolve_model(self) -> Optional[str]:
        cfg = self._registry.get("local-general-model")
        return cfg.model_path if cfg else None

    def analyze(
        self,
        extracted_text: str,
        source_document: str,
        goal: str,
        kb_matches: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Produce a grounded structured analysis of the extracted document text.
        kb_matches are supplementary only; they never replace the source text.
        """
        clean_text = (extracted_text or "").strip()
        if not clean_text:
            raise DocumentAnalysisError(
                "No extracted text is available from the uploaded document; "
                "analysis cannot be grounded without source content."
            )

        kb_matches = kb_matches or []
        clean_lower = clean_text.lower()
        is_unreadable = (
            "no readable text was extracted" in clean_lower
            or clean_lower.startswith("[image content:")
        )

        if is_unreadable:
            unreadable_msg = "No readable text was extracted from the supplied image."
            sections_payload = [
                {"heading": "Main Topic", "content": unreadable_msg},
                {"heading": "Objectives", "content": NOT_FOUND},
                {"heading": "Methodology", "content": NOT_FOUND},
                {"heading": "Key Findings", "content": NOT_FOUND},
                {"heading": "Conclusions", "content": NOT_FOUND},
                {"heading": "Overall Summary", "content": unreadable_msg},
            ]
            return {
                "source_document": source_document,
                "sections": sections_payload,
                "section_values": {
                    "main_topic": unreadable_msg,
                    "objectives": NOT_FOUND,
                    "methodology": NOT_FOUND,
                    "key_findings": NOT_FOUND,
                    "conclusions": NOT_FOUND,
                },
                "key_findings": [],
                "summary": unreadable_msg,
                "analysis_model": "rule-based-extraction",
                "grounding_verified": True,
            }

        kb_text = "\n".join(str(m.get("text", ""))[:MAX_KB_CHUNK_CHARS] for m in kb_matches[:MAX_KB_CHUNKS])
        source_lower = clean_text.lower()
        kb_lower = kb_text.lower()
        source_tokens = set(_tokenize(source_lower))
        kb_tokens = set(_tokenize(kb_lower))

        section_values = self._model_extract(clean_text, goal, kb_text)
        rule_sections = _extract_heading_sections(clean_text)

        # Merge: model output first, deterministic source extraction as
        # fallback, explicit "not found" as the final honest answer.
        grounded_flags: List[bool] = []
        for key, _heading in SECTION_ORDER:
            raw_val = section_values.get(key)
            if isinstance(raw_val, list):
                items = [str(v).strip() for v in raw_val if str(v).strip()]
                model_val = "\n".join(items) if items else ""
                section_values[key] = items if items else ""
            else:
                model_val = (str(raw_val) if raw_val is not None else "").strip()
            if model_val and model_val.lower() not in ("not found", "n/a", "none", "not found in the source document."):
                if _is_grounded(model_val, source_tokens, kb_tokens):
                    section_values[key] = model_val
                    grounded_flags.append(True)
                else:
                    logger.warning(
                        f"Discarded ungrounded model output for section '{key}'; "
                        "falling back to deterministic source extraction."
                    )
                    section_values[key] = rule_sections.get(key) or self._fallback_value(key, clean_text)
                    grounded_flags.append(section_values[key] != NOT_FOUND)
            else:
                section_values[key] = rule_sections.get(key) or self._fallback_value(key, clean_text)
                grounded_flags.append(section_values[key] != NOT_FOUND)

        # Normalize key findings into a bullet list for templates.
        findings_raw = section_values.get("key_findings", "")
        if isinstance(findings_raw, list):
            key_findings = [str(f).strip() for f in findings_raw if str(f).strip()]
        else:
            findings_str = str(findings_raw)
            key_findings = [s.strip() for s in re.split(r"(?<=[\.\!])\s+|\n+", findings_str) if s.strip()]
            key_findings = key_findings[:6]
        if not key_findings or findings_raw == NOT_FOUND:
            key_findings = []

        raw_summary = section_values.get("summary")
        if isinstance(raw_summary, list):
            summary = " ".join(str(s).strip() for s in raw_summary if str(s).strip())
        else:
            summary = (str(raw_summary) if raw_summary is not None else "").strip()

        if not summary or not _is_grounded(summary, source_tokens, kb_tokens):
            sentences = re.split(r"(?<=[\.!?])\s+", clean_text.replace("\n", " "))
            summary = " ".join(sentences[:2])[:600] if sentences else NOT_FOUND

        sections_payload = [
            {"heading": heading, "content": section_values.get(key, NOT_FOUND)}
            for key, heading in SECTION_ORDER
        ]
        sections_payload.append({"heading": "Overall Summary", "content": summary})

        return {
            "source_document": source_document,
            "sections": sections_payload,
            "section_values": {key: section_values.get(key, NOT_FOUND) for key, _ in SECTION_ORDER},
            "key_findings": key_findings,
            "summary": summary,
            "analysis_model": section_values.pop("_model", "rule-based-extraction"),
            "grounding_verified": all(grounded_flags),
        }

    def _fallback_value(self, key: str, text: str) -> str:
        """Deterministic per-section fallback drawn only from the source text."""
        if key == "main_topic":
            return _main_topic_from_text(text)
        return NOT_FOUND

    def _model_extract(self, text: str, goal: str, kb_text: str) -> Dict[str, str]:
        """Attempt structured JSON extraction via the local general model."""
        model_path = self._resolve_model()
        if not model_path:
            logger.warning("local-general-model not configured; using rule-based extraction.")
            return {"_model": "rule-based-extraction"}

        system_prompt = (
            "You are a meticulous document analyst. You must use ONLY the provided "
            "document text below. Never invent facilities, equipment, standards, "
            "citations, findings, or any fact not present in the document. If a "
            "requested item is absent from the document, answer exactly: "
            f"{NOT_FOUND}"
        )

        kb_block = ""
        if kb_text:
            kb_block = (
                "\n\nSUPPLEMENTARY KNOWLEDGE-BASE CONTEXT (use only if directly "
                "relevant; the document itself is the primary source):\n" + kb_text
            )

        prompt = (
            f"Task goal: {goal}\n\n"
            "DOCUMENT TEXT (primary source):\n"
            f"{text[:MAX_SOURCE_CHARS]}\n"
            f"{kb_block}\n\n"
            "Respond with a single JSON object with exactly these keys:\n"
            '{"main_topic": string, "objectives": string, "methodology": string, '
            '"key_findings": [string, ...], "conclusions": string, "summary": string}\n'
            "Each value must be concise (1-4 sentences or up to 5 bullet strings for "
            "key_findings) and strictly grounded in the document text."
        )

        try:
            provider = self._get_provider()
            raw_response = provider.generate(
                model_id=model_path,
                prompt=prompt,
                system=system_prompt,
                format="json",
            )
        except (ProviderUnavailable, ModelUnavailable, ModelLoadError) as e:
            logger.warning(f"Local model unavailable for document analysis: {e}")
            return {"_model": "rule-based-extraction"}
        except Exception as e:
            logger.error(f"Local model generation failed during document analysis: {e}", exc_info=True)
            return {"_model": "rule-based-extraction"}

        parsed = self._parse_model_json(raw_response)
        if parsed is None:
            logger.warning("Model response was not valid JSON; using rule-based extraction.")
            return {"_model": "rule-based-extraction"}

        parsed["_model"] = "local-general-model"
        return parsed

    @staticmethod
    def _parse_model_json(raw_response: str) -> Optional[Dict[str, Any]]:
        """Parse model JSON output tolerantly (handles code fences / extra prose)."""
        if not raw_response:
            return None
        candidate = raw_response.strip()
        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", candidate)
        if match:
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None


_document_analysis_service_instance: Optional[DocumentAnalysisService] = None


def get_document_analysis_service() -> DocumentAnalysisService:
    global _document_analysis_service_instance
    if _document_analysis_service_instance is None:
        _document_analysis_service_instance = DocumentAnalysisService()
    return _document_analysis_service_instance
