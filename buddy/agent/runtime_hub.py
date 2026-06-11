"""Buddy Runtime Hub — Universal execution environment management system.

Provides a unified abstraction over multiple execution backends:
- Local shell (subprocess-based)
- Docker containers (isolated, reproducible)
- Virtual environments (Python venv with dependency management)

Runtimes are auto-discovered, health-monitored, and support full lifecycle
management: create, start, stop, hibernate, destroy. Resource metrics (CPU,
memory, disk) are tracked per runtime with configurable limits.

Architecture:
    RuntimeHub (singleton)
    ├── RuntimeRegistry (runtime bookkeeping)
    ├── RuntimeMonitor (health + resource polling)
    ├── ExecutorFactory (backend-specific executors)
    └── RuntimePool (pre-warmed runtime reuse pool)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import platform
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("buddy.runtime_hub")


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════════════

class RuntimeBackend(str, Enum):
    """Supported execution backend types."""
    LOCAL = "local"
    DOCKER = "docker"
    VENV = "venv"
    SSH = "ssh"
    MODAL = "modal"


class RuntimeStatus(str, Enum):
    """Lifecycle states for a runtime."""
    CREATING = "creating"
    READY = "ready"
    RUNNING = "running"
    IDLE = "idle"
    HIBERNATING = "hibernating"
    DESTROYED = "destroyed"
    ERROR = "error"
    STOPPING = "stopping"


class ResourceArch(str, Enum):
    """Hardware architecture for resource limits."""
    AMD64 = "amd64"
    ARM64 = "arm64"


@dataclass
class ResourceLimits:
    """Resource constraints for a runtime."""
    max_cpu_cores: float = 2.0
    max_memory_mb: int = 2048
    max_disk_mb: int = 10240
    max_execution_timeout_sec: int = 3600
    max_concurrent_executions: int = 3


@dataclass
class ResourceUsage:
    """Current resource consumption snapshot."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_mb: float = 0.0
    active_executions: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RuntimeInfo:
    """Metadata for a registered runtime."""
    id: str = field(default_factory=lambda: f"rt-{uuid.uuid4().hex[:12]}")
    name: str = "default"
    backend: RuntimeBackend = RuntimeBackend.LOCAL
    status: RuntimeStatus = RuntimeStatus.CREATING
    arch: str = field(default_factory=lambda: platform.machine())
    workspace_dir: str = ""
    image: str = ""  # Docker image name (Docker backend only)
    startup_script: str = ""  # Script to run on startup
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    usage: ResourceUsage = field(default_factory=ResourceUsage)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "backend": self.backend.value,
            "status": self.status.value,
            "arch": self.arch,
            "workspace_dir": self.workspace_dir,
            "image": self.image,
            "limits": {
                "max_cpu_cores": self.limits.max_cpu_cores,
                "max_memory_mb": self.limits.max_memory_mb,
                "max_disk_mb": self.limits.max_disk_mb,
            },
            "usage": {
                "cpu_percent": self.usage.cpu_percent,
                "memory_mb": self.usage.memory_mb,
                "active_executions": self.usage.active_executions,
            },
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_heartbeat": self.last_heartbeat,
            "error_message": self.error_message,
        }


@dataclass
class ExecutionRequest:
    """Request to execute code or a command in a runtime."""
    runtime_id: str
    command: str = ""
    code: str = ""
    language: str = "python"
    environment: dict[str, str] = field(default_factory=dict)
    timeout_sec: int = 300
    working_dir: str = ""
    stream_output: bool = False
    id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:12]}")


@dataclass
class ExecutionResult:
    """Result from executing code or a command in a runtime."""
    execution_id: str
    runtime_id: str
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    success: bool = False
    error_message: str = ""
    artifacts: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# Backend Executors
# ═══════════════════════════════════════════════════════════════════════════

class BaseExecutor:
    """Abstract base for backend-specific execution."""

    async def execute(self, request: ExecutionRequest, runtime: RuntimeInfo) -> ExecutionResult:
        raise NotImplementedError

    async def probe(self, runtime: RuntimeInfo) -> bool:
        """Check if the runtime backend is available."""
        raise NotImplementedError


