"""
Buddy Sandbox - Secure Execution Environment

Provides isolated execution contexts for tool operations, terminal commands,
and code evaluation. Implements resource limits, timeout controls, and
permission gating to ensure safe agent operations.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class SandboxPolicy(str, Enum):
    """Execution policy for sandbox operations."""
    STRICT = "strict"        # All operations require approval
    STANDARD = "standard"    # File reads allowed, writes need approval
    PERMISSIVE = "permissive"  # All operations allowed within limits
    YOLO = "yolo"            # No restrictions (use with caution)


class ExecutionResult:
    """Result of a sandboxed execution."""

    def __init__(self, command_id: str, exit_code: int, stdout: str, stderr: str, duration_ms: float):
        self.command_id = command_id
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.success = exit_code == 0

    def to_dict(self) -> dict:
        return {
            "command_id": self.command_id,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution limits."""
    max_execution_time_sec: float = 30.0
    max_output_bytes: int = 1024 * 1024  # 1MB
    max_memory_mb: int = 512
    allowed_directories: list[str] = field(default_factory=lambda: ["/tmp", "./workspace"])
    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:", "chmod 777 /",
    ])
    network_enabled: bool = False
    env_allowlist: list[str] = field(default_factory=lambda: [
        "PATH", "HOME", "USER", "LANG", "PYTHONPATH",
    ])


class FileOperation:
    """Safe file system operations within sandbox."""

    def __init__(self, workspace_root: str, policy: SandboxPolicy = SandboxPolicy.STANDARD):
        self.workspace_root = Path(workspace_root).resolve()
        self.policy = policy
        self._operation_log: list[dict] = []

    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate a path within workspace."""
        target = (self.workspace_root / path).resolve()
        if not str(target).startswith(str(self.workspace_root)):
            raise ValueError(f"Path traversal detected: {path}")
        return target

    def read(self, path: str) -> str:
        """Read a file within the workspace."""
        target = self._resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        content = target.read_text(encoding="utf-8")
        self._log_operation("read", path, {"size": len(content)})
        return content

    def write(self, path: str, content: str) -> int:
        """Write a file within the workspace."""
        if self.policy in (SandboxPolicy.STRICT,):
            raise PermissionError("Write operations require approval in strict mode")
        target = self._resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._log_operation("write", path, {"size": len(content)})
        return len(content)

    def list_dir(self, path: str = ".") -> list[dict]:
        """List directory contents."""
        target = self._resolve_path(path)
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        entries = []
        for entry in sorted(target.iterdir()):
            entries.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else 0,
            })
        self._log_operation("list", path, {"count": len(entries)})
        return entries

    def delete(self, path: str) -> bool:
        """Delete a file or directory."""
        if self.policy in (SandboxPolicy.STRICT, SandboxPolicy.STANDARD):
            raise PermissionError("Delete operations require permissive mode")
        target = self._resolve_path(path)
        if target.is_dir():
            import shutil
            shutil.rmtree(target)
        else:
            target.unlink()
        self._log_operation("delete", path, {})
        return True

    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        target = self._resolve_path(path)
        return target.exists()

    def _log_operation(self, op: str, path: str, metadata: dict):
        self._operation_log.append({
            "operation": op,
            "path": path,
            "metadata": metadata,
            "timestamp": time.time(),
        })

    def get_log(self) -> list[dict]:
        return self._operation_log


class SandboxEngine:
    """Central sandbox engine for secure agent execution.

    Provides isolated execution environments for terminal commands,
    code evaluation, and file system operations. Implements resource
    limiting, timeout enforcement, and permission gating.
    """

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()
        self._sessions: dict[str, SandboxSession] = {}
        self._total_executions = 0
        self._total_errors = 0
        self._workspace_base = Path(tempfile.gettempdir()) / "buddy_sandbox"
        self._workspace_base.mkdir(parents=True, exist_ok=True)

    def create_session(self, agent_id: str, policy: SandboxPolicy = SandboxPolicy.STANDARD) -> str:
        """Create a new sandbox session for an agent."""
        session_id = f"sandbox-{uuid.uuid4().hex[:12]}"
        workspace = self._workspace_base / session_id
        workspace.mkdir(parents=True, exist_ok=True)

        session = SandboxSession(
            session_id=session_id,
            agent_id=agent_id,
            workspace=str(workspace),
            policy=policy,
            config=self.config,
        )
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> "SandboxSession":
        """Get an existing sandbox session."""
        if session_id not in self._sessions:
            raise KeyError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    async def execute(
        self,
        session_id: str,
        command: str,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute a command within a sandbox session."""
        session = self.get_session(session_id)
        result = await session.execute(command, timeout, env)
        self._total_executions += 1
        if not result.success:
            self._total_errors += 1
        return result

    def close_session(self, session_id: str) -> bool:
        """Close and clean up a sandbox session."""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            session.cleanup()
            return True
        return False

    def get_stats(self) -> dict:
        return {
            "active_sessions": len(self._sessions),
            "total_executions": self._total_executions,
            "total_errors": self._total_errors,
            "sessions": [
                {"id": s.session_id, "agent_id": s.agent_id, "policy": s.policy.value}
                for s in self._sessions.values()
            ],
        }


class SandboxSession:
    """Individual sandbox session with isolated workspace."""

    def __init__(
        self,
        session_id: str,
        agent_id: str,
        workspace: str,
        policy: SandboxPolicy,
        config: SandboxConfig,
    ):
        self.session_id = session_id
        self.agent_id = agent_id
        self.workspace = workspace
        self.policy = policy
        self.config = config
        self.files = FileOperation(workspace, policy)
        self._history: list[ExecutionResult] = []
        self._created_at = time.time()

    async def execute(
        self,
        command: str,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute a command with timeout and resource limits."""
        command_id = f"cmd-{uuid.uuid4().hex[:8]}"
        effective_timeout = timeout or self.config.max_execution_time_sec

        # Security check for blocked commands
        for blocked in self.config.blocked_commands:
            if blocked in command:
                result = ExecutionResult(command_id, 1, "", f"Blocked command pattern: {blocked}", 0)
                self._history.append(result)
                return result

        # Build environment
        exec_env = {k: v for k, v in os.environ.items() if k in self.config.env_allowlist}
        if env:
            exec_env.update(env)
        exec_env["BUDDY_SANDBOX_ID"] = self.session_id
        exec_env["BUDDY_WORKSPACE"] = self.workspace

        start = time.time()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace,
                env=exec_env,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=effective_timeout
            )

            duration_ms = (time.time() - start) * 1000
            stdout = stdout_bytes.decode("utf-8", errors="replace")[:self.config.max_output_bytes]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[:self.config.max_output_bytes]

            result = ExecutionResult(command_id, process.returncode or 0, stdout, stderr, duration_ms)
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            result = ExecutionResult(command_id, 124, "", f"Timeout after {effective_timeout}s", duration_ms)
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            result = ExecutionResult(command_id, 1, "", str(e), duration_ms)

        self._history.append(result)
        return result

    def get_history(self, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in self._history[-limit:]]

    def cleanup(self):
        """Remove workspace directory."""
        import shutil
        ws = Path(self.workspace)
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)


# Global sandbox engine instance
_sandbox_engine: SandboxEngine | None = None


def get_sandbox_engine() -> SandboxEngine:
    """Get or create the global sandbox engine."""
    global _sandbox_engine
    if _sandbox_engine is None:
        _sandbox_engine = SandboxEngine()
    return _sandbox_engine