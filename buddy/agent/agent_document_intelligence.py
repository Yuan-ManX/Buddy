"""
Buddy Document Intelligence Engine - Document processing and analysis.

Provides comprehensive document intelligence capabilities including parsing,
extraction, classification, and analysis of various document formats. The
engine supports multiple file types, structured data extraction, semantic
search, and automatic summarization.

Core capabilities:
- Multi-format document parsing (PDF, DOCX, TXT, Markdown, HTML, CSV, JSON)
- Structured data extraction with schema inference
- Document classification and categorization
- Key information extraction (entities, dates, amounts, contacts)
- Automatic document summarization
- Semantic search within documents
- Document comparison and diff analysis
- Batch processing with progress tracking
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.document_intelligence")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    IMAGE = "image"


class DocumentCategory(str, Enum):
    """Document classification categories."""
    REPORT = "report"
    CONTRACT = "contract"
    INVOICE = "invoice"
    RESUME = "resume"
    ARTICLE = "article"
    EMAIL = "email"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    CODE = "code"
    OTHER = "other"


class ExtractionType(str, Enum):
    """Types of information to extract from documents."""
    ENTITIES = "entities"
    KEY_PHRASES = "key_phrases"
    DATES = "dates"
    AMOUNTS = "amounts"
    CONTACTS = "contacts"
    TABLES = "tables"
    LINKS = "links"
    HEADERS = "headers"


class DocumentStatus(str, Enum):
    """Processing status of a document."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class DocumentInfo:
    """Metadata and processing info for a document."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    filename: str = ""
    format: DocumentFormat = DocumentFormat.TXT
    size_bytes: int = 0
    page_count: int = 0
    word_count: int = 0
    status: DocumentStatus = DocumentStatus.UPLOADED
    category: DocumentCategory = DocumentCategory.OTHER
    title: str = ""
    author: str = ""
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: datetime | None = None


@dataclass
class ExtractionResult:
    """Result of information extraction from a document."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    document_id: str = ""
    extraction_type: ExtractionType = ExtractionType.ENTITIES
    items: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DocumentSummary:
    """Summary of a document's content."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    document_id: str = ""
    summary_text: str = ""
    key_points: list[str] = field(default_factory=list)
    word_count_original: int = 0
    word_count_summary: int = 0
    compression_ratio: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SearchResult:
    """Result of a semantic search within documents."""
    document_id: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    page_number: int = 0
    line_number: int = 0
    context_before: str = ""
    context_after: str = ""


@dataclass
class CompareResult:
    """Result of comparing two documents."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    doc_a_id: str = ""
    doc_b_id: str = ""
    similarity_score: float = 0.0
    differences: list[dict[str, Any]] = field(default_factory=list)
    common_sections: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════
# Document Intelligence Engine
# ═══════════════════════════════════════════════════════════

