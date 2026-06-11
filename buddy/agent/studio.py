"""Buddy Studio — Project workspace system with white-box memory management.

Provides complete workspace isolation inspired by PilotDeck's WorkSpace model.
Each studio has its own file system, memory store, skill set, and runtime
environment. Memory is white-box: fully visible, editable, traceable, and
rollback-capable.

Features:
- Workspace-level isolation (files, memory, skills, runtimes)
- White-box memory with full CRUD and version history
- Memory rollback with snapshot diff comparison
- Project templates for rapid workspace creation
- Cross-workspace memory search and linking
- Workspace analytics (activity, cost, memory growth)
- Import/export workspace snapshots

Architecture:
    BuddyStudio (singleton)
    ├── StudioRegistry (workspace CRUD)
    ├── WhiteBoxMemory (editable memory store)
    ├── MemorySnapshotter (versioning + rollback)
    ├── TemplateLibrary (project templates)
    └── StudioAnalyzer (analytics + insights)
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("buddy.studio")


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════════════

class StudioStatus(str, Enum):
    """Lifecycle states for a studio workspace."""
    CREATING = "creating"
    ACTIVE = "active"
    ARCHIVED = "archived"
    HIBERNATING = "hibernating"
    DESTROYED = "destroyed"


class MemoryCategory(str, Enum):
    """Categories for white-box memory entries."""
    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    LEARNED_SKILL = "learned_skill"
    CONTEXT = "context"
    PATTERN = "pattern"
    GOAL = "goal"
    CONSTRAINT = "constraint"
    RELATIONSHIP = "relationship"
    CUSTOM = "custom"


class MemoryImportance(str, Enum):
    """Importance levels for memory retention."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    PINNED = "pinned"


@dataclass
class MemoryEntry:
    """A single white-box memory entry — fully visible, editable, and traceable."""
    id: str = field(default_factory=lambda: f"mem-{uuid.uuid4().hex[:12]}")
    studio_id: str = ""
    category: MemoryCategory = MemoryCategory.FACT
    importance: MemoryImportance = MemoryImportance.MEDIUM
    key: str = ""
    value: str = ""
    source: str = ""  # How this memory was created (agent, user, inference, etc.)
    tags: list[str] = field(default_factory=list)
    context: str = ""  # Conversation context when memory was created
    confidence: float = 1.0
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str = ""  # Optional TTL
    is_pinned: bool = False
    is_archived: bool = False
    edit_history: list[dict[str, Any]] = field(default_factory=list)
    linked_entries: list[str] = field(default_factory=list)


@dataclass
class MemorySnapshot:
    """A point-in-time snapshot of studio memory for rollback."""
    id: str = field(default_factory=lambda: f"snap-{uuid.uuid4().hex[:12]}")
    studio_id: str = ""
    label: str = ""
    description: str = ""
    entries: list[MemoryEntry] = field(default_factory=list)
    entry_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_auto: bool = False


@dataclass
class StudioInfo:
    """Metadata for a studio workspace."""
    id: str = field(default_factory=lambda: f"studio-{uuid.uuid4().hex[:12]}")
    name: str = "New Studio"
    description: str = ""
    status: StudioStatus = StudioStatus.CREATING
    base_dir: str = ""  # File system root for this studio
    icon: str = "📁"
    tags: list[str] = field(default_factory=list)
    template: str = ""  # Which template was used to create it
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active_agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "base_dir": self.base_dir,
            "icon": self.icon,
            "tags": self.tags,
            "template": self.template,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "active_agents": self.active_agents,
        }


# ═══════════════════════════════════════════════════════════════════════════
# White-Box Memory Store
# ═══════════════════════════════════════════════════════════════════════════