class LocalExecutor(BaseExecutor):
    """Execute commands directly via subprocess on the host machine."""

    async def execute(self, request: ExecutionRequest, runtime: RuntimeInfo) -> ExecutionResult:
        started = time.time()
        result = ExecutionResult(
            execution_id=request.id,
            runtime_id=request.runtime_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            cmd = request.command if request.command else request.code
            env = {**os.environ, **request.environment}
            cwd = request.working_dir or runtime.workspace_dir or os.getcwd()

            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=request.timeout_sec,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                result.error_message = f"Execution timed out after {request.timeout_sec}s"
                result.finished_at = datetime.now(timezone.utc).isoformat()
                result.duration_ms = (time.time() - started) * 1000
                return result

            result.exit_code = proc.returncode or 0
            result.stdout = stdout.decode("utf-8", errors="replace") if stdout else ""
            result.stderr = stderr.decode("utf-8", errors="replace") if stderr else ""
            result.success = result.exit_code == 0

        except FileNotFoundError:
            result.error_message = f"Command not found: {cmd[:100]}"
        except Exception as e:
            result.error_message = str(e)

        result.finished_at = datetime.now(timezone.utc).isoformat()
        result.duration_ms = (time.time() - started) * 1000
        return result

    async def probe(self, runtime: RuntimeInfo) -> bool:
        try:
            proc = await asyncio.create_subprocess_shell(
                "echo ok",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return b"ok" in (stdout or b"")
        except Exception:
            return False


class DockerExecutor(BaseExecutor):
    """Execute commands inside Docker containers."""

    async def execute(self, request: ExecutionRequest, runtime: RuntimeInfo) -> ExecutionResult:
        started = time.time()
        result = ExecutionResult(
            execution_id=request.id,
            runtime_id=request.runtime_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            cmd = request.command if request.command else request.code
            cwd = request.working_dir or "/workspace"

            docker_args = [
                "docker", "exec",
                "-w", cwd,
            ]
            for k, v in request.environment.items():
                docker_args.extend(["-e", f"{k}={v}"])

            docker_args.append(runtime.id)
            docker_args.extend(["sh", "-c", cmd])

            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=request.timeout_sec,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                result.error_message = f"Execution timed out after {request.timeout_sec}s"
                result.finished_at = datetime.now(timezone.utc).isoformat()
                result.duration_ms = (time.time() - started) * 1000
                return result

            result.exit_code = proc.returncode or 0
            result.stdout = stdout.decode("utf-8", errors="replace") if stdout else ""
            result.stderr = stderr.decode("utf-8", errors="replace") if stderr else ""
            result.success = result.exit_code == 0

        except FileNotFoundError:
            result.error_message = "Docker is not installed or not on PATH"
        except Exception as e:
            result.error_message = str(e)

        result.finished_at = datetime.now(timezone.utc).isoformat()
        result.duration_ms = (time.time() - started) * 1000
        return result

    async def probe(self, runtime: RuntimeInfo) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", runtime.id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False


class VenvExecutor(BaseExecutor):
    """Execute Python code inside virtual environments."""

    async def execute(self, request: ExecutionRequest, runtime: RuntimeInfo) -> ExecutionResult:
        started = time.time()
        result = ExecutionResult(
            execution_id=request.id,
            runtime_id=request.runtime_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            venv_dir = runtime.workspace_dir or os.path.join(tempfile.gettempdir(), runtime.id, "venv")
            python_bin = os.path.join(venv_dir, "bin" if os.name != "nt" else "Scripts", "python")

            if request.code:
                # Write code to temp file and execute
                tmpfile = os.path.join(tempfile.gettempdir(), f"{request.id}.py")
                with open(tmpfile, "w") as f:
                    f.write(request.code)

                proc = await asyncio.create_subprocess_exec(
                    python_bin, tmpfile,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, **request.environment},
                    cwd=request.working_dir or venv_dir,
                )
            else:
                proc = await asyncio.create_subprocess_shell(
                    request.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**os.environ, **request.environment},
                    cwd=request.working_dir or venv_dir,
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=request.timeout_sec,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                result.error_message = f"Execution timed out after {request.timeout_sec}s"
                result.finished_at = datetime.now(timezone.utc).isoformat()
                result.duration_ms = (time.time() - started) * 1000
                return result

            result.exit_code = proc.returncode or 0
            result.stdout = stdout.decode("utf-8", errors="replace") if stdout else ""
            result.stderr = stderr.decode("utf-8", errors="replace") if stderr else ""
            result.success = result.exit_code == 0

            # Cleanup temp file
            if request.code and os.path.exists(tmpfile):
                os.unlink(tmpfile)

        except FileNotFoundError:
            result.error_message = "Python venv not found"
        except Exception as e:
            result.error_message = str(e)

        result.finished_at = datetime.now(timezone.utc).isoformat()
        result.duration_ms = (time.time() - started) * 1000
        return result

    async def probe(self, runtime: RuntimeInfo) -> bool:
        venv_dir = runtime.workspace_dir or ""
        python_bin = os.path.join(venv_dir, "bin" if os.name != "nt" else "Scripts", "python")
        return os.path.isfile(python_bin) and os.access(python_bin, os.X_OK)


# ═══════════════════════════════════════════════════════════════════════════
# Runtime Registry
# ═══════════════════════════════════════════════════════════════════════════

class RuntimeRegistry:
    """Manages runtime registration and lifecycle."""

    def __init__(self):
        self._runtimes: dict[str, RuntimeInfo] = {}
        self._executors: dict[str, BaseExecutor] = {}
        self._execution_history: dict[str, list[ExecutionResult]] = {}

    def register(self, info: RuntimeInfo) -> RuntimeInfo:
        self._runtimes[info.id] = info
        self._execution_history.setdefault(info.id, [])

        # Assign executor based on backend
        if info.backend == RuntimeBackend.DOCKER:
            self._executors[info.id] = DockerExecutor()
        elif info.backend == RuntimeBackend.VENV:
            self._executors[info.id] = VenvExecutor()
        else:
            self._executors[info.id] = LocalExecutor()

        logger.info(f"Runtime registered: {info.id} ({info.name}, backend={info.backend.value})")
        return info

    def unregister(self, runtime_id: str) -> bool:
        if runtime_id in self._runtimes:
            del self._runtimes[runtime_id]
            self._executors.pop(runtime_id, None)
            logger.info(f"Runtime unregistered: {runtime_id}")
            return True
        return False

    def get(self, runtime_id: str) -> RuntimeInfo | None:
        return self._runtimes.get(runtime_id)

    def get_executor(self, runtime_id: str) -> BaseExecutor | None:
        return self._executors.get(runtime_id)

    def list_all(self) -> list[RuntimeInfo]:
        return list(self._runtimes.values())

    def list_by_backend(self, backend: RuntimeBackend) -> list[RuntimeInfo]:
        return [r for r in self._runtimes.values() if r.backend == backend]

    def list_by_tag(self, tag: str) -> list[RuntimeInfo]:
        return [r for r in self._runtimes.values() if tag in r.tags]

    def list_by_status(self, status: RuntimeStatus) -> list[RuntimeInfo]:
        return [r for r in self._runtimes.values() if r.status == status]

    def update_status(self, runtime_id: str, status: RuntimeStatus, error: str = "") -> bool:
        rt = self._runtimes.get(runtime_id)
        if rt:
            rt.status = status
            if error:
                rt.error_message = error
            if status == RuntimeStatus.ERROR and not error:
                rt.error_message = "Unknown error"
            return True
        return False

    def heartbeat(self, runtime_id: str) -> bool:
        rt = self._runtimes.get(runtime_id)
        if rt:
            rt.last_heartbeat = datetime.now(timezone.utc).isoformat()
            return True
        return False

    def record_execution(self, runtime_id: str, result: ExecutionResult) -> None:
        history = self._execution_history.setdefault(runtime_id, [])
        history.append(result)
        # Keep last 100 executions
        if len(history) > 100:
            self._execution_history[runtime_id] = history[-100:]

    def get_execution_history(self, runtime_id: str) -> list[ExecutionResult]:
        return self._execution_history.get(runtime_id, [])

    def get_stats(self) -> dict[str, Any]:
        runtimes = self._runtimes
        total = len(runtimes)
        status_counts: dict[str, int] = {}
        backend_counts: dict[str, int] = {}

        for rt in runtimes.values():
            status_counts[rt.status.value] = status_counts.get(rt.status.value, 0) + 1
            backend_counts[rt.backend.value] = backend_counts.get(rt.backend.value, 0) + 1

        total_executions = sum(len(h) for h in self._execution_history.values())

        return {
            "total_runtimes": total,
            "by_status": status_counts,
            "by_backend": backend_counts,
            "total_executions": total_executions,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Runtime Monitor
# ═══════════════════════════════════════════════════════════════════════════

class RuntimeMonitor:
    """Periodic health checking and resource polling for runtimes."""

    def __init__(self, registry: RuntimeRegistry):
        self._registry = registry
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._interval_sec = 30
        self._callbacks: list[Callable[[RuntimeInfo], Any]] = []

    def on_unhealthy(self, callback: Callable[[RuntimeInfo], Any]) -> None:
        self._callbacks.append(callback)

    async def start(self, interval_sec: int = 30) -> None:
        self._interval_sec = interval_sec
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Runtime monitor started (interval={interval_sec}s)")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Runtime monitor stopped")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._check_all()
            except Exception as e:
                logger.error(f"Runtime monitor error: {e}")
            await asyncio.sleep(self._interval_sec)

    async def _check_all(self) -> None:
        for rt in self._registry.list_all():
            try:
                executor = self._registry.get_executor(rt.id)
                if executor:
                    healthy = await executor.probe(rt)
                    if healthy:
                        self._registry.heartbeat(rt.id)
                        if rt.status in (RuntimeStatus.ERROR, RuntimeStatus.CREATING):
                            self._registry.update_status(rt.id, RuntimeStatus.READY)
                    else:
                        self._registry.update_status(rt.id, RuntimeStatus.ERROR, "Health check failed")
                        for cb in self._callbacks:
                            try:
                                cb(rt)
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"Monitor check failed for {rt.id}: {e}")

    async def check_now(self, runtime_id: str) -> bool:
        rt = self._registry.get(runtime_id)
        if not rt:
            return False
        executor = self._registry.get_executor(runtime_id)
        if not executor:
            return False
        healthy = await executor.probe(rt)
        if healthy:
            self._registry.heartbeat(runtime_id)
        return healthy


# ═══════════════════════════════════════════════════════════════════════════
# Runtime Hub (Facade)
# ═══════════════════════════════════════════════════════════════════════════

class RuntimeHub:
    """Central facade for runtime management, execution, and monitoring.

    Usage:
        hub = RuntimeHub()
        rt = hub.create_runtime(name="my-env", backend=RuntimeBackend.LOCAL)
        result = await hub.execute(ExecutionRequest(
            runtime_id=rt.id,
            command="echo hello",
        ))
        stats = hub.get_stats()
    """

    def __init__(self):
        self.registry = RuntimeRegistry()
        self.monitor = RuntimeMonitor(self.registry)

    # ── Runtime Lifecycle ──

    def create_runtime(
        self,
        name: str,
        backend: RuntimeBackend = RuntimeBackend.LOCAL,
        workspace_dir: str = "",
        image: str = "",
        tags: list[str] | None = None,
        limits: ResourceLimits | None = None,
        metadata: dict[str, str] | None = None,
    ) -> RuntimeInfo:
        """Create and register a new runtime."""
        rt = RuntimeInfo(
            name=name,
            backend=backend,
            workspace_dir=workspace_dir,
            image=image,
            tags=tags or [],
            limits=limits or ResourceLimits(),
            metadata=metadata or {},
        )
        self.registry.register(rt)
        self.registry.update_status(rt.id, RuntimeStatus.READY)
        logger.info(f"Runtime created: {rt.id} ({name})")
        return rt

    def destroy_runtime(self, runtime_id: str) -> bool:
        """Remove a runtime from the registry."""
        self.registry.update_status(runtime_id, RuntimeStatus.DESTROYED)
        return self.registry.unregister(runtime_id)

    def get_runtime(self, runtime_id: str) -> RuntimeInfo | None:
        return self.registry.get(runtime_id)

    def list_runtimes(self, backend: RuntimeBackend | None = None) -> list[dict[str, Any]]:
        runtimes = self.registry.list_by_backend(backend) if backend else self.registry.list_all()
        return [rt.to_dict() for rt in runtimes]

    # ── Execution ──

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a command or code in a runtime."""
        rt = self.registry.get(request.runtime_id)
        if not rt:
            return ExecutionResult(
                execution_id=request.id,
                runtime_id=request.runtime_id,
                error_message=f"Runtime not found: {request.runtime_id}",
            )

        executor = self.registry.get_executor(request.runtime_id)
        if not executor:
            return ExecutionResult(
                execution_id=request.id,
                runtime_id=request.runtime_id,
                error_message=f"No executor for backend: {rt.backend.value}",
            )

        if rt.status == RuntimeStatus.HIBERNATING:
            self.registry.update_status(request.runtime_id, RuntimeStatus.READY)

        self.registry.update_status(request.runtime_id, RuntimeStatus.RUNNING)

        result = await executor.execute(request, rt)
        self.registry.record_execution(request.runtime_id, result)
        self.registry.heartbeat(request.runtime_id)

        self.registry.update_status(
            request.runtime_id,
            RuntimeStatus.IDLE if rt.status != RuntimeStatus.ERROR else RuntimeStatus.ERROR,
        )

        return result

    async def execute_python(self, runtime_id: str, code: str, **kwargs: Any) -> ExecutionResult:
        """Convenience method to execute Python code."""
        request = ExecutionRequest(
            runtime_id=runtime_id,
            code=code,
            language="python",
            **kwargs,
        )
        return await self.execute(request)

    async def execute_command(self, runtime_id: str, command: str, **kwargs: Any) -> ExecutionResult:
        """Convenience method to execute a shell command."""
        request = ExecutionRequest(
            runtime_id=runtime_id,
            command=command,
            **kwargs,
        )
        return await self.execute(request)

    # ── Health ──

    async def start_monitor(self, interval_sec: int = 30) -> None:
        await self.monitor.start(interval_sec)

    async def stop_monitor(self) -> None:
        await self.monitor.stop()

    async def check_health(self, runtime_id: str) -> bool:
        return await self.monitor.check_now(runtime_id)

    # ── Stats ──

    def get_stats(self) -> dict[str, Any]:
        return self.registry.get_stats()

    def get_execution_history(self, runtime_id: str) -> list[dict[str, Any]]:
        history = self.registry.get_execution_history(runtime_id)
        return [
            {
                "execution_id": r.execution_id,
                "exit_code": r.exit_code,
                "success": r.success,
                "duration_ms": r.duration_ms,
                "stdout": r.stdout[:500],
                "stderr": r.stderr[:500],
                "error_message": r.error_message,
                "started_at": r.started_at,
            }
            for r in history
        ]

    # ── Auto-Discovery ──

    async def auto_discover(self) -> list[RuntimeInfo]:
        """Auto-discover available runtimes on the host."""
        discovered: list[RuntimeInfo] = []

        # Always available: local runtime
        local = self.create_runtime(
            name="local-host",
            backend=RuntimeBackend.LOCAL,
            tags=["auto-discovered", platform.system().lower()],
        )
        discovered.append(local)

        # Check for Docker
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode == 0:
                docker = self.create_runtime(
                    name="docker-engine",
                    backend=RuntimeBackend.DOCKER,
                    tags=["auto-discovered", "docker"],
                )
                discovered.append(docker)
                logger.info("Docker runtime auto-discovered")
        except Exception:
            pass

        # Check for Python venv
        if shutil.which("python3") or shutil.which("python"):
            venv = self.create_runtime(
                name="python-venv",
                backend=RuntimeBackend.VENV,
                workspace_dir=os.path.join(tempfile.gettempdir(), "buddy-venv"),
                tags=["auto-discovered", "python"],
            )
            discovered.append(venv)

        logger.info(f"Auto-discovered {len(discovered)} runtimes")
        return discovered


# ═══════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════

runtime_hub = RuntimeHub()