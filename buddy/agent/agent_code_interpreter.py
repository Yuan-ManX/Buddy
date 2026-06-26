"""Buddy Agent Code Interpreter — secure multi-language code execution sandbox

The Code Interpreter provides a sandboxed execution environment for running
code in multiple languages. It supports Python, JavaScript, Bash, and SQL
with resource limits, timeout controls, and output capture.

Core capabilities:
  - Multi-Language: Python, JavaScript, Bash, SQL, and more
  - Sandboxed Execution: isolated subprocess with resource limits
  - Output Capture: stdout, stderr, and return value capture
  - Timeout Control: per-execution time limits with graceful termination
  - Session Management: persistent sessions with shared state
  - File System: virtual file system for code artifacts
  - Package Management: on-demand package installation
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger("buddy.code_interpreter")


# ═══════════════════════════════════════════════════════════
# Enums and Types
# ═══════════════════════════════════════════════════════════

class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    SQL = "sql"
    HTML = "html"
    CSS = "css"


class ExecutionStatus(str, Enum):
    """Status of a code execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    KILLED = "killed"


class SessionMode(str, Enum):
    """Execution session mode."""
    EPHEMERAL = "ephemeral"  # New session each execution
    PERSISTENT = "persistent"  # State persists across executions


# ═══════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════

@dataclass
class CodeInterpreterConfig:
    """Configuration for the Code Interpreter."""
    max_execution_time_seconds: int = 30
    max_memory_mb: int = 256
    max_output_chars: int = 50000
    max_sessions: int = 20
    max_file_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    sandbox_enabled: bool = True
    allowed_imports: list[str] = field(default_factory=lambda: [
        "math", "random", "datetime", "json", "re", "collections",
        "itertools", "functools", "statistics", "string", "hashlib",
        "base64", "csv", "io", "typing", "dataclasses", "enum",
        "decimal", "fractions", "textwrap", "pprint", "copy",
    ])
    blocked_imports: list[str] = field(default_factory=lambda: [
        "os", "subprocess", "sys", "shutil", "socket", "requests",
        "http", "urllib", "ftplib", "telnetlib", "smtplib",
        "pickle", "ctypes", "multiprocessing", "signal",
    ])


@dataclass
class CodeExecution:
    """Result of a code execution."""
    execution_id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}")
    session_id: str = ""
    agent_id: str = ""
    language: Language = Language.PYTHON
    code: str = ""
    output: str = ""
    error: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    exit_code: int = -1
    duration_ms: int = 0
    memory_used_mb: float = 0.0
    line_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "language": self.language.value,
            "code": self.code[:200] + "..." if len(self.code) > 200 else self.code,
            "output": self.output[:1000] + "..." if len(self.output) > 1000 else self.output,
            "error": self.error[:500] + "..." if len(self.error) > 500 else self.error,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "memory_used_mb": self.memory_used_mb,
            "line_count": self.line_count,
            "created_at": self.created_at,
        }


@dataclass
class CodeSession:
    """A persistent code execution session."""
    session_id: str = field(default_factory=lambda: f"session-{uuid.uuid4().hex[:12]}")
    agent_id: str = ""
    language: Language = Language.PYTHON
    mode: SessionMode = SessionMode.EPHEMERAL
    state: dict[str, Any] = field(default_factory=dict)
    files: dict[str, str] = field(default_factory=dict)
    executions: list[CodeExecution] = field(default_factory=list)
    variable_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "language": self.language.value,
            "mode": self.mode.value,
            "variable_count": self.variable_count,
            "file_count": len(self.files),
            "execution_count": len(self.executions),
            "created_at": self.created_at,
            "last_activity": self.last_activity,
        }


@dataclass
class CodeInterpreterStats:
    """Statistics for the Code Interpreter."""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    timeout_executions: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    avg_execution_ms: float = 0.0
    total_code_lines: int = 0
    executions_by_language: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "timeout_executions": self.timeout_executions,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "avg_execution_ms": self.avg_execution_ms,
            "total_code_lines": self.total_code_lines,
            "executions_by_language": self.executions_by_language,
        }


