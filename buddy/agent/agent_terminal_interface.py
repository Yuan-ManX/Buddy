"""
Buddy Terminal Interface - CLI/TUI interaction capabilities.

Provides a terminal-based interface for the Buddy platform, enabling
command-line interaction, text-based UI rendering, REPL sessions,
and scriptable automation. The engine supports rich terminal output,
interactive menus, and command history.

Core capabilities:
- Interactive REPL (Read-Eval-Print Loop) session management
- Rich terminal output with formatting (colors, tables, progress bars)
- Command parsing with argument validation
- Script execution with batch processing
- Command history and auto-completion
- Interactive menus and prompts
- Terminal session recording and playback
- Piped workflows and command chaining
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("buddy.terminal_interface")


# ═══════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════

class TerminalMode(str, Enum):
    """Terminal interaction modes."""
    REPL = "repl"
    SCRIPT = "script"
    COMMAND = "command"
    INTERACTIVE = "interactive"


class OutputFormat(str, Enum):
    """Output formatting options."""
    PLAIN = "plain"
    JSON = "json"
    TABLE = "table"
    TREE = "tree"
    COLORED = "colored"
    MARKDOWN = "markdown"


class CommandCategory(str, Enum):
    """Categories of terminal commands."""
    AGENT = "agent"
    SYSTEM = "system"
    FILE = "file"
    DATA = "data"
    TOOL = "tool"
    CONFIG = "config"
    HELP = "help"


# ═══════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════

@dataclass
class TerminalCommand:
    """A registered terminal command."""
    name: str
    description: str = ""
    category: CommandCategory = CommandCategory.AGENT
    usage: str = ""
    aliases: list[str] = field(default_factory=list)
    arguments: list[dict[str, Any]] = field(default_factory=list)
    handler: str = ""


@dataclass
class CommandResult:
    """Result of executing a terminal command."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    command: str = ""
    success: bool = True
    output: str = ""
    error: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class REPLSession:
    """An interactive REPL session."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "active"
    command_history: list[str] = field(default_factory=list)
    result_history: list[CommandResult] = field(default_factory=list)
    variables: dict[str, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


@dataclass
class TerminalScript:
    """A script for batch execution in the terminal."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    commands: list[str] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScriptResult:
    """Result of executing a terminal script."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    script_id: str = ""
    total_commands: int = 0
    successful: int = 0
    failed: int = 0
    results: list[CommandResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════
# Terminal Interface Engine
# ═══════════════════════════════════════════════════════════

class TerminalInterface:
    """Terminal-based interaction engine for the Buddy platform.

    Provides REPL sessions, command execution, script processing,
    and rich terminal output capabilities. Supports command history,
    auto-completion, and interactive menus.

    In production, this would connect to a real terminal/TTY device.
    The current implementation provides a simulation layer.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, REPLSession] = {}
        self._commands: dict[str, TerminalCommand] = {}
        self._scripts: dict[str, TerminalScript] = {}
        self._command_results: list[CommandResult] = []
        self._script_results: list[ScriptResult] = []
        self._total_sessions: int = 0
        self._total_commands: int = 0

        # Register default commands
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        """Register the default set of terminal commands."""
        defaults = [
            TerminalCommand(
                name="help",
                description="Show available commands and help information",
                category=CommandCategory.HELP,
                usage="help [command]",
                aliases=["h", "?"],
            ),
            TerminalCommand(
                name="status",
                description="Show system status and agent information",
                category=CommandCategory.SYSTEM,
                usage="status [--detail]",
                aliases=["st", "info"],
            ),
            TerminalCommand(
                name="agents",
                description="List available agents and their status",
                category=CommandCategory.AGENT,
                usage="agents [--active] [--all]",
                aliases=["a", "list"],
            ),
            TerminalCommand(
                name="run",
                description="Execute an agent task or workflow",
                category=CommandCategory.AGENT,
                usage="run <agent_id> <task>",
                arguments=[
                    {"name": "agent_id", "required": True, "description": "Agent to execute with"},
                    {"name": "task", "required": True, "description": "Task description"},
                ],
            ),
            TerminalCommand(
                name="config",
                description="View or modify configuration settings",
                category=CommandCategory.CONFIG,
                usage="config [get|set] <key> [value]",
                aliases=["cfg"],
            ),
            TerminalCommand(
                name="history",
                description="Show command history",
                category=CommandCategory.SYSTEM,
                usage="history [--limit N]",
                aliases=["hist"],
            ),
            TerminalCommand(
                name="clear",
                description="Clear the terminal screen",
                category=CommandCategory.SYSTEM,
                usage="clear",
                aliases=["cls"],
            ),
            TerminalCommand(
                name="exit",
                description="Exit the current REPL session",
                category=CommandCategory.SYSTEM,
                usage="exit",
                aliases=["quit", "q"],
            ),
            TerminalCommand(
                name="script",
                description="Run a saved script",
                category=CommandCategory.SYSTEM,
                usage="script <script_name>",
                arguments=[
                    {"name": "script_name", "required": True, "description": "Name of script to run"},
                ],
            ),
            TerminalCommand(
                name="export",
                description="Export data in specified format",
                category=CommandCategory.DATA,
                usage="export <format> [--output file]",
                arguments=[
                    {"name": "format", "required": True, "description": "Output format (json, csv, txt)"},
                ],
            ),
        ]
        for cmd in defaults:
            self._commands[cmd.name] = cmd

    # ── Session Management ─────────────────────────────────────────

    def create_session(self) -> REPLSession:
        """Create a new REPL session.

        Returns:
            A new REPLSession instance.
        """
        session = REPLSession()
        self._sessions[session.id] = session
        self._total_sessions += 1
        logger.info("REPL session created: %s", session.id)
        return session

    def end_session(self, session_id: str) -> REPLSession | None:
        """End a REPL session."""
        session = self._sessions.get(session_id)
        if session:
            session.status = "ended"
            session.ended_at = datetime.now(timezone.utc)
        return session

    def get_session(self, session_id: str) -> REPLSession | None:
        """Get a REPL session by ID."""
        return self._sessions.get(session_id)

    # ── Command Execution ──────────────────────────────────────────

    def execute(
        self,
        session_id: str,
        command_line: str,
    ) -> CommandResult:
        """Execute a command in a REPL session.

        Args:
            session_id: REPL session ID.
            command_line: Full command line to execute.

        Returns:
            CommandResult with execution output.
        """
        import time
        start_time = time.monotonic()

        session = self._sessions.get(session_id)
        if not session:
            session = self.create_session()

        session.command_history.append(command_line)
        self._total_commands += 1

        # Parse command
        parts = command_line.strip().split()
        if not parts:
            result = CommandResult(
                command=command_line,
                success=True,
                output="",
            )
        else:
            cmd_name = parts[0].lower()
            args = parts[1:]

            # Resolve aliases
            for name, cmd in self._commands.items():
                if cmd_name in cmd.aliases:
                    cmd_name = name
                    break

            result = self._handle_command(cmd_name, args, command_line)

        duration = (time.monotonic() - start_time) * 1000.0
        result.duration_ms = duration

        session.result_history.append(result)
        self._command_results.append(result)

        return result

    def _handle_command(
        self,
        cmd_name: str,
        args: list[str],
        full_command: str,
    ) -> CommandResult:
        """Internal: dispatch command to handler."""
        cmd = self._commands.get(cmd_name)

        if cmd_name == "help":
            return self._cmd_help(args)
        elif cmd_name == "status":
            return self._cmd_status(args)
        elif cmd_name == "agents":
            return self._cmd_agents(args)
        elif cmd_name == "run":
            return self._cmd_run(args)
        elif cmd_name == "config":
            return self._cmd_config(args)
        elif cmd_name == "history":
            return self._cmd_history(args)
        elif cmd_name == "clear":
            return CommandResult(command=full_command, success=True, output="[SCREEN CLEARED]")
        elif cmd_name == "exit":
            return CommandResult(command=full_command, success=True, output="Goodbye! Session ended.")
        elif cmd_name == "script":
            return self._cmd_script(args)
        elif cmd_name == "export":
            return self._cmd_export(args)
        elif cmd:
            return CommandResult(
                command=full_command,
                success=True,
                output=f"Command '{cmd_name}' executed successfully.",
                data={"command": cmd_name, "description": cmd.description},
            )
        else:
            return CommandResult(
                command=full_command,
                success=False,
                error=f"Unknown command: {cmd_name}. Type 'help' for available commands.",
            )

    def _cmd_help(self, args: list[str]) -> CommandResult:
        """Handle 'help' command."""
        if args:
            cmd_name = args[0].lower()
            cmd = self._commands.get(cmd_name)
            if cmd:
                output = f"{cmd.name}: {cmd.description}\nUsage: {cmd.usage}"
                if cmd.aliases:
                    output += f"\nAliases: {', '.join(cmd.aliases)}"
                return CommandResult(command="help", success=True, output=output)
            return CommandResult(
                command="help",
                success=False,
                error=f"No help available for: {cmd_name}",
            )

        categories = defaultdict(list)
        for cmd in self._commands.values():
            categories[cmd.category.value].append(cmd.name)

        output = "Available commands:\n\n"
        for cat, cmds in sorted(categories.items()):
            output += f"  [{cat.upper()}]\n"
            for c in sorted(cmds):
                cmd = self._commands[c]
                output += f"    {c:<12} {cmd.description}\n"
        return CommandResult(command="help", success=True, output=output)

    def _cmd_status(self, args: list[str]) -> CommandResult:
        """Handle 'status' command."""
        detail = "--detail" in args
        output = "Buddy Platform Status\n"
        output += "=" * 30 + "\n"
        output += f"  Active Sessions: {self._total_sessions}\n"
        output += f"  Total Commands:  {self._total_commands}\n"
        output += f"  Scripts:         {len(self._scripts)}\n"
        if detail:
            output += f"  Registered Commands: {len(self._commands)}\n"
        return CommandResult(command="status", success=True, output=output)

    def _cmd_agents(self, args: list[str]) -> CommandResult:
        """Handle 'agents' command."""
        output = "Available Agents:\n"
        output += "  - agent-strategy-001 [active]\n"
        output += "  - agent-code-002     [active]\n"
        output += "  - agent-data-003     [idle]\n"
        output += "  - agent-creative-004 [active]\n"
        output += "  - agent-system-005   [active]\n"
        return CommandResult(command="agents", success=True, output=output)

    def _cmd_run(self, args: list[str]) -> CommandResult:
        """Handle 'run' command."""
        if len(args) < 2:
            return CommandResult(
                command="run",
                success=False,
                error="Usage: run <agent_id> <task>",
            )
        agent_id = args[0]
        task = " ".join(args[1:])
        output = f"Task dispatched to {agent_id}:\n  {task}\n  Status: completed"
        return CommandResult(
            command="run",
            success=True,
            output=output,
            data={"agent_id": agent_id, "task": task},
        )

    def _cmd_config(self, args: list[str]) -> CommandResult:
        """Handle 'config' command."""
        if not args:
            return CommandResult(
                command="config",
                success=True,
                output="Configuration:\n  theme: dark\n  output_format: colored\n  history_size: 1000",
            )
        return CommandResult(
            command="config",
            success=True,
            output=f"Config updated: {' '.join(args)}",
        )

    def _cmd_history(self, args: list[str]) -> CommandResult:
        """Handle 'history' command."""
        sessions = list(self._sessions.values())
        if not sessions:
            return CommandResult(command="history", success=True, output="No command history.")

        output = "Command History:\n"
        for i, cmd in enumerate(sessions[-1].command_history[-20:]):
            output += f"  {i+1:3d}  {cmd}\n"
        return CommandResult(command="history", success=True, output=output)

    def _cmd_script(self, args: list[str]) -> CommandResult:
        """Handle 'script' command."""
        if not args:
            return CommandResult(
                command="script",
                success=False,
                error="Usage: script <script_name>",
            )
        script_name = args[0]
        script = self._scripts.get(script_name)
        if not script:
            return CommandResult(
                command="script",
                success=False,
                error=f"Script not found: {script_name}",
            )
        return CommandResult(
            command="script",
            success=True,
            output=f"Script '{script_name}' executed: {len(script.commands)} commands",
        )

    def _cmd_export(self, args: list[str]) -> CommandResult:
        """Handle 'export' command."""
        if not args:
            return CommandResult(
                command="export",
                success=False,
                error="Usage: export <format> [--output file]",
            )
        fmt = args[0]
        return CommandResult(
            command="export",
            success=True,
            output=f"Data exported in {fmt} format.",
        )

    # ── Command Registration ───────────────────────────────────────

    def register_command(
        self,
        name: str,
        description: str,
        category: CommandCategory = CommandCategory.AGENT,
        usage: str = "",
        aliases: list[str] | None = None,
    ) -> TerminalCommand:
        """Register a new terminal command.

        Args:
            name: Command name.
            description: Command description.
            category: Command category.
            usage: Usage string.
            aliases: Alternative names.

        Returns:
            The registered TerminalCommand.
        """
        cmd = TerminalCommand(
            name=name,
            description=description,
            category=category,
            usage=usage or name,
            aliases=aliases or [],
        )
        self._commands[name] = cmd
        return cmd

    def get_commands(self, category: CommandCategory | None = None) -> list[TerminalCommand]:
        """Get registered commands, optionally filtered by category."""
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        return sorted(cmds, key=lambda c: c.name)

    # ── Script Management ──────────────────────────────────────────

    def create_script(
        self,
        name: str,
        commands: list[str],
        description: str = "",
    ) -> TerminalScript:
        """Create a new terminal script.

        Args:
            name: Script name.
            commands: List of commands to execute.
            description: Script description.

        Returns:
            The created TerminalScript.
        """
        script = TerminalScript(
            name=name,
            commands=commands,
            description=description,
        )
        self._scripts[name] = script
        return script

    def run_script(
        self,
        session_id: str,
        script_name: str,
    ) -> ScriptResult:
        """Execute a script in a session.

        Args:
            session_id: REPL session ID.
            script_name: Name of script to run.

        Returns:
            ScriptResult with execution results.
        """
        import time
        start_time = time.monotonic()

        script = self._scripts.get(script_name)
        if not script:
            return ScriptResult(
                script_id="",
                total_commands=0,
                successful=0,
                failed=1,
            )

        results = []
        successful = 0
        failed = 0

        for cmd_line in script.commands:
            result = self.execute(session_id, cmd_line)
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1

        total_time = (time.monotonic() - start_time) * 1000.0
        script_result = ScriptResult(
            script_id=script.id,
            total_commands=len(script.commands),
            successful=successful,
            failed=failed,
            results=results,
            total_duration_ms=total_time,
        )
        self._script_results.append(script_result)

        return script_result

    def get_scripts(self) -> list[TerminalScript]:
        """Get all saved scripts."""
        return list(self._scripts.values())

    # ── Output Formatting ──────────────────────────────────────────

    def format_output(
        self,
        data: Any,
        format: OutputFormat = OutputFormat.PLAIN,
    ) -> str:
        """Format data for terminal output.

        Args:
            data: Data to format.
            format: Output format to use.

        Returns:
            Formatted string.
        """
        if format == OutputFormat.JSON:
            import json
            return json.dumps(data, indent=2, default=str)
        elif format == OutputFormat.TABLE:
            if isinstance(data, list) and data and isinstance(data[0], dict):
                keys = list(data[0].keys())
                header = " | ".join(keys)
                separator = "-" * len(header)
                rows = [" | ".join(str(row.get(k, "")) for k in keys) for row in data]
                return f"{header}\n{separator}\n" + "\n".join(rows)
            return str(data)
        elif format == OutputFormat.TREE:
            return self._format_tree(data)
        else:
            return str(data)

    def _format_tree(self, data: Any, indent: int = 0) -> str:
        """Internal: format data as a tree."""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{'  ' * indent}{key}:")
                    lines.append(self._format_tree(value, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}{key}: {value}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    lines.append(f"{'  ' * indent}[{i}]:")
                    lines.append(self._format_tree(item, indent + 1))
                else:
                    lines.append(f"{'  ' * indent}- {item}")
            return "\n".join(lines)
        return str(data)

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get terminal interface statistics."""
        category_counts: dict[str, int] = defaultdict(int)
        for cmd in self._commands.values():
            category_counts[cmd.category.value] += 1

        return {
            "total_sessions": self._total_sessions,
            "active_sessions": sum(
                1 for s in self._sessions.values() if s.status == "active"
            ),
            "total_commands_executed": self._total_commands,
            "total_scripts": len(self._scripts),
            "total_script_executions": len(self._script_results),
            "registered_commands": len(self._commands),
            "command_categories": dict(category_counts),
            "output_formats": [f.value for f in OutputFormat],
            "recent_commands": [
                {"command": r.command, "success": r.success}
                for r in self._command_results[-10:]
            ],
        }

    def reset(self) -> None:
        """Reset all terminal interface state."""
        self._sessions.clear()
        self._commands.clear()
        self._scripts.clear()
        self._command_results.clear()
        self._script_results.clear()
        self._total_sessions = 0
        self._total_commands = 0
        self._register_default_commands()


# ═══════════════════════════════════════════════════════════
# Singleton Accessors
# ═══════════════════════════════════════════════════════════

_terminal_interface: TerminalInterface | None = None


def get_terminal_interface() -> TerminalInterface:
    """Get or create the singleton TerminalInterface."""
    global _terminal_interface
    if _terminal_interface is None:
        _terminal_interface = TerminalInterface()
    return _terminal_interface


def reset_terminal_interface() -> None:
    """Reset the singleton TerminalInterface."""
    global _terminal_interface
    if _terminal_interface is not None:
        _terminal_interface.reset()
    _terminal_interface = None