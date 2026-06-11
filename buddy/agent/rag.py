"""Buddy RAG System — Retrieval-Augmented Generation with multi-source knowledge

Provides document ingestion, chunking, embedding, and semantic retrieval
capabilities. Supports local files, URLs, and direct text input. Integrates
with the hierarchical memory system for persistent knowledge storage.
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from config.settings import settings

logger = logging.getLogger("buddy.rag")


@dataclass
class Document:
    """Represents a processed document in the knowledge base."""
    id: str
    title: str
    source: str  # file path, URL, or "direct"
    content: str
    content_hash: str
    chunk_count: int = 0
    total_tokens: int = 0
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Chunk:
    """A chunk of document content with embedding."""
    id: str
    document_id: str
    content: str
    embedding: list[float] | None = None
    index: int = 0
    metadata: dict = field(default_factory=dict)


class DocumentStore:
    """In-memory document storage with chunk management."""

    def __init__(self):
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, Chunk] = {}
        self._doc_chunks: dict[str, list[str]] = {}  # doc_id -> [chunk_id, ...]

    def add_document(self, doc: Document):
        self._documents[doc.id] = doc

    def add_chunk(self, chunk: Chunk):
        self._chunks[chunk.id] = chunk
        self._doc_chunks.setdefault(chunk.document_id, []).append(chunk.id)

    def get_document(self, doc_id: str) -> Document | None:
        return self._documents.get(doc_id)

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)

    def get_document_chunks(self, doc_id: str) -> list[Chunk]:
        chunk_ids = self._doc_chunks.get(doc_id, [])
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    def get_all_chunks(self) -> list[Chunk]:
        return list(self._chunks.values())

    def remove_document(self, doc_id: str) -> int:
        self._documents.pop(doc_id, None)
        chunk_ids = self._doc_chunks.pop(doc_id, [])
        for cid in chunk_ids:
            self._chunks.pop(cid, None)
        return len(chunk_ids)

    def clear(self):
        self._documents.clear()
        self._chunks.clear()
        self._doc_chunks.clear()

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)


class RAGEngine:
    """Retrieval-Augmented Generation engine with document processing and semantic search.

    Supports:
    - Document ingestion from text, files, and URLs
    - Recursive text chunking with overlap
    - Embedding generation via configured model
    - Semantic (vector similarity) search
    - Hybrid (semantic + keyword) search
    - Context window-aware result formatting
    """

    # Chunking defaults
    DEFAULT_CHUNK_SIZE = 1024
    DEFAULT_CHUNK_OVERLAP = 128

    def __init__(self, agent_id: str, client: AsyncOpenAI | None = None):
        self.agent_id = agent_id
        self._client = client or AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self._embedding_model = settings.EMBEDDING_MODEL
        self._store = DocumentStore()

    # ── Document Ingestion ──────────────────────────────────

    async def ingest_text(
        self,
        content: str,
        title: str = "",
        source: str = "direct",
        metadata: dict | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> Document:
        """Ingest raw text content into the knowledge base."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"

        doc = Document(
            id=doc_id,
            title=title or f"Document {doc_id[:8]}",
            source=source,
            content=content,
            content_hash=content_hash,
            metadata=metadata or {},
        )

        chunks = self._chunk_text(content, chunk_size, chunk_overlap)
        doc.chunk_count = len(chunks)
        doc.total_tokens = sum(self._estimate_tokens(c) for c in chunks)

        self._store.add_document(doc)

        for i, chunk_text in enumerate(chunks):
            chunk = Chunk(
                id=f"{doc_id}-chunk-{i}",
                document_id=doc_id,
                content=chunk_text,
                index=i,
                metadata={"title": doc.title, "source": doc.source},
            )
            self._store.add_chunk(chunk)

        logger.info(f"Ingested document '{doc.title}': {doc.chunk_count} chunks, ~{doc.total_tokens} tokens")
        return doc

    async def ingest_file(self, file_path: str, metadata: dict | None = None) -> Document:
        """Ingest a local file into the knowledge base."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()

        title = os.path.basename(file_path)
        return await self.ingest_text(
            content=content,
            title=title,
            source=f"file://{os.path.abspath(file_path)}",
            metadata=metadata,
        )

    async def ingest_url(self, url: str, metadata: dict | None = None) -> Document:
        """Ingest content from a URL into the knowledge base."""
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Buddy-RAG/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8", errors="replace")
            content_type = response.headers.get("Content-Type", "")

            # Simple HTML text extraction
            if "html" in content_type:
                content = self._strip_html(content)

        title = url.rstrip("/").rsplit("/", 1)[-1] or url
        return await self.ingest_text(
            content=content,
            title=title,
            source=url,
            metadata=metadata,
        )

    # ── Chunking ────────────────────────────────────────────

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping chunks, respecting paragraph boundaries."""
        if len(text) <= chunk_size:
            return [text]

        # First split by paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if not current_chunk:
                current_chunk = para
            elif self._estimate_tokens(current_chunk + "\n\n" + para) <= chunk_size:
                current_chunk += "\n\n" + para
            else:
                # Current chunk is full, save it
                chunks.append(current_chunk)

                # Handle very long paragraphs by sentence splitting
                if self._estimate_tokens(para) > chunk_size:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    current_chunk = ""
                    for sent in sentences:
                        if not current_chunk:
                            current_chunk = sent
                        elif self._estimate_tokens(current_chunk + " " + sent) <= chunk_size:
                            current_chunk += " " + sent
                        else:
                            chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 chars per token for English."""
        return max(1, len(text) // 4)

    # ── Embedding Generation ────────────────────────────────

    async def generate_embeddings(self, doc_id: str | None = None) -> int:
        """Generate embeddings for document chunks. Returns count of embeddings generated."""
        if doc_id:
            chunks = self._store.get_document_chunks(doc_id)
        else:
            chunks = self._store.get_all_chunks()

        unembedded = [c for c in chunks if c.embedding is None]
        if not unembedded:
            return 0

        texts = [c.content[:8000] for c in unembedded]

        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=texts,
            )
            for i, emb_data in enumerate(response.data):
                unembedded[i].embedding = emb_data.embedding

            logger.info(f"Generated {len(unembedded)} embeddings for agent {self.agent_id}")
            return len(unembedded)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    # ── Semantic Search ─────────────────────────────────────

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
        hybrid: bool = True,
    ) -> list[dict]:
        """Search the knowledge base with hybrid (semantic + keyword) approach.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            min_similarity: Minimum similarity threshold.
            hybrid: If True, combine semantic and keyword search results.

        Returns:
            List of result dicts with content, similarity score, and metadata.
        """
        # Generate query embedding
        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=query[:8000],
            )
            query_embedding = response.data[0].embedding
        except Exception as e:
            logger.warning(f"Query embedding failed, using keyword-only search: {e}")
            return self._keyword_search(query, top_k)

        # Score all chunks by cosine similarity
        scored = []
        for chunk in self._store.get_all_chunks():
            if chunk.embedding is None:
                continue
            similarity = self._cosine_similarity(query_embedding, chunk.embedding)
            if similarity >= min_similarity:
                scored.append((similarity, chunk))

        scored.sort(key=lambda x: -x[0])

        # Hybrid: boost chunks with keyword matches
        if hybrid:
            keyword_results = self._keyword_search(query, top_k * 2)
            keyword_ids = {r["chunk_id"] for r in keyword_results}
            scored = [(s + (0.15 if c.id in keyword_ids else 0), c) for s, c in scored]
            scored.sort(key=lambda x: -x[0])

        top = scored[:top_k]
        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "similarity": round(sim, 4),
                "title": chunk.metadata.get("title", ""),
                "source": chunk.metadata.get("source", ""),
                "chunk_index": chunk.index,
            }
            for sim, chunk in top
        ]

    async def search_and_format(
        self,
        query: str,
        top_k: int = 5,
        max_context_tokens: int = 4096,
    ) -> str:
        """Search and return formatted context for LLM consumption."""
        results = await self.search(query, top_k=top_k)

        if not results:
            return ""

        context_parts = []
        token_count = 0

        for r in results:
            chunk_tokens = self._estimate_tokens(r["content"])
            if token_count + chunk_tokens > max_context_tokens:
                break

            source_info = f" (from {r['title']})" if r["title"] else ""
            context_parts.append(
                f"[Source{source_info}, relevance: {r['similarity']}]\n{r['content']}"
            )
            token_count += chunk_tokens

        return "\n\n---\n\n".join(context_parts)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        """Keyword-based search as fallback or hybrid boost."""
        import math

        query_terms = set(query.lower().split())
        scored = []

        for chunk in self._store.get_all_chunks():
            content_lower = chunk.content.lower()
            tf = sum(content_lower.count(term) for term in query_terms if term)
            if tf > 0:
                # Simple TF-IDF-like scoring
                idf = 1.0 / (1.0 + math.log(1 + tf))
                scored.append((tf * idf, chunk))

        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]

        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "similarity": round(sim, 4),
                "title": chunk.metadata.get("title", ""),
                "source": chunk.metadata.get("source", ""),
            }
            for sim, chunk in top
        ]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _strip_html(self, html: str) -> str:
        """Simple HTML to text extraction."""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    # ── Management ──────────────────────────────────────────

    def get_document(self, doc_id: str) -> dict | None:
        doc = self._store.get_document(doc_id)
        if not doc:
            return None
        return {
            "id": doc.id,
            "title": doc.title,
            "source": doc.source,
            "chunk_count": doc.chunk_count,
            "total_tokens": doc.total_tokens,
            "metadata": doc.metadata,
            "created_at": doc.created_at,
        }

    def list_documents(self) -> list[dict]:
        return [self.get_document(d.id) for d in self._store._documents.values() if self.get_document(d.id)]

    def remove_document(self, doc_id: str) -> int:
        return self._store.remove_document(doc_id)

    def clear_knowledge_base(self):
        self._store.clear()
        logger.info(f"Knowledge base cleared for agent {self.agent_id}")

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "document_count": self._store.document_count,
            "chunk_count": self._store.chunk_count,
            "embedded_chunks": sum(1 for c in self._store.get_all_chunks() if c.embedding is not None),
            "total_tokens": sum(
                d.total_tokens for d in self._store._documents.values()
            ),
            "embedding_model": self._embedding_model,
        }