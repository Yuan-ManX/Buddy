"""
Buddy Multi-Modal Understanding Engine - Cross-modal processing and fusion.

An engine for processing and understanding multiple modalities of input
including text, code, structured data, and more. Supports cross-modal
fusion, format detection, and unified understanding across modalities.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class InputModality(str, Enum):
    """Supported input modalities."""
    TEXT = "text"
    CODE = "code"
    STRUCTURED_DATA = "structured_data"
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    TABLE = "table"
    LIST = "list"
    QUERY = "query"
    COMMAND = "command"


class ProcessingMode(str, Enum):
    """Processing modes for different understanding strategies."""
    DIRECT = "direct"           # Pass through as-is
    PARSE = "parse"             # Parse structured format
    EXTRACT = "extract"         # Extract key information
    TRANSFORM = "transform"     # Transform to another format
    FUSE = "fuse"               # Fuse multiple modalities
    SUMMARIZE = "summarize"     # Generate summary
    CLASSIFY = "classify"       # Classify the content


@dataclass
class ModalityInput:
    """A single input in a specific modality."""
    input_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    modality: InputModality = InputModality.TEXT
    content: str = ""
    raw_content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)


@dataclass
class UnderstandingResult:
    """Result of processing and understanding input."""
    result_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    input_id: str = ""
    modality: InputModality = InputModality.TEXT
    processing_mode: ProcessingMode = ProcessingMode.DIRECT
    understanding: str = ""
    extracted_entities: list[str] = field(default_factory=list)
    extracted_keywords: list[str] = field(default_factory=list)
    detected_language: str = ""
    content_type: str = ""
    summary: str = ""
    confidence: float = 0.5
    processing_time_ms: float = 0.0
    created_at: float = field(default_factory=time.time)


@dataclass
class FusionResult:
    """Result of fusing multiple modalities."""
    fusion_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    inputs: list[str] = field(default_factory=list)
    modalities: list[str] = field(default_factory=list)
    unified_understanding: str = ""
    cross_modal_insights: list[str] = field(default_factory=list)
    consistency_score: float = 0.0
    confidence: float = 0.0
    created_at: float = field(default_factory=time.time)


class MultiModalUnderstandingEngine:
    """Cross-modal processing and understanding engine.

    Processes inputs across multiple modalities, detects formats automatically,
    extracts structured information, and fuses understanding across modalities
    for a unified comprehension of content.
    """

    # Language detection keywords
    LANGUAGE_KEYWORDS: dict[str, list[str]] = {
        "python": ["def ", "import ", "class ", "print(", "lambda", "from ", "self."],
        "javascript": ["function ", "const ", "let ", "var ", "=>", "console.log", "import {"],
        "typescript": ["interface ", "type ", "enum ", "as const", ": string", ": number"],
        "sql": ["SELECT ", "FROM ", "WHERE ", "INSERT ", "UPDATE ", "JOIN ", "GROUP BY"],
        "html": ["<html", "<div", "<span", "<body", "<head", "<!DOCTYPE"],
        "css": ["{", "}", ":", ";", "px", "em", "rem", "color:", "margin:", "padding:"],
        "json": ["{", "}", "[", "]", '":', '",'],
        "yaml": ["apiVersion:", "kind:", "metadata:", "spec:", "---"],
        "markdown": ["# ", "## ", "### ", "```", "**", "__", "- ["],
        "shell": ["#!/bin", "echo ", "export ", "sudo ", "chmod ", "grep ", "awk "],
    }

    def __init__(self) -> None:
        self._inputs: dict[str, ModalityInput] = {}
        self._results: list[UnderstandingResult] = []
        self._fusions: list[FusionResult] = []
        self._total_inputs: int = 0
        self._total_results: int = 0

    # ── Input Processing ─────────────────────────────────────────

    def detect_modality(self, content: str) -> InputModality:
        """Auto-detect the modality of input content.

        Args:
            content: The raw input content.

        Returns:
            The detected InputModality.
        """
        content_stripped = content.strip()

        # Check for JSON
        if content_stripped.startswith("{") or content_stripped.startswith("["):
            try:
                import json
                json.loads(content_stripped)
                return InputModality.JSON
            except (json.JSONDecodeError, ValueError):
                pass

        # Check for YAML
        if ":" in content_stripped and "\n" in content_stripped:
            yaml_indicators = ["apiVersion:", "kind:", "metadata:", "spec:"]
            if any(ind in content_stripped for ind in yaml_indicators):
                return InputModality.YAML

        # Check for Markdown
        if content_stripped.startswith("#") or "```" in content_stripped:
            return InputModality.MARKDOWN

        # Check for code
        code_indicators = [
            "def ", "class ", "import ", "function ", "const ", "let ",
            "SELECT ", "FROM ", "#!/bin",
        ]
        if any(ind in content_stripped[:200] for ind in code_indicators):
            return InputModality.CODE

        # Check for table-like structure
        if "|" in content_stripped and "\n" in content_stripped:
            lines = content_stripped.split("\n")
            if len(lines) >= 2 and all("|" in line for line in lines[:2]):
                return InputModality.TABLE

        # Check for list
        if "\n" in content_stripped:
            lines = content_stripped.split("\n")
            if all(line.strip().startswith(("- ", "* ", "+ ", "1. ")) for line in lines[:3] if line.strip()):
                return InputModality.LIST

        # Default to text
        return InputModality.TEXT

    def detect_language(self, content: str) -> str:
        """Detect the programming language of code content.

        Args:
            content: The code content.

        Returns:
            Detected language name or 'unknown'.
        """
        scores: dict[str, int] = {}
        for lang, keywords in self.LANGUAGE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                scores[lang] = score

        if scores:
            return max(scores, key=scores.get)  # type: ignore[arg-type]
        return "unknown"

    def process(
        self,
        content: str,
        modality: InputModality | None = None,
        processing_mode: ProcessingMode = ProcessingMode.DIRECT,
        metadata: dict[str, Any] | None = None,
    ) -> UnderstandingResult:
        """Process and understand input content.

        Args:
            content: The input content to process.
            modality: Explicit modality. Auto-detected if None.
            processing_mode: How to process the content.
            metadata: Additional metadata about the input.

        Returns:
            An UnderstandingResult with processed understanding.
        """
        start_time = time.time()

        if modality is None:
            modality = self.detect_modality(content)

        # Create input record
        inp = ModalityInput(
            modality=modality,
            content=content,
            raw_content=content,
            metadata=metadata or {},
        )
        self._inputs[inp.input_id] = inp
        self._total_inputs += 1

        # Process based on modality and mode
        understanding = ""
        entities: list[str] = []
        keywords: list[str] = []
        detected_lang = ""
        summary = ""

        if processing_mode == ProcessingMode.PARSE:
            understanding, entities, keywords = self._parse(content, modality)
        elif processing_mode == ProcessingMode.EXTRACT:
            understanding, entities, keywords = self._extract(content, modality)
        elif processing_mode == ProcessingMode.TRANSFORM:
            understanding = self._transform(content, modality)
        elif processing_mode == ProcessingMode.SUMMARIZE:
            summary = self._summarize(content)
            understanding = summary
        elif processing_mode == ProcessingMode.CLASSIFY:
            understanding = self._classify(content, modality)
        else:  # DIRECT
            understanding = content
            keywords = self._extract_keywords(content)

        if modality == InputModality.CODE:
            detected_lang = self.detect_language(content)

        processing_time = (time.time() - start_time) * 1000

        result = UnderstandingResult(
            input_id=inp.input_id,
            modality=modality,
            processing_mode=processing_mode,
            understanding=understanding,
            extracted_entities=entities,
            extracted_keywords=keywords,
            detected_language=detected_lang,
            content_type=modality.value,
            summary=summary,
            confidence=self._compute_confidence(modality, processing_mode),
            processing_time_ms=processing_time,
        )

        self._results.append(result)
        self._total_results += 1
        return result

    def _parse(
        self, content: str, modality: InputModality
    ) -> tuple[str, list[str], list[str]]:
        """Parse structured content."""
        if modality == InputModality.JSON:
            try:
                import json
                data = json.loads(content)
                return (
                    f"JSON object with {len(data) if isinstance(data, dict) else len(data)} top-level elements",
                    list(data.keys()) if isinstance(data, dict) else [],
                    list(data.keys()) if isinstance(data, dict) else [],
                )
            except (json.JSONDecodeError, ValueError):
                return "Invalid JSON", [], []

        elif modality == InputModality.TABLE:
            lines = content.strip().split("\n")
            if len(lines) >= 2:
                headers = [h.strip() for h in lines[0].split("|") if h.strip()]
                return (
                    f"Table with {len(headers)} columns: {', '.join(headers)}",
                    headers,
                    headers,
                )
            return "Invalid table format", [], []

        return content, [], []

    def _extract(
        self, content: str, modality: InputModality
    ) -> tuple[str, list[str], list[str]]:
        """Extract key information from content."""
        keywords = self._extract_keywords(content)
        entities = self._extract_entities(content)
        return (
            f"Extracted {len(keywords)} keywords and {len(entities)} entities",
            entities,
            keywords,
        )

    def _transform(self, content: str, modality: InputModality) -> str:
        """Transform content to a different representation."""
        if modality == InputModality.STRUCTURED_DATA:
            return f"Transformed structured data: {content[:200]}"
        return f"Transformed {modality.value}: {content[:200]}"

    def _summarize(self, content: str) -> str:
        """Generate a summary of content."""
        words = content.split()
        if len(words) <= 50:
            return content

        first_sentences = ". ".join(content.split(".")[:3]) + "."
        return f"Summary: {first_sentences}"

    def _classify(self, content: str, modality: InputModality) -> str:
        """Classify the content type."""
        classifications = []
        if modality == InputModality.CODE:
            lang = self.detect_language(content)
            classifications.append(f"Code ({lang})")
        elif modality == InputModality.MARKDOWN:
            classifications.append("Documentation")
        elif modality == InputModality.QUERY:
            classifications.append("Query/Question")
        else:
            classifications.append("General text")

        return f"Classification: {', '.join(classifications)}"

    def _extract_keywords(self, content: str) -> list[str]:
        """Extract meaningful keywords from content."""
        # Simple keyword extraction: long words and capitalized words
        words = content.split()
        keywords = []
        for word in words:
            clean = word.strip(".,!?;:()[]{}'\"")
            if len(clean) > 4 and not clean.islower():
                keywords.append(clean)
        return list(set(keywords))[:15]

    def _extract_entities(self, content: str) -> list[str]:
        """Extract named entities from content."""
        entities = []
        words = content.split()
        for i, word in enumerate(words):
            clean = word.strip(".,!?;:()[]{}'\"")
            # Capitalized words that aren't at sentence start
            if clean and clean[0].isupper() and len(clean) > 1:
                if i > 0 and not words[i - 1].endswith("."):
                    entities.append(clean)
        return list(set(entities))[:10]

    def _compute_confidence(
        self, modality: InputModality, mode: ProcessingMode
    ) -> float:
        """Compute confidence based on modality and processing mode."""
        base = 0.8
        if mode == ProcessingMode.DIRECT:
            base = 0.9
        elif mode == ProcessingMode.PARSE:
            base = 0.85
        elif mode == ProcessingMode.EXTRACT:
            base = 0.7
        elif mode == ProcessingMode.FUSE:
            base = 0.75
        return base

    # ── Fusion Operations ────────────────────────────────────────

    def fuse(
        self,
        input_ids: list[str],
    ) -> FusionResult | None:
        """Fuse understanding from multiple inputs across modalities.

        Args:
            input_ids: Input IDs to fuse together.

        Returns:
            A FusionResult with unified understanding.
        """
        # Get the inputs and their results
        inputs_found = []
        modalities = []
        for iid in input_ids:
            inp = self._inputs.get(iid)
            if inp:
                inputs_found.append(inp)
                modalities.append(inp.modality.value)

        if not inputs_found:
            return None

        # Build unified understanding
        parts = []
        insights = []
        for inp in inputs_found:
            parts.append(f"[{inp.modality.value}] {inp.content[:200]}")

        unified = (
            f"Cross-modal fusion of {len(inputs_found)} inputs "
            f"({', '.join(set(modalities))}):\n\n" + "\n\n---\n\n".join(parts)
        )

        # Generate cross-modal insights
        if len(set(modalities)) > 1:
            insights.append(
                f"Cross-modal insight: {len(set(modalities))} different modalities "
                f"combined for holistic understanding"
            )

        consistency = 0.8 if len(inputs_found) > 1 else 1.0

        fusion = FusionResult(
            inputs=input_ids,
            modalities=modalities,
            unified_understanding=unified,
            cross_modal_insights=insights,
            consistency_score=consistency,
            confidence=0.8,
        )

        self._fusions.append(fusion)
        return fusion

    # ── Query & Stats ────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get understanding engine statistics."""
        modality_counts: dict[str, int] = {}
        for inp in self._inputs.values():
            modality_counts[inp.modality.value] = (
                modality_counts.get(inp.modality.value, 0) + 1
            )

        return {
            "total_inputs": self._total_inputs,
            "total_results": self._total_results,
            "total_fusions": len(self._fusions),
            "modality_distribution": modality_counts,
            "avg_confidence": round(
                sum(r.confidence for r in self._results) / len(self._results), 3
            ) if self._results else 0.0,
            "avg_processing_ms": round(
                sum(r.processing_time_ms for r in self._results) / len(self._results), 1
            ) if self._results else 0.0,
        }

    def get_recent_results(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent understanding results."""
        return [
            {
                "result_id": r.result_id,
                "modality": r.modality.value,
                "processing_mode": r.processing_mode.value,
                "understanding": r.understanding[:300],
                "extracted_entities": r.extracted_entities,
                "extracted_keywords": r.extracted_keywords,
                "detected_language": r.detected_language,
                "summary": r.summary,
                "confidence": r.confidence,
                "processing_time_ms": r.processing_time_ms,
            }
            for r in self._results[-limit:]
        ]

    def get_recent_fusions(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent fusion results."""
        return [
            {
                "fusion_id": f.fusion_id,
                "modalities": f.modalities,
                "unified_understanding": f.unified_understanding[:300],
                "cross_modal_insights": f.cross_modal_insights,
                "consistency_score": f.consistency_score,
                "confidence": f.confidence,
            }
            for f in self._fusions[-limit:]
        ]

    def reset(self) -> None:
        """Reset the understanding engine to initial state."""
        self._inputs.clear()
        self._results.clear()
        self._fusions.clear()
        self._total_inputs = 0
        self._total_results = 0


# ── Singleton Access ───────────────────────────────────────────────

_understanding_engine: MultiModalUnderstandingEngine | None = None


def get_understanding_engine() -> MultiModalUnderstandingEngine:
    """Get or create the singleton understanding engine instance."""
    global _understanding_engine
    if _understanding_engine is None:
        _understanding_engine = MultiModalUnderstandingEngine()
    return _understanding_engine


def reset_understanding_engine() -> None:
    """Reset the singleton understanding engine."""
    global _understanding_engine
    if _understanding_engine:
        _understanding_engine.reset()
    _understanding_engine = None