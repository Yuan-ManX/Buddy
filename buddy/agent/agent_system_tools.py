"""
Buddy System Tools Module.

Provides system-level capabilities for agents including command execution,
file system operations, clipboard management, and environment access.
Designed with safety sandboxing and permission controls.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CommandRisk(Enum):
    """Risk level for system commands."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileOperation(Enum):
    """Types of file system operations."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    COPY = "copy"
    MOVE = "move"
    LIST = "list"
    EXISTS = "exists"
    MKDIR = "mkdir"
    STAT = "stat"
    SEARCH = "search"


@dataclass
class CommandResult:
    """Result of a system command execution."""
    command: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: float = 0.0
    risk_level: CommandRisk = CommandRisk.MEDIUM
    sandboxed: bool = True
    truncated: bool = False


@dataclass
class FileOperationResult:
    """Result of a file system operation."""
    operation: FileOperation
    success: bool
    path: str = ""
    content: Any = None
    error: Optional[str] = None
    size_bytes: int = 0
    is_directory: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClipboardContent:
    """Content from the system clipboard."""
    text: str = ""
    html: str = ""
    image_base64: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class SystemToolManager:
    """
    System tool manager providing sandboxed access to system capabilities.

    Manages command execution, file system operations, clipboard access,
    and environment variable management with safety controls.
    """

    # Commands that are always allowed
    SAFE_COMMANDS = {
        "ls", "pwd", "echo", "cat", "head", "tail", "wc",
        "grep", "find", "which", "date", "env", "printenv",
        "uname", "whoami", "id", "hostname", "df", "du",
        "ps", "top", "uptime", "free", "ifconfig", "netstat",
        "ping", "curl", "wget", "git", "python", "python3",
        "node", "npm", "pip", "pip3", "make", "cmake",
    }

    # Commands that are always blocked
    BLOCKED_COMMANDS = {
        "rm", "rmdir", "mv", "dd", "mkfs", "fdisk", "mount",
        "umount", "chmod", "chown", "sudo", "su", "passwd",
        "shutdown", "reboot", "halt", "poweroff", "init",
        "kill", "killall", "pkill", "systemctl", "service",
    }

    # Patterns that indicate dangerous operations
    DANGEROUS_PATTERNS = [
        "rm -rf /", "rm -rf /*", "rm -rf ~", "dd if=",
        "mkfs.", "> /dev/sda", "fork bomb", ":(){ :|:& };:",
        "chmod 777 /", "chown -R", "> /etc/",
    ]

    def __init__(self, workspace_root: str = ""):
        self._workspace_root = workspace_root or os.getcwd()
        self._command_history: list[CommandResult] = []
        self._clipboard: Optional[ClipboardContent] = None
        self._command_timeout: float = 60.0
        self._max_output_size: int = 100_000

    # ── Command Execution ──────────────────────────────────────────

    def assess_command_risk(self, command: str) -> CommandRisk:
        """Assess the risk level of a system command."""
        cmd_base = command.strip().split()[0] if command.strip() else ""

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command:
                return CommandRisk.CRITICAL

        # Check if base command is blocked
        if cmd_base in self.BLOCKED_COMMANDS:
            return CommandRisk.HIGH

        # Check if command uses pipe or redirect
        if "|" in command or ">" in command or ">>" in command:
            return CommandRisk.MEDIUM

        # Check if safe command
        if cmd_base in self.SAFE_COMMANDS:
            return CommandRisk.SAFE

        return CommandRisk.LOW

    async def execute_command(
        self,
        command: str,
        cwd: str = "",
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        sandbox: bool = True,
    ) -> CommandResult:
        """Execute a system command with safety controls."""
        risk = self.assess_command_risk(command)

        if risk == CommandRisk.CRITICAL:
            return CommandResult(
                command=command,
                success=False,
                stderr="Command blocked: critical risk detected",
                risk_level=risk,
            )

        if risk == CommandRisk.HIGH and sandbox:
            return CommandResult(
                command=command,
                success=False,
                stderr="Command blocked: high risk operation requires sandbox bypass",
                risk_level=risk,
            )

        work_dir = cwd or self._workspace_root
        timeout = timeout or self._command_timeout

        start = time.time()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env={**os.environ, **(env or {})},
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            truncated = False
            if len(stdout_str) > self._max_output_size:
                stdout_str = stdout_str[:self._max_output_size] + "\n... [output truncated]"
                truncated = True

            result = CommandResult(
                command=command,
                success=process.returncode == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=process.returncode,
                duration_ms=(time.time() - start) * 1000,
                risk_level=risk,
                sandboxed=sandbox,
                truncated=truncated,
            )
        except asyncio.TimeoutError:
            result = CommandResult(
                command=command,
                success=False,
                stderr=f"Command timed out after {timeout}s",
                risk_level=risk,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = CommandResult(
                command=command,
                success=False,
                stderr=str(e),
                risk_level=risk,
                duration_ms=(time.time() - start) * 1000,
            )

        self._command_history.append(result)
        return result

    async def execute_commands_parallel(
        self,
        commands: list[str],
        cwd: str = "",
        sandbox: bool = True,
    ) -> list[CommandResult]:
        """Execute multiple commands in parallel."""
        tasks = [
            self.execute_command(cmd, cwd=cwd, sandbox=sandbox)
            for cmd in commands
        ]
        return await asyncio.gather(*tasks)

    # ── File System Operations ─────────────────────────────────────

    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to the workspace root."""
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(Path(self._workspace_root) / p)

    def read_file(self, path: str, max_size: int = 1_000_000) -> FileOperationResult:
        """Read a file from the workspace."""
        resolved = self._resolve_path(path)
        try:
            file_path = Path(resolved)
            if not file_path.exists():
                return FileOperationResult(
                    operation=FileOperation.READ,
                    success=False,
                    path=resolved,
                    error="File not found",
                )
            if file_path.stat().st_size > max_size:
                return FileOperationResult(
                    operation=FileOperation.READ,
                    success=False,
                    path=resolved,
                    error=f"File too large (>{max_size} bytes)",
                )
            content = file_path.read_text(encoding="utf-8")
            return FileOperationResult(
                operation=FileOperation.READ,
                success=True,
                path=resolved,
                content=content,
                size_bytes=file_path.stat().st_size,
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.READ,
                success=False,
                path=resolved,
                error=str(e),
            )

    def write_file(
        self,
        path: str,
        content: str,
        create_dirs: bool = True,
    ) -> FileOperationResult:
        """Write content to a file."""
        resolved = self._resolve_path(path)
        try:
            file_path = Path(resolved)
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return FileOperationResult(
                operation=FileOperation.WRITE,
                success=True,
                path=resolved,
                size_bytes=file_path.stat().st_size,
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.WRITE,
                success=False,
                path=resolved,
                error=str(e),
            )

    def delete_file(self, path: str) -> FileOperationResult:
        """Delete a file."""
        resolved = self._resolve_path(path)
        try:
            file_path = Path(resolved)
            if not file_path.exists():
                return FileOperationResult(
                    operation=FileOperation.DELETE,
                    success=False,
                    path=resolved,
                    error="File not found",
                )
            file_path.unlink()
            return FileOperationResult(
                operation=FileOperation.DELETE,
                success=True,
                path=resolved,
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.DELETE,
                success=False,
                path=resolved,
                error=str(e),
            )

    def copy_file(self, source: str, destination: str) -> FileOperationResult:
        """Copy a file."""
        src = self._resolve_path(source)
        dst = self._resolve_path(destination)
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return FileOperationResult(
                operation=FileOperation.COPY,
                success=True,
                path=dst,
                size_bytes=Path(dst).stat().st_size,
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.COPY,
                success=False,
                path=src,
                error=str(e),
            )

    def move_file(self, source: str, destination: str) -> FileOperationResult:
        """Move a file."""
        src = self._resolve_path(source)
        dst = self._resolve_path(destination)
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            return FileOperationResult(
                operation=FileOperation.MOVE,
                success=True,
                path=dst,
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.MOVE,
                success=False,
                path=src,
                error=str(e),
            )

    def list_directory(self, path: str = ".") -> FileOperationResult:
        """List contents of a directory."""
        resolved = self._resolve_path(path)
        try:
            dir_path = Path(resolved)
            if not dir_path.exists():
                return FileOperationResult(
                    operation=FileOperation.LIST,
                    success=False,
                    path=resolved,
                    error="Directory not found",
                )
            items = []
            for item in sorted(dir_path.iterdir()):
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "is_directory": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": stat.st_mtime,
                })
            return FileOperationResult(
                operation=FileOperation.LIST,
                success=True,
                path=resolved,
                content=items,
                is_directory=True,
                metadata={"item_count": len(items)},
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.LIST,
                success=False,
                path=resolved,
                error=str(e),
            )

    def make_directory(self, path: str) -> FileOperationResult:
        """Create a directory."""
        resolved = self._resolve_path(path)
        try:
            Path(resolved).mkdir(parents=True, exist_ok=True)
            return FileOperationResult(
                operation=FileOperation.MKDIR,
                success=True,
                path=resolved,
                is_directory=True,
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.MKDIR,
                success=False,
                path=resolved,
                error=str(e),
            )

    def file_exists(self, path: str) -> FileOperationResult:
        """Check if a file or directory exists."""
        resolved = self._resolve_path(path)
        file_path = Path(resolved)
        exists = file_path.exists()
        return FileOperationResult(
            operation=FileOperation.EXISTS,
            success=True,
            path=resolved,
            content=exists,
            is_directory=file_path.is_dir() if exists else False,
        )

    def search_files(
        self,
        pattern: str,
        directory: str = ".",
        recursive: bool = True,
        max_results: int = 100,
    ) -> FileOperationResult:
        """Search for files matching a pattern."""
        resolved = self._resolve_path(directory)
        try:
            dir_path = Path(resolved)
            if recursive:
                matches = list(dir_path.rglob(pattern))[:max_results]
            else:
                matches = list(dir_path.glob(pattern))[:max_results]

            results = [
                {
                    "path": str(m.relative_to(dir_path)),
                    "absolute_path": str(m),
                    "is_directory": m.is_dir(),
                    "size": m.stat().st_size if m.is_file() else 0,
                }
                for m in matches
            ]
            return FileOperationResult(
                operation=FileOperation.SEARCH,
                success=True,
                path=resolved,
                content=results,
                metadata={"pattern": pattern, "count": len(results)},
            )
        except Exception as e:
            return FileOperationResult(
                operation=FileOperation.SEARCH,
                success=False,
                path=resolved,
                error=str(e),
            )

    # ── Clipboard Management ───────────────────────────────────────

    def get_clipboard(self) -> Optional[ClipboardContent]:
        """Get current clipboard content."""
        return self._clipboard

    def set_clipboard(self, content: ClipboardContent) -> None:
        """Set clipboard content."""
        self._clipboard = content
        logger.info("Clipboard updated: %d chars", len(content.text))

    def clear_clipboard(self) -> None:
        """Clear clipboard content."""
        self._clipboard = None

    # ── Environment Info ───────────────────────────────────────────

    def get_system_info(self) -> dict[str, Any]:
        """Get system information."""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "workspace_root": self._workspace_root,
            "cwd": os.getcwd(),
            "home": str(Path.home()),
        }

    def get_env_variable(self, name: str) -> Optional[str]:
        """Get an environment variable value."""
        return os.environ.get(name)

    def set_env_variable(self, name: str, value: str) -> None:
        """Set an environment variable for the current process."""
        os.environ[name] = value

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get system tools statistics."""
        return {
            "total_commands_executed": len(self._command_history),
            "commands_by_risk": {
                risk.value: sum(1 for c in self._command_history if c.risk_level == risk)
                for risk in CommandRisk
            },
            "successful_commands": sum(1 for c in self._command_history if c.success),
            "failed_commands": sum(1 for c in self._command_history if not c.success),
            "workspace_root": self._workspace_root,
            "command_timeout": self._command_timeout,
            "clipboard_available": self._clipboard is not None,
        }

    def get_command_history(self, limit: int = 50) -> list[CommandResult]:
        """Get recent command execution history."""
        return self._command_history[-limit:]

    def clear_command_history(self) -> None:
        """Clear command execution history."""
        self._command_history.clear()


# Global system tool manager instance
system_tools = SystemToolManager()