class WhiteBoxMemory:
    """Fully transparent, editable memory store with version history.

    Every memory entry is visible, can be inspected, edited, or rolled back.
    Provides full traceability from creation to retrieval.
    """

    def __init__(self, studio_id: str):
        self.studio_id = studio_id
        self._entries: dict[str, MemoryEntry] = {}

    # ── CRUD Operations ──

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        entry.studio_id = self.studio_id
        self._entries[entry.id] = entry
        logger.debug(f"Memory added: {entry.id} ({entry.key})")
        return entry

    def get(self, entry_id: str) -> MemoryEntry | None:
        return self._entries.get(entry_id)

    def get_by_key(self, key: str) -> list[MemoryEntry]:
        return [e for e in self._entries.values() if e.key == key and not e.is_archived]

    def update(self, entry_id: str, **kwargs: Any) -> MemoryEntry | None:
        entry = self._entries.get(entry_id)
        if not entry:
            return None

        # Record edit history
        edit_record = {
            "version": entry.version,
            "previous_value": entry.value,
            "previous_category": entry.category.value,
            "previous_importance": entry.importance.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        entry.edit_history.append(edit_record)

        # Apply updates
        for key, val in kwargs.items():
            if hasattr(entry, key):
                if isinstance(val, str) and key in ("category", "importance"):
                    enum_cls = MemoryCategory if key == "category" else MemoryImportance
                    setattr(entry, key, enum_cls(val))
                else:
                    setattr(entry, key, val)

        entry.version += 1
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        return entry

    def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def archive(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            entry.is_archived = True
            entry.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def pin(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            entry.is_pinned = True
            entry.importance = MemoryImportance.PINNED
            entry.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def unpin(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry:
            entry.is_pinned = False
            entry.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    # ── Queries ──

    def list_all(self, include_archived: bool = False) -> list[MemoryEntry]:
        entries = self._entries.values()
        if not include_archived:
            entries = [e for e in entries if not e.is_archived]
        return sorted(entries, key=lambda e: e.updated_at, reverse=True)

    def list_by_category(self, category: MemoryCategory) -> list[MemoryEntry]:
        return [e for e in self._entries.values() if e.category == category and not e.is_archived]

    def list_by_importance(self, importance: MemoryImportance) -> list[MemoryEntry]:
        return [e for e in self._entries.values() if e.importance == importance and not e.is_archived]

    def list_by_tag(self, tag: str) -> list[MemoryEntry]:
        return [e for e in self._entries.values() if tag in e.tags and not e.is_archived]

    def list_pinned(self) -> list[MemoryEntry]:
        return [e for e in self._entries.values() if e.is_pinned]

    def search(self, query: str) -> list[MemoryEntry]:
        """Simple keyword search across keys, values, and tags."""
        query_lower = query.lower()
        results = []
        for e in self._entries.values():
            if e.is_archived:
                continue
            if (query_lower in e.key.lower() or
                query_lower in e.value.lower() or
                any(query_lower in t.lower() for t in e.tags)):
                results.append(e)
        return sorted(results, key=lambda e: e.updated_at, reverse=True)

    def get_linked_entries(self, entry_id: str) -> list[MemoryEntry]:
        entry = self._entries.get(entry_id)
        if not entry:
            return []
        return [self._entries[eid] for eid in entry.linked_entries if eid in self._entries]

    def link_entries(self, entry_a_id: str, entry_b_id: str) -> bool:
        a, b = self._entries.get(entry_a_id), self._entries.get(entry_b_id)
        if not a or not b:
            return False
        if entry_b_id not in a.linked_entries:
            a.linked_entries.append(entry_b_id)
        if entry_a_id not in b.linked_entries:
            b.linked_entries.append(entry_a_id)
        return True

    # ── Stats ──

    def get_stats(self) -> dict[str, Any]:
        entries = list(self._entries.values())
        active = [e for e in entries if not e.is_archived]
        pinned = [e for e in active if e.is_pinned]

        category_counts: dict[str, int] = {}
        for e in active:
            cat = e.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_entries": len(entries),
            "active_entries": len(active),
            "archived_entries": len(entries) - len(active),
            "pinned_entries": len(pinned),
            "by_category": category_counts,
            "total_versions": sum(e.version for e in entries),
        }

    # ── Export/Import ──

    def export_entries(self) -> list[dict[str, Any]]:
        return [
            {
                "id": e.id,
                "key": e.key,
                "value": e.value,
                "category": e.category.value,
                "importance": e.importance.value,
                "source": e.source,
                "tags": e.tags,
                "context": e.context,
                "confidence": e.confidence,
                "version": e.version,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
                "is_pinned": e.is_pinned,
                "linked_entries": e.linked_entries,
            }
            for e in self._entries.values()
        ]

    def import_entries(self, data: list[dict[str, Any]]) -> int:
        count = 0
        for item in data:
            entry = MemoryEntry(
                id=item.get("id", f"mem-{uuid.uuid4().hex[:12]}"),
                studio_id=self.studio_id,
                key=item.get("key", ""),
                value=item.get("value", ""),
                category=MemoryCategory(item.get("category", "fact")),
                importance=MemoryImportance(item.get("importance", "medium")),
                source=item.get("source", "import"),
                tags=item.get("tags", []),
                context=item.get("context", ""),
                confidence=item.get("confidence", 1.0),
                version=item.get("version", 1),
                created_at=item.get("created_at", ""),
                is_pinned=item.get("is_pinned", False),
                linked_entries=item.get("linked_entries", []),
            )
            self._entries[entry.id] = entry
            count += 1
        return count


# ═══════════════════════════════════════════════════════════════════════════
# Memory Snapshotter (Versioning & Rollback)
# ═══════════════════════════════════════════════════════════════════════════

class MemorySnapshotter:
    """Manages memory snapshots for versioning and rollback.

    Inspired by PilotDeck's one-click rollback for Dream Mode.
    """

    def __init__(self):
        self._snapshots: dict[str, list[MemorySnapshot]] = {}  # studio_id -> snapshots

    def create_snapshot(
        self,
        memory: WhiteBoxMemory,
        label: str = "",
        description: str = "",
        is_auto: bool = False,
    ) -> MemorySnapshot:
        """Create a point-in-time snapshot of all memory entries."""
        entries_copy = copy.deepcopy(list(memory._entries.values()))
        snap = MemorySnapshot(
            studio_id=memory.studio_id,
            label=label or f"Snapshot {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            description=description,
            entries=entries_copy,
            entry_count=len(entries_copy),
            is_auto=is_auto,
        )
        self._snapshots.setdefault(memory.studio_id, []).append(snap)
        logger.info(f"Memory snapshot created: {snap.id} ({snap.entry_count} entries)")
        return snap

    def list_snapshots(self, studio_id: str) -> list[MemorySnapshot]:
        return [(s, i) for i, s in enumerate(self._snapshots.get(studio_id, []))]

    def get_snapshot(self, snapshot_id: str) -> MemorySnapshot | None:
        for snaps in self._snapshots.values():
            for snap in snaps:
                if snap.id == snapshot_id:
                    return snap
        return None

    def rollback(self, memory: WhiteBoxMemory, snapshot_id: str) -> bool:
        """Roll back memory to a previous snapshot state."""
        snap = self.get_snapshot(snapshot_id)
        if not snap:
            return False

        # Create safety snapshot before rollback
        self.create_snapshot(memory, label="Pre-rollback safety snapshot", is_auto=True)

        # Restore entries
        memory._entries.clear()
        for entry in snap.entries:
            restored = copy.deepcopy(entry)
            restored.updated_at = datetime.now(timezone.utc).isoformat()
            memory._entries[restored.id] = restored

        logger.info(f"Memory rolled back to snapshot: {snapshot_id}")
        return True

    def compare_snapshots(self, snap_a_id: str, snap_b_id: str) -> dict[str, Any]:
        """Compare two snapshots and return the diff."""
        snap_a = self.get_snapshot(snap_a_id)
        snap_b = self.get_snapshot(snap_b_id)
        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}

        ids_a = {e.id for e in snap_a.entries}
        ids_b = {e.id for e in snap_b.entries}

        return {
            "snapshot_a": {"id": snap_a.id, "label": snap_a.label, "count": snap_a.entry_count},
            "snapshot_b": {"id": snap_b.id, "label": snap_b.label, "count": snap_b.entry_count},
            "added": list(ids_b - ids_a),
            "removed": list(ids_a - ids_b),
            "modified": list(ids_a & ids_b),
            "unchanged_count": len(ids_a & ids_b),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Template Library
# ═══════════════════════════════════════════════════════════════════════════

class TemplateLibrary:
    """Library of project templates for rapid studio creation."""

    _TEMPLATES: dict[str, dict[str, Any]] = {
        "python-project": {
            "name": "Python Project",
            "description": "Standard Python project with venv, pytest, and linting",
            "icon": "🐍",
            "tags": ["python", "development"],
            "files": {
                "pyproject.toml": '[project]\nname = "my-project"\nversion = "0.1.0"\nrequires-python = ">=3.10"\n',
                "README.md": "# My Project\n\nProject description here.\n",
                "src/main.py": '"""Main entry point."""\n\ndef main():\n    print("Hello from My Project!")\n\nif __name__ == "__main__":\n    main()\n',
                "tests/test_main.py": '"""Tests for main module."""\n\ndef test_main():\n    assert True\n',
            },
        },
        "react-app": {
            "name": "React Application",
            "description": "React + TypeScript application with Vite",
            "icon": "⚛️",
            "tags": ["react", "typescript", "frontend"],
            "files": {
                "package.json": '{"name": "my-app", "private": true, "version": "0.1.0", "scripts": {"dev": "vite", "build": "tsc && vite build"}}\n',
                "src/App.tsx": 'import React from "react";\n\nexport default function App() {\n  return <div>Hello from React!</div>;\n}\n',
                "src/main.tsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")!).render(<App />);\n',
            },
        },
        "api-server": {
            "name": "API Server",
            "description": "FastAPI REST API server with SQLite",
            "icon": "🔌",
            "tags": ["api", "python", "backend"],
            "files": {
                "main.py": 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/")\ndef root():\n    return {"message": "API Server is running"}\n',
                "requirements.txt": "fastapi\nuvicorn\n",
            },
        },
        "data-analysis": {
            "name": "Data Analysis",
            "description": "Jupyter-based data analysis workspace",
            "icon": "📊",
            "tags": ["data", "python", "analysis"],
            "files": {
                "analysis.ipynb": '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}\n',
                "data/.gitkeep": "",
                "charts/.gitkeep": "",
            },
        },
        "blog-writing": {
            "name": "Blog Writing",
            "description": "Content writing workspace with drafts and published folders",
            "icon": "✍️",
            "tags": ["writing", "content", "blog"],
            "files": {
                "drafts/.gitkeep": "",
                "published/.gitkeep": "",
                "images/.gitkeep": "",
                "style-guide.md": "# Style Guide\n\nTone: Professional yet approachable\nTarget audience: Technical professionals\n",
            },
        },
        "research-lab": {
            "name": "Research Lab",
            "description": "Research workspace with notes, papers, and experiments",
            "icon": "🔬",
            "tags": ["research", "academic", "notes"],
            "files": {
                "notes/.gitkeep": "",
                "papers/.gitkeep": "",
                "experiments/.gitkeep": "",
                "bibliography.md": "# Bibliography\n\n",
                "research-plan.md": "# Research Plan\n\n",
            },
        },
    }

    @classmethod
    def list_templates(cls) -> list[dict[str, Any]]:
        return [
            {"id": tid, "name": t["name"], "description": t["description"],
             "icon": t["icon"], "tags": t["tags"]}
            for tid, t in cls._TEMPLATES.items()
        ]

    @classmethod
    def get_template(cls, template_id: str) -> dict[str, Any] | None:
        return cls._TEMPLATES.get(template_id)

    @classmethod
    def apply_template(cls, template_id: str, target_dir: str) -> dict[str, str]:
        """Create project files from a template in the target directory."""
        template = cls.get_template(template_id)
        if not template:
            return {}

        created_files: dict[str, str] = {}
        for file_path, content in template["files"].items():
            full_path = os.path.join(target_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)
            created_files[file_path] = full_path

        logger.info(f"Template '{template_id}' applied to {target_dir}: {len(created_files)} files")
        return created_files


# ═══════════════════════════════════════════════════════════════════════════
# Studio Analyzer
# ═══════════════════════════════════════════════════════════════════════════

class StudioAnalyzer:
    """Provides analytics and insights for studio workspaces."""

    def analyze_memory(self, memory: WhiteBoxMemory) -> dict[str, Any]:
        """Generate memory analytics report."""
        entries = memory.list_all()

        if not entries:
            return {"total": 0, "message": "No memory entries"}

        categories: dict[str, int] = {}
        imports: dict[str, int] = {}
        tags: dict[str, int] = {}
        total_confidence = 0.0

        for e in entries:
            categories[e.category.value] = categories.get(e.category.value, 0) + 1
            imports[e.importance.value] = imports.get(e.importance.value, 0) + 1
            for tag in e.tags:
                tags[tag] = tags.get(tag, 0) + 1
            total_confidence += e.confidence

        # Age analysis
        now = datetime.now(timezone.utc)
        ages_hours = []
        for e in entries:
            try:
                created = datetime.fromisoformat(e.created_at)
                age = (now - created).total_seconds() / 3600
                ages_hours.append(age)
            except Exception:
                ages_hours.append(0)

        return {
            "total": len(entries),
            "avg_confidence": round(total_confidence / len(entries), 3) if entries else 0,
            "by_category": categories,
            "by_importance": imports,
            "top_tags": dict(sorted(tags.items(), key=lambda x: -x[1])[:10]),
            "age": {
                "newest_hours": round(min(ages_hours), 1),
                "oldest_hours": round(max(ages_hours), 1),
                "avg_age_hours": round(sum(ages_hours) / len(ages_hours), 1),
            },
            "pinned_count": len(memory.list_pinned()),
        }

    def analyze_studio(self, studio: "StudioInfo", memory: "WhiteBoxMemory") -> dict[str, Any]:
        """Generate comprehensive studio analytics."""
        return {
            "studio": studio.to_dict(),
            "memory": self.analyze_memory(memory),
            "files": self._analyze_files(studio.base_dir),
        }

    def _analyze_files(self, base_dir: str) -> dict[str, Any]:
        """Analyze file system in the studio directory."""
        if not base_dir or not os.path.isdir(base_dir):
            return {"total_files": 0, "total_size_bytes": 0}

        total_files = 0
        total_size = 0
        extensions: dict[str, int] = {}

        for root, dirs, files in os.walk(base_dir):
            # Skip hidden and venv directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__" and d != "node_modules"]
            for f in files:
                if f.startswith("."):
                    continue
                total_files += 1
                fpath = os.path.join(root, f)
                try:
                    size = os.path.getsize(fpath)
                    total_size += size
                except OSError:
                    continue
                ext = os.path.splitext(f)[1] or "(no ext)"
                extensions[ext] = extensions.get(ext, 0) + 1

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": dict(sorted(extensions.items(), key=lambda x: -x[1])[:10]),
        }