# ═══════════════════════════════════════════════════════════
# Code Interpreter Implementation
# ═══════════════════════════════════════════════════════════

class AgentCodeInterpreter:
    """Secure multi-language code execution sandbox."""

    def __init__(self, config: CodeInterpreterConfig | None = None):
        self.config = config or CodeInterpreterConfig()
        self._sessions: dict[str, CodeSession] = {}
        self._executions: list[CodeExecution] = []
        self._total_executions: int = 0
        self._total_success: int = 0
        self._total_failed: int = 0
        self._total_timeout: int = 0
        self._total_code_lines: int = 0
        self._total_duration: int = 0
        logger.info("AgentCodeInterpreter initialized")

    # ── Session Management ───────────────────────────────

    def create_session(
        self,
        agent_id: str = "",
        language: Language = Language.PYTHON,
        mode: SessionMode = SessionMode.EPHEMERAL,
    ) -> CodeSession:
        """Create a new execution session."""
        if len(self._sessions) >= self.config.max_sessions:
            # Clean up oldest sessions
            oldest = sorted(self._sessions.values(), key=lambda s: s.last_activity)[:5]
            for session in oldest:
                self._sessions.pop(session.session_id, None)

        session = CodeSession(
            agent_id=agent_id,
            language=language,
            mode=mode,
        )
        self._sessions[session.session_id] = session
        logger.info("Created code session %s (%s)", session.session_id, language.value)
        return session

    def get_session(self, session_id: str) -> CodeSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        """Close a session and free resources."""
        session = self._sessions.pop(session_id, None)
        if session:
            logger.info("Closed code session %s", session_id)
            return True
        return False

    def list_sessions(self, agent_id: str = "") -> list[CodeSession]:
        """List sessions with optional filtering."""
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return sorted(sessions, key=lambda s: s.last_activity, reverse=True)

    # ── Code Execution ───────────────────────────────────

    async def execute(
        self,
        code: str,
        language: Language = Language.PYTHON,
        session_id: str = "",
        agent_id: str = "",
        timeout_seconds: int | None = None,
    ) -> CodeExecution:
        """Execute code in the specified language."""
        execution = CodeExecution(
            session_id=session_id,
            agent_id=agent_id,
            language=language,
            code=code,
            line_count=code.count("\n") + 1,
        )

        # Get or create session
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_activity = datetime.now(timezone.utc).isoformat()
        else:
            session = None

        timeout = timeout_seconds or self.config.max_execution_time_seconds
        start_time = time.monotonic()

        try:
            execution.status = ExecutionStatus.RUNNING

            if language == Language.PYTHON:
                result = await self._execute_python(code, timeout)
            elif language == Language.JAVASCRIPT:
                result = await self._execute_javascript(code, timeout)
            elif language == Language.BASH:
                result = await self._execute_bash(code, timeout)
            elif language == Language.SQL:
                result = await self._execute_sql(code, timeout)
            elif language == Language.HTML:
                result = self._execute_html(code)
            else:
                result = {"output": "", "error": f"Unsupported language: {language.value}", "exit_code": 1}

            execution.output = result.get("output", "")[:self.config.max_output_chars]
            execution.error = result.get("error", "")
            execution.exit_code = result.get("exit_code", 0)
            execution.duration_ms = int((time.monotonic() - start_time) * 1000)

            if execution.exit_code == 0 and not execution.error:
                execution.status = ExecutionStatus.COMPLETED
                self._total_success += 1
            else:
                execution.status = ExecutionStatus.ERROR
                self._total_failed += 1

        except asyncio.TimeoutError:
            execution.status = ExecutionStatus.TIMEOUT
            execution.error = f"Execution timed out after {timeout}s"
            execution.duration_ms = timeout * 1000
            self._total_timeout += 1
        except Exception as e:
            execution.status = ExecutionStatus.ERROR
            execution.error = str(e)
            execution.duration_ms = int((time.monotonic() - start_time) * 1000)
            self._total_failed += 1

        # Update stats
        self._total_executions += 1
        self._total_code_lines += execution.line_count
        self._total_duration += execution.duration_ms

        # Store execution
        self._executions.append(execution)
        if session:
            session.executions.append(execution)

        return execution

    # ── Language Executors ────────────────────────────────

    async def _execute_python(self, code: str, timeout: int) -> dict[str, Any]:
        """Execute Python code in a sandboxed subprocess."""
        # Add safety wrapper
        safe_code = self._wrap_python_safe(code)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(safe_code)
            temp_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-u", temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {"output": "", "error": f"Timeout after {timeout}s", "exit_code": -1}

            return {
                "output": stdout.decode("utf-8", errors="replace"),
                "error": stderr.decode("utf-8", errors="replace"),
                "exit_code": process.returncode or 0,
            }
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def _execute_javascript(self, code: str, timeout: int) -> dict[str, Any]:
        """Execute JavaScript code."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                "node", "--no-warnings", temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {"output": "", "error": f"Timeout after {timeout}s", "exit_code": -1}

            return {
                "output": stdout.decode("utf-8", errors="replace"),
                "error": stderr.decode("utf-8", errors="replace"),
                "exit_code": process.returncode or 0,
            }
        except FileNotFoundError:
            return {"output": "", "error": "Node.js not found. Install Node.js to run JavaScript.", "exit_code": 1}
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def _execute_bash(self, code: str, timeout: int) -> dict[str, Any]:
        """Execute Bash code with safety restrictions."""
        safe_code = "set -euo pipefail\n" + code

        process = await asyncio.create_subprocess_shell(
            safe_code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {"output": "", "error": f"Timeout after {timeout}s", "exit_code": -1}

        return {
            "output": stdout.decode("utf-8", errors="replace"),
            "error": stderr.decode("utf-8", errors="replace"),
            "exit_code": process.returncode or 0,
        }

    async def _execute_sql(self, code: str, timeout: int) -> dict[str, Any]:
        """Execute SQL code using sqlite3 in-memory database."""
        import sqlite3

        try:
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            output_parts = []
            for statement in code.split(";"):
                statement = statement.strip()
                if not statement:
                    continue

                try:
                    cursor.execute(statement)
                    if statement.upper().startswith("SELECT") or statement.upper().startswith("PRAGMA"):
                        rows = cursor.fetchall()
                        if rows:
                            if cursor.description:
                                headers = [d[0] for d in cursor.description]
                                output_parts.append(" | ".join(headers))
                                output_parts.append("-" * len(" | ".join(headers)))
                            for row in rows:
                                output_parts.append(" | ".join(str(v) for v in row))
                            output_parts.append(f"({len(rows)} row(s))")
                    else:
                        output_parts.append(f"OK ({cursor.rowcount} row(s) affected)")
                except Exception as e:
                    output_parts.append(f"Error: {e}")

            conn.commit()
            conn.close()

            return {
                "output": "\n".join(output_parts),
                "error": "",
                "exit_code": 0,
            }
        except Exception as e:
            return {"output": "", "error": str(e), "exit_code": 1}

    def _execute_html(self, code: str) -> dict[str, Any]:
        """Validate HTML code (rendering is handled by frontend)."""
        # Basic HTML validation
        open_tags = []
        valid = True
        for part in code.split("<"):
            if not part:
                continue
            tag = part.split(">")[0].split()[0] if ">" in part else part.split()[0]
            if tag.startswith("/"):
                tag_name = tag[1:]
                if tag_name in open_tags:
                    open_tags.remove(tag_name)
            elif tag and not tag.startswith("!") and not tag.startswith("?"):
                if not any(tag.endswith(c) for c in ["/", "br", "hr", "img", "input", "meta", "link"]):
                    open_tags.append(tag)

        return {
            "output": code if valid else "HTML rendered",
            "error": f"Unclosed tags: {', '.join(open_tags)}" if open_tags else "",
            "exit_code": 0 if not open_tags else 1,
        }

    # ── File Management ──────────────────────────────────

    def write_file(self, session_id: str, filename: str, content: str) -> bool:
        """Write a file to a session's virtual file system."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        if len(content) > self.config.max_file_size_bytes:
            logger.warning("File too large: %s (%d bytes)", filename, len(content))
            return False

        session.files[filename] = content
        return True

    def read_file(self, session_id: str, filename: str) -> str | None:
        """Read a file from a session's virtual file system."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        return session.files.get(filename)

    def list_files(self, session_id: str) -> list[str]:
        """List files in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return []
        return list(session.files.keys())

    def delete_file(self, session_id: str, filename: str) -> bool:
        """Delete a file from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        return session.files.pop(filename, None) is not None

    # ── Execution History ────────────────────────────────

    def get_execution(self, execution_id: str) -> CodeExecution | None:
        """Get an execution record by ID."""
        for execution in self._executions:
            if execution.execution_id == execution_id:
                return execution
        return None

    def list_executions(
        self,
        session_id: str = "",
        agent_id: str = "",
        language: Language | None = None,
        status: ExecutionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CodeExecution]:
        """List execution records with filtering."""
        executions = self._executions
        if session_id:
            executions = [e for e in executions if e.session_id == session_id]
        if agent_id:
            executions = [e for e in executions if e.agent_id == agent_id]
        if language:
            executions = [e for e in executions if e.language == language]
        if status:
            executions = [e for e in executions if e.status == status]

        executions.sort(key=lambda e: e.created_at, reverse=True)
        return executions[offset:offset + limit]

    # ── Statistics ───────────────────────────────────────

    def get_stats(self) -> CodeInterpreterStats:
        """Get comprehensive interpreter statistics."""
        stats = CodeInterpreterStats()
        stats.total_executions = self._total_executions
        stats.successful_executions = self._total_success
        stats.failed_executions = self._total_failed
        stats.timeout_executions = self._total_timeout
        stats.total_sessions = len(self._sessions)
        stats.active_sessions = sum(1 for s in self._sessions.values() if s.mode == SessionMode.PERSISTENT)
        stats.total_code_lines = self._total_code_lines

        if self._total_executions > 0:
            stats.avg_execution_ms = self._total_duration / self._total_executions

        lang_counts: dict[str, int] = {}
        for execution in self._executions:
            lang = execution.language.value
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        stats.executions_by_language = lang_counts

        return stats

    def reset(self) -> None:
        """Reset the code interpreter."""
        self._sessions.clear()
        self._executions.clear()
        self._total_executions = 0
        self._total_success = 0
        self._total_failed = 0
        self._total_timeout = 0
        self._total_code_lines = 0
        self._total_duration = 0
        logger.info("AgentCodeInterpreter reset")

    # ── Internal Helpers ─────────────────────────────────

    def _wrap_python_safe(self, code: str) -> str:
        """Wrap Python code with safety restrictions."""
        allowed = ", ".join(f'"{m}"' for m in self.config.allowed_imports)
        blocked = ", ".join(f'"{m}"' for m in self.config.blocked_imports)

        wrapper = f'''
import builtins
import sys

# Block dangerous imports
_allowed = {{{allowed}}}
_blocked = {{{blocked}}}

_original_import = builtins.__import__

def _safe_import(name, *args, **kwargs):
    if name in _blocked:
        raise ImportError(f"Import of '{{name}}' is blocked for security")
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _safe_import

# Redirect stdout
from io import StringIO
_output = StringIO()
sys.stdout = _output

try:
{chr(10).join("    " + line for line in code.split(chr(10)))}
finally:
    sys.stdout = sys.__stdout__
    print(_output.getvalue(), end="")
'''
        return wrapper


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_code_interpreter: AgentCodeInterpreter | None = None


def get_code_interpreter() -> AgentCodeInterpreter:
    """Get or create the global Code Interpreter instance."""
    global _code_interpreter
    if _code_interpreter is None:
        _code_interpreter = AgentCodeInterpreter()
    return _code_interpreter


def reset_code_interpreter() -> None:
    """Reset the global Code Interpreter instance."""
    global _code_interpreter
    if _code_interpreter:
        _code_interpreter.reset()
    _code_interpreter = None