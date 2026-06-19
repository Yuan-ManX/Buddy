"""
Buddy Terminal Agent - Shell Command Execution

Provides terminal command execution capabilities for agents, enabling
them to run shell commands, manage processes, and interact with the
operating system through a secure sandboxed interface.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TerminalMode(str, Enum):
    """Terminal execution modes."""
    COMMAND = "command"        # Single command execution
    SESSION = "session"        # Interactive session
    SCRIPT = "script"          # Script execution
    PIPELINE = "pipeline"      # Command pipeline


@dataclass
class TerminalConfig:
    """Configuration for terminal execution."""
    default_shell: str = "/bin/bash"
    max_command_length: int = 10000
    max_output_lines: int = 500
    timeout_sec: float = 30.0
    history_size: int = 100
    allowed_commands: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /", "mkfs", "shutdown", "reboot", "halt",
        "dd if=/dev/zero", "> /dev/sda", "chmod 777 /",
    ])


class TerminalSession:
    """A single terminal session with command history."""

    def __init__(self, session_id: str, agent_id: str, config: TerminalConfig):
        self.session_id = session_id
        self.agent_id = agent_id
        self.config = config
        self.history: list[TerminalResult] = []
        self._cwd = "/tmp"
        self._env: dict[str, str] = {}
        self._created_at = time.time()
        self._command_count = 0

    async def execute(self, command: str, timeout: float | None = None) -> "TerminalResult":
        """Execute a command in this terminal session."""
        self._command_count += 1
        result_id = f"term-{uuid.uuid4().hex[:8]}"

        # Security check
        if len(command) > self.config.max_command_length:
            return TerminalResult(
                result_id, command, 1, "",
                f"Command exceeds max length ({self.config.max_command_length})",
                time.time(),
            )

        for blocked in self.config.blocked_commands:
            if blocked in command:
                return TerminalResult(
                    result_id, command, 1, "",
                    f"Blocked command pattern detected: {blocked}",
                    time.time(),
                )

        effective_timeout = timeout or self.config.timeout_sec
        start = time.time()

        try:
            from agent.sandbox import get_sandbox_engine, SandboxPolicy
            sandbox = get_sandbox_engine()
            s_id = sandbox.create_session(self.agent_id, SandboxPolicy.STANDARD)

            result = await sandbox.execute(s_id, command, effective_timeout, self._env)
            sandbox.close_session(s_id)

            term_result = TerminalResult(
                result_id=result_id,
                command=command,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=result.duration_ms,
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            term_result = TerminalResult(
                result_id, command, 1, "", str(e), duration,
            )

        self.history.append(term_result)
        if len(self.history) > self.config.history_size:
            self.history = self.history[-self.config.history_size:]

        return term_result

    async def execute_script(self, script: str, language: str = "bash") -> "TerminalResult":
        """Execute a multi-line script."""
        import tempfile
        ext_map = {"bash": ".sh", "python": ".py", "node": ".js", "ruby": ".rb"}
        ext = ext_map.get(language, ".sh")

        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as f:
            f.write(script)
            tmp_path = f.name

        import os
        os.chmod(tmp_path, 0o755)

        if language == "python":
            cmd = f"python3 {tmp_path}"
        elif language == "node":
            cmd = f"node {tmp_path}"
        elif language == "ruby":
            cmd = f"ruby {tmp_path}"
        else:
            cmd = f"bash {tmp_path}"

        result = await self.execute(cmd)

        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        return result

    def set_env(self, key: str, value: str):
        """Set an environment variable for the session."""
        self._env[key] = value

    def set_cwd(self, path: str):
        """Set the working directory."""
        self._cwd = path

    def get_history(self, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in self.history[-limit:]]


class TerminalResult:
    """Result of a terminal command execution."""

    def __init__(
        self,
        result_id: str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: float,
    ):
        self.result_id = result_id
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.success = exit_code == 0

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }


class TerminalAgent:
    """Terminal command execution agent for Buddy.

    Provides agents with secure shell command execution capabilities
    through sandboxed sessions. Supports single commands, scripts,
    pipelines, and interactive sessions with environment control.
    """

    def __init__(self, config: TerminalConfig | None = None):
        self.config = config or TerminalConfig()
        self._sessions: dict[str, TerminalSession] = {}
        self._total_commands = 0
        self._total_sessions = 0

    def create_session(self, agent_id: str) -> TerminalSession:
        """Create a new terminal session."""
        session_id = f"term-{uuid.uuid4().hex[:12]}"
        session = TerminalSession(session_id, agent_id, self.config)
        self._sessions[session_id] = session
        self._total_sessions += 1
        return session

    def get_session(self, session_id: str) -> TerminalSession | None:
        """Get an existing session."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close a terminal session."""
        self._sessions.pop(session_id, None)

    async def execute(
        self,
        session_id: str,
        command: str,
        timeout: float | None = None,
    ) -> TerminalResult:
        """Execute a command in a session."""
        session = self.get_session(session_id)
        if not session:
            session = self.create_session("default")
            self._sessions[session_id] = session

        self._total_commands += 1
        return await session.execute(command, timeout)

    async def quick_execute(self, command: str, timeout: float | None = None) -> TerminalResult:
        """Execute a single command in a temporary session."""
        session = self.create_session("quick")
        result = await session.execute(command, timeout)
        self.close_session(session.session_id)
        return result

    def get_stats(self) -> dict:
        return {
            "active_sessions": len(self._sessions),
            "total_sessions": self._total_sessions,
            "total_commands": self._total_commands,
            "sessions": [
                {"id": s.session_id, "agent_id": s.agent_id, "command_count": s._command_count}
                for s in self._sessions.values()
            ],
        }


# Global terminal agent instance
_terminal_agent: TerminalAgent | None = None


def get_terminal_agent() -> TerminalAgent:
    """Get or create the global terminal agent."""
    global _terminal_agent
    if _terminal_agent is None:
        _terminal_agent = TerminalAgent()
    return _terminal_agent