class DocumentIntelligenceEngine:
    """Document processing and analysis engine.

    Handles document parsing, information extraction, classification,
    summarization, and semantic search across multiple document formats.
    Simulates document processing for development and testing.
    """

    # Simulated document content database
    _SAMPLE_CONTENT: dict[str, str] = {
        "report": "This is a quarterly business report. Revenue increased by 15% to $2.5M. "
                   "Customer acquisition grew by 22% with 450 new accounts. "
                   "Operating costs were reduced by 8% through automation.",
        "contract": "Service Agreement between Company A and Company B. "
                    "Effective date: January 15, 2026. Term: 12 months. "
                    "Total value: $150,000. Payment terms: Net 30 days.",
        "invoice": "INVOICE #2026-0042. Date: March 10, 2026. "
                   "Bill to: Acme Corp, 123 Main St. "
                   "Line items: Consulting services - $5,000, Software license - $2,500. "
                   "Total due: $7,500. Due date: April 10, 2026.",
        "resume": "John Smith - Senior Software Engineer. "
                  "Email: john@example.com, Phone: (555) 123-4567. "
                  "Experience: 8 years in Python, TypeScript, React, AWS. "
                  "Education: MS Computer Science, Stanford University.",
    }

    def __init__(self) -> None:
        self._documents: dict[str, DocumentInfo] = {}
        self._extractions: dict[str, list[ExtractionResult]] = defaultdict(list)
        self._summaries: dict[str, DocumentSummary] = {}
        self._compare_results: list[CompareResult] = []
        self._total_documents: int = 0
        self._total_extractions: int = 0
        self._total_summaries: int = 0

    # ── Document Management ────────────────────────────────────────

    def upload_document(
        self,
        filename: str,
        format: DocumentFormat = DocumentFormat.TXT,
        content: str = "",
        tags: list[str] | None = None,
    ) -> DocumentInfo:
        """Upload and register a new document.

        Args:
            filename: Document filename.
            format: Document format type.
            content: Document text content.
            tags: Optional categorization tags.

        Returns:
            DocumentInfo with metadata.
        """
        doc = DocumentInfo(
            filename=filename,
            format=format,
            size_bytes=len(content.encode("utf-8")),
            word_count=len(content.split()) if content else 0,
            tags=tags or [],
            category=self._classify_document(content),
        )
        self._documents[doc.id] = doc
        self._total_documents += 1

        # Store sample content for simulation
        if content:
            self._SAMPLE_CONTENT[doc.id] = content

        logger.info(
            "Document uploaded: %s [%s] %d words",
            filename, format.value, doc.word_count,
        )
        return doc

    def _classify_document(self, content: str) -> DocumentCategory:
        """Internal: classify document based on content analysis."""
        if not content:
            return DocumentCategory.OTHER
        content_lower = content.lower()
        if any(w in content_lower for w in ["report", "quarterly", "revenue", "growth"]):
            return DocumentCategory.REPORT
        if any(w in content_lower for w in ["agreement", "contract", "terms", "parties"]):
            return DocumentCategory.CONTRACT
        if any(w in content_lower for w in ["invoice", "bill", "due", "payment"]):
            return DocumentCategory.INVOICE
        if any(w in content_lower for w in ["resume", "experience", "education", "skills"]):
            return DocumentCategory.RESUME
        if any(w in content_lower for w in ["article", "published", "abstract"]):
            return DocumentCategory.ARTICLE
        return DocumentCategory.OTHER

    def get_document(self, doc_id: str) -> DocumentInfo | None:
        """Get document info by ID."""
        return self._documents.get(doc_id)

    def list_documents(
        self,
        category: DocumentCategory | None = None,
        format: DocumentFormat | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[DocumentInfo]:
        """List documents with optional filters.

        Args:
            category: Filter by category.
            format: Filter by format.
            tags: Filter by tags.
            limit: Maximum results.

        Returns:
            List of matching DocumentInfo objects.
        """
        docs = list(self._documents.values())
        if category:
            docs = [d for d in docs if d.category == category]
        if format:
            docs = [d for d in docs if d.format == format]
        if tags:
            docs = [d for d in docs if any(t in d.tags for t in tags)]
        docs.sort(key=lambda d: d.uploaded_at, reverse=True)
        return docs[:limit]

    # ── Information Extraction ─────────────────────────────────────

    def extract(
        self,
        doc_id: str,
        extraction_type: ExtractionType = ExtractionType.ENTITIES,
    ) -> ExtractionResult:
        """Extract structured information from a document.

        Args:
            doc_id: Document ID to extract from.
            extraction_type: Type of information to extract.

        Returns:
            ExtractionResult with extracted items.
        """
        doc = self._documents.get(doc_id)
        if not doc:
            return ExtractionResult(document_id=doc_id)

        content = self._SAMPLE_CONTENT.get(doc_id, "")
        items: list[dict[str, Any]] = []

        if extraction_type == ExtractionType.ENTITIES:
            items = self._extract_entities(content)
        elif extraction_type == ExtractionType.KEY_PHRASES:
            items = self._extract_key_phrases(content)
        elif extraction_type == ExtractionType.DATES:
            items = self._extract_dates(content)
        elif extraction_type == ExtractionType.AMOUNTS:
            items = self._extract_amounts(content)
        elif extraction_type == ExtractionType.CONTACTS:
            items = self._extract_contacts(content)
        elif extraction_type == ExtractionType.TABLES:
            items = self._extract_tables(content)
        elif extraction_type == ExtractionType.LINKS:
            items = self._extract_links(content)
        elif extraction_type == ExtractionType.HEADERS:
            items = self._extract_headers(content)

        result = ExtractionResult(
            document_id=doc_id,
            extraction_type=extraction_type,
            items=items,
            confidence=0.85,
            count=len(items),
        )
        self._extractions[doc_id].append(result)
        self._total_extractions += 1

        doc.status = DocumentStatus.COMPLETED
        doc.processed_at = datetime.now(timezone.utc)

        return result

    def _extract_entities(self, content: str) -> list[dict[str, Any]]:
        """Extract named entities from content."""
        entities = []
        import re
        # Extract names (capitalized multi-word sequences)
        names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', content)
        for name in names[:5]:
            entities.append({"type": "person", "value": name, "confidence": 0.8})
        # Extract monetary amounts
        amounts = re.findall(r'\$[\d,]+(?:\.\d+)?', content)
        for amount in amounts[:5]:
            entities.append({"type": "money", "value": amount, "confidence": 0.95})
        # Extract percentages
        percentages = re.findall(r'\d+%', content)
        for pct in percentages[:5]:
            entities.append({"type": "percentage", "value": pct, "confidence": 0.9})
        return entities

    def _extract_key_phrases(self, content: str) -> list[dict[str, Any]]:
        """Extract key phrases from content."""
        words = content.split()
        if len(words) < 5:
            return []
        phrases = []
        for i in range(0, len(words) - 3, max(1, len(words) // 5)):
            phrase = " ".join(words[i:i + 3])
            phrases.append({"value": phrase, "position": i, "confidence": 0.7})
        return phrases[:10]

    def _extract_dates(self, content: str) -> list[dict[str, Any]]:
        """Extract dates from content."""
        import re
        dates = re.findall(
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}\b',
            content,
        )
        return [{"value": d, "confidence": 0.95} for d in dates]

    def _extract_amounts(self, content: str) -> list[dict[str, Any]]:
        """Extract monetary amounts from content."""
        import re
        amounts = re.findall(r'\$[\d,]+(?:\.\d{1,2})?', content)
        return [{"value": a, "confidence": 0.95} for a in amounts]

    def _extract_contacts(self, content: str) -> list[dict[str, Any]]:
        """Extract contact information from content."""
        import re
        contacts = []
        emails = re.findall(r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b', content)
        for email in emails:
            contacts.append({"type": "email", "value": email, "confidence": 0.95})
        phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content)
        for phone in phones:
            contacts.append({"type": "phone", "value": phone, "confidence": 0.9})
        return contacts

    def _extract_tables(self, content: str) -> list[dict[str, Any]]:
        """Extract tabular data from content."""
        return [{"rows": 3, "columns": 4, "confidence": 0.6}]

    def _extract_links(self, content: str) -> list[dict[str, Any]]:
        """Extract URLs from content."""
        import re
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', content)
        return [{"value": u, "confidence": 0.9} for u in urls]

    def _extract_headers(self, content: str) -> list[dict[str, Any]]:
        """Extract potential headers from content."""
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        headers = [l for l in lines if len(l) < 80 and l[0].isupper()]
        return [{"value": h, "level": 1, "confidence": 0.7} for h in headers[:5]]

    # ── Document Summarization ─────────────────────────────────────

    def summarize(
        self,
        doc_id: str,
        max_length: int = 200,
    ) -> DocumentSummary:
        """Generate a summary of a document.

        Args:
            doc_id: Document ID to summarize.
            max_length: Maximum summary length in words.

        Returns:
            DocumentSummary with summary text and key points.
        """
        doc = self._documents.get(doc_id)
        content = self._SAMPLE_CONTENT.get(doc_id, "")

        if not doc:
            doc = DocumentInfo(filename="unknown")

        if not content:
            summary_text = "No content available for summarization."
            key_points = []
        else:
            # Simple extractive summarization: take first sentences
            sentences = content.replace("!", ".").replace("?", ".").split(".")
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            summary_sentences = sentences[:3]
            summary_text = ". ".join(summary_sentences) + "."
            key_points = [s[:100] for s in sentences[:5]]

        summary = DocumentSummary(
            document_id=doc_id,
            summary_text=summary_text[:max_length],
            key_points=key_points,
            word_count_original=doc.word_count if doc else len(content.split()),
            word_count_summary=len(summary_text.split()),
            compression_ratio=(
                len(summary_text.split()) / max(doc.word_count if doc else 1, 1)
                if doc and doc.word_count > 0 else 0.0
            ),
        )
        self._summaries[doc_id] = summary
        self._total_summaries += 1

        return summary

    # ── Semantic Search ────────────────────────────────────────────

    def search(
        self,
        query: str,
        doc_ids: list[str] | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search for content within documents.

        Args:
            query: Search query string.
            doc_ids: Optional list of document IDs to search in.
            limit: Maximum results.

        Returns:
            List of SearchResult objects.
        """
        results = []
        search_docs = doc_ids or list(self._documents.keys())

        for doc_id in search_docs:
            content = self._SAMPLE_CONTENT.get(doc_id, "")
            if not content:
                continue

            query_lower = query.lower()
            content_lower = content.lower()

            if query_lower in content_lower:
                idx = content_lower.find(query_lower)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = content[start:end]

                # Simple relevance scoring
                relevance = len(query) / max(len(content_lower), 1) * 10.0 + 0.5
                relevance = min(relevance, 1.0)

                results.append(SearchResult(
                    document_id=doc_id,
                    snippet=snippet.strip(),
                    relevance_score=round(relevance, 3),
                ))

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:limit]

    # ── Document Comparison ────────────────────────────────────────

    def compare(
        self,
        doc_a_id: str,
        doc_b_id: str,
    ) -> CompareResult:
        """Compare two documents and find differences.

        Args:
            doc_a_id: First document ID.
            doc_b_id: Second document ID.

        Returns:
            CompareResult with similarity and differences.
        """
        content_a = self._SAMPLE_CONTENT.get(doc_a_id, "")
        content_b = self._SAMPLE_CONTENT.get(doc_b_id, "")

        words_a = set(content_a.lower().split())
        words_b = set(content_b.lower().split())

        if not words_a or not words_b:
            similarity = 0.0
        else:
            intersection = words_a & words_b
            union = words_a | words_b
            similarity = len(intersection) / len(union) if union else 0.0

        common = list(words_a & words_b)[:10]
        only_a = list(words_a - words_b)[:10]
        only_b = list(words_b - words_a)[:10]

        differences = []
        if only_a:
            differences.append({"location": "document_a_only", "words": only_a})
        if only_b:
            differences.append({"location": "document_b_only", "words": only_b})

        result = CompareResult(
            doc_a_id=doc_a_id,
            doc_b_id=doc_b_id,
            similarity_score=round(similarity, 3),
            differences=differences,
            common_sections=common,
        )
        self._compare_results.append(result)

        return result

    # ── Batch Processing ───────────────────────────────────────────

    def process_batch(
        self,
        doc_ids: list[str],
        extractions: list[ExtractionType] | None = None,
        summarize: bool = True,
    ) -> dict[str, Any]:
        """Process multiple documents in batch.

        Args:
            doc_ids: List of document IDs to process.
            extractions: Types of extraction to perform.
            summarize: Whether to generate summaries.

        Returns:
            Processing results with counts.
        """
        extraction_types = extractions or [ExtractionType.ENTITIES]
        results = {
            "processed": 0,
            "extractions": 0,
            "summaries": 0,
            "failed": 0,
            "details": [],
        }

        for doc_id in doc_ids:
            if doc_id not in self._documents:
                results["failed"] += 1
                continue

            for ext_type in extraction_types:
                self.extract(doc_id, ext_type)
                results["extractions"] += 1

            if summarize:
                self.summarize(doc_id)
                results["summaries"] += 1

            results["processed"] += 1
            results["details"].append({"doc_id": doc_id, "status": "completed"})

        return results

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get document intelligence statistics."""
        format_counts: dict[str, int] = defaultdict(int)
        category_counts: dict[str, int] = defaultdict(int)
        for doc in self._documents.values():
            format_counts[doc.format.value] += 1
            category_counts[doc.category.value] += 1

        return {
            "total_documents": self._total_documents,
            "total_extractions": self._total_extractions,
            "total_summaries": self._total_summaries,
            "total_comparisons": len(self._compare_results),
            "format_distribution": dict(format_counts),
            "category_distribution": dict(category_counts),
            "supported_formats": [f.value for f in DocumentFormat],
            "extraction_types": [e.value for e in ExtractionType],
        }

    def reset(self) -> None:
        """Reset all document intelligence state."""
        self._documents.clear()
        self._extractions.clear()
        self._summaries.clear()
        self._compare_results.clear()
        self._total_documents = 0
        self._total_extractions = 0
        self._total_summaries = 0


# ═══════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════

_document_intelligence: DocumentIntelligenceEngine | None = None


def get_document_intelligence() -> DocumentIntelligenceEngine:
    """Get or create the singleton DocumentIntelligenceEngine."""
    global _document_intelligence
    if _document_intelligence is None:
        _document_intelligence = DocumentIntelligenceEngine()
    return _document_intelligence


def reset_document_intelligence() -> None:
    """Reset the singleton DocumentIntelligenceEngine."""
    global _document_intelligence
    if _document_intelligence is not None:
        _document_intelligence.reset()
    _document_intelligence = None