# ═══════════════════════════════════════════════════════════════════════════
# Studio Registry
# ═══════════════════════════════════════════════════════════════════════════

class StudioRegistry:
    """Manages studio workspace lifecycle."""

    def __init__(self):
        self._studios: dict[str, StudioInfo] = {}
        self._memories: dict[str, WhiteBoxMemory] = {}
        self._base_path = os.path.join(tempfile.gettempdir(), "buddy-studios")

    def create_studio(
        self,
        name: str,
        description: str = "",
        template_id: str = "",
        icon: str = "📁",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StudioInfo:
        """Create a new studio workspace."""
        studio = StudioInfo(
            name=name,
            description=description,
            template=template_id,
            icon=icon,
            tags=tags or [],
            metadata=metadata or {},
            status=StudioStatus.CREATING,
        )

        # Set up file system
        studio.base_dir = os.path.join(self._base_path, studio.id)
        os.makedirs(studio.base_dir, exist_ok=True)

        # Apply template if specified
        if template_id:
            TemplateLibrary.apply_template(template_id, studio.base_dir)

        # Initialize white-box memory
        memory = WhiteBoxMemory(studio.id)

        self._studios[studio.id] = studio
        self._memories[studio.id] = memory
        studio.status = StudioStatus.ACTIVE

        logger.info(f"Studio created: {studio.id} ({name}) at {studio.base_dir}")
        return studio

    def archive_studio(self, studio_id: str) -> bool:
        studio = self._studios.get(studio_id)
        if studio:
            studio.status = StudioStatus.ARCHIVED
            studio.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def destroy_studio(self, studio_id: str) -> bool:
        studio = self._studios.get(studio_id)
        if studio:
            studio.status = StudioStatus.DESTROYED
            # Remove file system
            if studio.base_dir and os.path.isdir(studio.base_dir):
                try:
                    shutil.rmtree(studio.base_dir)
                except Exception as e:
                    logger.warning(f"Failed to remove studio files: {e}")
            self._memories.pop(studio_id, None)
            return True
        return False

    def get_studio(self, studio_id: str) -> StudioInfo | None:
        return self._studios.get(studio_id)

    def get_memory(self, studio_id: str) -> WhiteBoxMemory | None:
        return self._memories.get(studio_id)

    def list_studios(self) -> list[StudioInfo]:
        return list(self._studios.values())


# ═══════════════════════════════════════════════════════════════════════════
# Buddy Studio Facade
# ═══════════════════════════════════════════════════════════════════════════

class BuddyStudio:
    """Central facade for studio workspace management.

    Usage:
        studio = BuddyStudio()
        ws = studio.create_studio(name="My Project", template_id="python-project")
        memory = studio.get_memory(ws.id)
        memory.add(MemoryEntry(key="project_type", value="web app"))
        snap = studio.snapshotter.create_snapshot(memory, label="Initial state")
        # ... make changes ...
        studio.snapshotter.rollback(memory, snap.id)
    """

    def __init__(self):
        self.registry = StudioRegistry()
        self.snapshotter = MemorySnapshotter()
        self.analyzer = StudioAnalyzer()

    def create_studio(self, **kwargs: Any) -> StudioInfo:
        return self.registry.create_studio(**kwargs)

    def get_studio(self, studio_id: str) -> StudioInfo | None:
        return self.registry.get_studio(studio_id)

    def get_memory(self, studio_id: str) -> WhiteBoxMemory | None:
        return self.registry.get_memory(studio_id)

    def list_studios(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.registry.list_studios()]

    def list_templates(self) -> list[dict[str, Any]]:
        return TemplateLibrary.list_templates()

    def analyze_studio(self, studio_id: str) -> dict[str, Any]:
        studio = self.registry.get_studio(studio_id)
        memory = self.registry.get_memory(studio_id)
        if not studio or not memory:
            return {"error": "Studio not found"}
        return self.analyzer.analyze_studio(studio, memory)

    def get_stats(self) -> dict[str, Any]:
        studios = self.registry.list_studios()
        total_entries = sum(
            len(m.list_all()) for m in self.registry._memories.values()
        )
        total_snapshots = sum(
            len(snaps) for snaps in self.snapshotter._snapshots.values()
        )

        return {
            "total_studios": len(studios),
            "active_studios": sum(1 for s in studios if s.status == StudioStatus.ACTIVE),
            "archived_studios": sum(1 for s in studios if s.status == StudioStatus.ARCHIVED),
            "total_memory_entries": total_entries,
            "total_snapshots": total_snapshots,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

buddy_studio = BuddyStudio()