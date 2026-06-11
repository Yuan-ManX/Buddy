"""Buddy Agent Workspace — sandboxed file operations and code execution

Provides agents with a virtual workspace for file management, code execution,
and artifact storage. Supports isolated environments per agent.
"""
from __future__ import annotations
import os
import json
import uuid
import re
import shlex
import logging
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("buddy.workspace")


# Dangerous shell patterns that should be rejected
FORBIDDEN_SHELL_PATTERNS = [
    r"rm\s+-rf\s+/", r">\s*/dev/", r"mkfs\.", r"dd\s+if=",
    r"chmod\s+777", r"chown\s+-R", r"wget\s+.*\|.*sh", r"curl\s+.*\|.*sh",
    r"eval\s+", r"exec\s+", r"__import__", r"os\.system",
    r"subprocess\.", r"import\s+os", r"import\s+subprocess",
    r"fork\b", r"\.remove\(\)", r"\.unlink\(\)", r"shutil\.rmtree",
]


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

    def _validate_path(self, path: str) -> Path:
        """Validate and resolve a path within the workspace, preventing traversal."""
        safe_path = path.replace("..", "").lstrip("/")
        resolved = (self.base_dir / safe_path).resolve()
        base_real = os.path.realpath(str(self.base_dir))
        path_real = os.path.realpath(str(resolved))
        if not path_real.startswith(base_real):
            raise ValueError("Path traversal not allowed")
        return resolved

    def create_file(self, name: str, content: str, subdir: str = "") -> WorkspaceFile:
        """Create a new file in the workspace."""
        if len(content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File exceeds maximum size of {self.MAX_FILE_SIZE} bytes")

        ext = Path(name).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' not allowed")

        # Prevent path traversal attacks
        safe_subdir = subdir.replace("..", "").lstrip("/")
        dir_path = self.base_dir / safe_subdir if safe_subdir else self.base_dir
        base_real = os.path.realpath(str(self.base_dir))
        dir_real = os.path.realpath(str(dir_path.resolve()))
        if not dir_real.startswith(base_real):
            raise ValueError("Path traversal not allowed")
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / name
        file_real = os.path.realpath(str(file_path.resolve()))
        if not file_real.startswith(base_real):
            raise ValueError("Path traversal not allowed")
        rel_path = str(Path(file_real).relative_to(Path(base_real)))

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
        try:
            file_path = self._validate_path(path)
        except ValueError:
            return None
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
        try:
            file_path = self._validate_path(path)
        except ValueError:
            return None
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
        try:
            file_path = self._validate_path(path)
        except ValueError:
            return False
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
        """Execute a shell command safely in the workspace directory."""
        timeout = timeout or self.EXECUTION_TIMEOUT
        import time

        # Check for dangerous patterns
        for pattern in FORBIDDEN_SHELL_PATTERNS:
            if re.search(pattern, command):
                return ExecutionResult(
                    success=False,
                    error=f"Command rejected: dangerous pattern detected ({pattern})",
                    execution_time=0.0,
                )

        start = time.time()
        try:
            result = subprocess.run(
                shlex.split(command),
                shell=False,
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
            "total_files": len(files),
            "total_size": total_size,
            "languages": languages,
        }

    def create_project_from_template(self, template_name: str, project_name: str) -> dict:
        """Scaffold a project from a built-in template."""
        templates = {
            "python-package": {
                "files": {
                    "setup.py": "from setuptools import setup, find_packages\n\nsetup(\n    name='{name}',\n    version='0.1.0',\n    packages=find_packages(),\n    python_requires='>=3.9',\n)\n",
                    "README.md": "# {name}\n\nProject description.\n",
                    "{name}/__init__.py": "# {name} package\n__version__ = '0.1.0'\n",
                    "{name}/core.py": "\"\"\"Core module for {name}.\"\"\"\n\n\ndef main():\n    \"\"\"Entry point.\"\"\"\n    print('Hello from {name}!')\n\n\nif __name__ == '__main__':\n    main()\n",
                    "tests/__init__.py": "# Test package\n",
                    "tests/test_core.py": "\"\"\"Tests for core module.\"\"\"\nimport pytest\nfrom {name}.core import main\n\n\ndef test_main():\n    \"\"\"Verify main function runs without error.\"\"\"\n    main()\n",
                    ".gitignore": "__pycache__/\n*.pyc\n*.pyo\n.env\n.venv/\ndist/\n*.egg-info/\n.pytest_cache/\n",
                }
            },
            "react-component": {
                "files": {
                    "package.json": '{\n  "name": "{name}",\n  "version": "0.1.0",\n  "private": true,\n  "dependencies": {\n    "react": "^18.0.0",\n    "react-dom": "^18.0.0"\n  }\n}\n',
                    "src/index.tsx": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\n\nconst root = ReactDOM.createRoot(document.getElementById('root')!);\nroot.render(<React.StrictMode><App /></React.StrictMode>);\n",
                    "src/App.tsx": "import React from 'react';\n\nconst App: React.FC = () => {\n  return (\n    <div className=\"app\">\n      <h1>{name}</h1>\n      <p>Welcome to your new project.</p>\n    </div>\n  );\n};\n\nexport default App;\n",
                    "src/App.css": ".app {\n  font-family: system-ui, sans-serif;\n  max-width: 800px;\n  margin: 0 auto;\n  padding: 2rem;\n}\n",
                    "tsconfig.json": '{\n  "compilerOptions": {\n    "target": "ES2020",\n    "module": "ESNext",\n    "jsx": "react-jsx",\n    "strict": true,\n    "esModuleInterop": true,\n    "moduleResolution": "node"\n  }\n}\n',
                    ".gitignore": "node_modules/\ndist/\n.env\n*.log\n",
                }
            },
            "web-api": {
                "files": {
                    "main.py": "\"\"\"{name} API server.\"\"\"\nfrom fastapi import FastAPI\n\napp = FastAPI(title='{name}')\n\n\n@app.get('/')\nasync def root():\n    return {{'service': '{name}', 'status': 'running'}}\n\n\n@app.get('/health')\nasync def health():\n    return {{'status': 'healthy'}}\n",
                    "requirements.txt": "fastapi>=0.100.0\nuvicorn>=0.23.0\npydantic>=2.0.0\n",
                    "README.md": "# {name}\n\nFastAPI web service.\n\n## Run\n```bash\nuvicorn main:app --reload\n```\n",
                    ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n.venv/\n",
                }
            },
        }

        template = templates.get(template_name)
        if not template:
            available = list(templates.keys())
            return {"error": f"Unknown template: {template_name}", "available": available}

        created_files = []
        for file_path, content_template in template["files"].items():
            # Replace placeholders
            resolved_content = content_template.replace("{name}", project_name)
            resolved_path = file_path.replace("{name}", project_name)

            # Create subdirectory if needed
            if "/" in resolved_path:
                subdir = "/".join(resolved_path.split("/")[:-1])
                dir_path = self.base_dir / subdir
                dir_path.mkdir(parents=True, exist_ok=True)

            full_path = self.base_dir / resolved_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(resolved_content, encoding="utf-8")
            created_files.append(resolved_path)

        # Reload workspace files
        self._load_existing_files()
        logger.info(f"Project '{project_name}' created from template '{template_name}' with {len(created_files)} files")
        return {
            "template": template_name,
            "project": project_name,
            "files_created": len(created_files),
            "files": created_files,
        }

    def get_file_versions(self, path: str) -> list[dict]:
        """Get version history for a workspace file (simulated via content snapshots)."""
        # Simple versioning: return the current file as version 1
        # For real version control, integrate with git or a VCS
        wf = self.read_file(path)
        if not wf:
            return []
        return [{
            "version": 1,
            "size": wf.size,
            "language": wf.language,
            "updated_at": wf.updated_at,
        }]

    def export_project(self, target_dir: str) -> dict:
        """Export all workspace files to an external directory."""
        import shutil
        target = Path(target_dir).expanduser()
        if target.exists():
            return {"error": f"Target directory already exists: {target_dir}"}

        try:
            shutil.copytree(self.base_dir, target)
            return {
                "source": str(self.base_dir),
                "target": str(target),
                "files_copied": len(self.list_files()),
            }
        except Exception as e:
            return {"error": str(e)}

    def cleanup(self):
        """Remove all workspace files."""
        import shutil
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            self._files.clear()
            logger.info(f"Workspace cleaned up for agent {self.agent_id}")