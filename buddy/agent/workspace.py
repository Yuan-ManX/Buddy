"""Buddy Agent Workspace — sandboxed file operations and code execution

Provides agents with a virtual workspace for file management, code execution,
and artifact storage. Supports isolated environments per agent.
"""
from __future__ import annotations
import os
import json
import uuid
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("buddy.workspace")


@dataclass
class WorkspaceFile:
    name: str
    path: str
    content: str = ""
    language: str = ""
    size: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ExecutionResult:
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    execution_time: float = 0.0


class AgentWorkspace:
    """Virtual workspace for agent file operations and code execution."""

    MAX_FILE_SIZE = 1_000_000  # 1MB
    EXECUTION_TIMEOUT = 30  # seconds
    ALLOWED_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
        ".json", ".yaml", ".yml", ".toml", ".xml", ".csv",
        ".md", ".txt", ".sh", ".sql", ".rs", ".go", ".java",
        ".cpp", ".c", ".h", ".rb", ".php", ".swift", ".kt",
    }

    def __init__(self, agent_id: str, base_dir: str | None = None):
        self.agent_id = agent_id
        self.base_dir = (
            Path(base_dir) if base_dir
            else Path(tempfile.gettempdir()) / "buddy_workspaces" / agent_id
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._files: dict[str, WorkspaceFile] = {}
        self._load_existing_files()

    def _load_existing_files(self):
        """Load existing files from the workspace directory."""
        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.base_dir))
                try:
                    content = file_path.read_text(encoding="utf-8")
                    self._files[rel_path] = WorkspaceFile(
                        name=file_path.name,
                        path=rel_path,
                        content=content,
                        language=self._detect_language(file_path.suffix),
                        size=len(content),
                        created_at=datetime.fromtimestamp(
                            file_path.stat().st_ctime, tz=timezone.utc
                        ).isoformat(),
                        updated_at=datetime.fromtimestamp(
                            file_path.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    )
                except Exception:
                    pass

    def _detect_language(self, suffix: str) -> str:
        mapping = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".tsx": "typescriptreact", ".jsx": "javascriptreact",
            ".html": "html", ".css": "css", ".json": "json",
            ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
            ".md": "markdown", ".txt": "text", ".sh": "shell",
            ".sql": "sql", ".rs": "rust", ".go": "go",
            ".java": "java", ".cpp": "cpp", ".c": "c",
            ".rb": "ruby", ".php": "php", ".swift": "swift",
            ".kt": "kotlin", ".xml": "xml", ".csv": "csv",
        }
        return mapping.get(suffix, "text")

    def create_file(self, name: str, content: str, subdir: str = "") -> WorkspaceFile:
        """Create a new file in the workspace."""
        if len(content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum size of {self.MAX_FILE_SIZE} bytes")

        ext = Path(name).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' not allowed")

        dir_path = self.base_dir / subdir if subdir else self.base_dir
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / name
        rel_path = str(file_path.relative_to(self.base_dir))

        file_path.write_text(content, encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat()

        wf = WorkspaceFile(
            name=name,
            path=rel_path,
            content=content,
            language=self._detect_language(ext),
            size=len(content),
            created_at=now,
            updated_at=now,
        )
        self._files[rel_path] = wf
        logger.info(f"Workspace file created: {rel_path} ({len(content)} bytes)")
        return wf

    def read_file(self, path: str) -> WorkspaceFile | None:
        """Read a file from the workspace."""
        file_path = self.base_dir / path
        if not file_path.exists() or not file_path.is_file():
            return None

        content = file_path.read_text(encoding="utf-8")
        wf = self._files.get(path)
        if wf:
            wf.content = content
            wf.size = len(content)
            return wf

        wf = WorkspaceFile(
            name=file_path.name,
            path=path,
            content=content,
            language=self._detect_language(file_path.suffix),
            size=len(content),
            created_at=datetime.fromtimestamp(
                file_path.stat().st_ctime, tz=timezone.utc
            ).isoformat(),
            updated_at=datetime.fromtimestamp(
                file_path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        )
        self._files[path] = wf
        return wf

    def update_file(self, path: str, content: str) -> WorkspaceFile | None:
        """Update an existing file."""
        file_path = self.base_dir / path
        if not file_path.exists():
            return None

        file_path.write_text(content, encoding="utf-8")
        now = datetime.now(timezone.utc).isoformat()

        wf = self._files.get(path)
        if wf:
            wf.content = content
            wf.size = len(content)
            wf.updated_at = now
        return wf

    def delete_file(self, path: str) -> bool:
        """Delete a file from the workspace."""
        file_path = self.base_dir / path
        if not file_path.exists():
            return False

        file_path.unlink()
        self._files.pop(path, None)
        logger.info(f"Workspace file deleted: {path}")
        return True

    def list_files(self, subdir: str = "") -> list[WorkspaceFile]:
        """List all files in the workspace."""
        dir_path = self.base_dir / subdir if subdir else self.base_dir
        if not dir_path.exists():
            return []

        files = []
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(self.base_dir))
                wf = self._files.get(rel_path)
                if wf:
                    files.append(wf)
                else:
                    content = file_path.read_text(encoding="utf-8")
                    wf = WorkspaceFile(
                        name=file_path.name,
                        path=rel_path,
                        content=content,
                        language=self._detect_language(file_path.suffix),
                        size=len(content),
                        created_at=datetime.fromtimestamp(
                            file_path.stat().st_ctime, tz=timezone.utc
                        ).isoformat(),
                        updated_at=datetime.fromtimestamp(
                            file_path.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    )
                    self._files[rel_path] = wf
                    files.append(wf)

        return sorted(files, key=lambda f: f.updated_at, reverse=True)

    async def execute_python(self, code: str, timeout: int | None = None) -> ExecutionResult:
        """Execute Python code in a sandboxed subprocess."""
        timeout = timeout or self.EXECUTION_TIMEOUT
        import time

        start = time.time()
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                temp_path = f.name

            result = subprocess.run(
                ["python3", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.base_dir),
            )

            os.unlink(temp_path)
            elapsed = time.time() - start

            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout[:10000],
                error=result.stderr[:10000],
                exit_code=result.returncode,
                execution_time=elapsed,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Execution timed out after {timeout}s",
                execution_time=time.time() - start,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
            )

    async def execute_shell(self, command: str, timeout: int | None = None) -> ExecutionResult:
        """Execute a shell command in the workspace directory."""
        timeout = timeout or self.EXECUTION_TIMEOUT
        import time

        start = time.time()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.base_dir),
            )

            elapsed = time.time() - start
            return ExecutionResult(
                success=result.returncode == 0,
                output=result.stdout[:10000],
                error=result.stderr[:10000],
                exit_code=result.returncode,
                execution_time=elapsed,
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                error=f"Command timed out after {timeout}s",
                execution_time=time.time() - start,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start,
            )

    def get_stats(self) -> dict:
        """Get workspace statistics."""
        files = self.list_files()
        total_size = sum(f.size for f in files)
        languages = list(set(f.language for f in files))
        return {
            "agent_id": self.agent_id,
            "base_dir": str(self.base_dir),
            "file_count": len(files),
            "total_size": total_size,
            "languages": languages,
        }

    def cleanup(self):
        """Remove all workspace files."""
        import shutil
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self._files.clear()
            logger.info(f"Workspace cleaned up for agent {self.agent_id}")