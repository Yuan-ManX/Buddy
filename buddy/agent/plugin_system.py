"""
Buddy Plugin System

A dynamic plugin architecture that enables hot-loading of third-party
extensions, capabilities, and integrations. Plugins can be installed,
activated, deactivated, and uninstalled at runtime without restarting
the platform.

Each plugin defines its own lifecycle hooks, dependencies, permissions,
and capabilities, allowing the platform to be extended by the community.
"""

import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("buddy.plugin")


class PluginStatus(str, Enum):
    """Lifecycle states of a plugin."""
    REGISTERED = "registered"
    INSTALLING = "installing"
    INSTALLED = "installed"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    INACTIVE = "inactive"
    ERROR = "error"
    UNINSTALLING = "uninstalling"


class PluginPermission(str, Enum):
    """Permissions that a plugin can request."""
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    EXECUTE_TOOLS = "execute_tools"
    ACCESS_FILESYSTEM = "access_filesystem"
    NETWORK_ACCESS = "network_access"
    MANAGE_AGENTS = "manage_agents"
    SEND_MESSAGES = "send_messages"
    READ_CONVERSATIONS = "read_conversations"
    SYSTEM_CONFIG = "system_config"


@dataclass
class PluginManifest:
    """Metadata describing a plugin's identity, requirements, and capabilities."""
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    homepage: str = ""
    license: str = "MIT"
    min_platform_version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    permissions: list[PluginPermission] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    entry_point: str = ""
    config_schema: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class PluginInstance:
    """Runtime representation of an installed plugin."""
    manifest: PluginManifest
    status: PluginStatus = PluginStatus.REGISTERED
    installed_at: str = ""
    activated_at: str = ""
    error_message: str = ""
    config: dict = field(default_factory=dict)
    _module: Any = None
    _hooks: dict[str, Callable] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == PluginStatus.ACTIVE


class PluginSystem:
    """Central plugin management system for the Buddy platform.

    Handles the complete plugin lifecycle:
    - Discovery and registration
    - Installation with dependency resolution
    - Activation and deactivation with hook management
    - Configuration management
    - Permission enforcement
    - Uninstallation with cleanup
    """

    def __init__(self, plugins_dir: str = ""):
        self._plugins: dict[str, PluginInstance] = {}
        self._plugins_dir = plugins_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "plugins"
        )
        self._hooks: dict[str, list[tuple[str, Callable]]] = {
            "on_agent_start": [],
            "on_agent_stop": [],
            "on_message_received": [],
            "on_message_sent": [],
            "on_tool_executed": [],
            "on_memory_updated": [],
            "on_system_startup": [],
            "on_system_shutdown": [],
        }
        self._ensure_plugins_dir()
        logger.info(f"Plugin system initialized at {self._plugins_dir}")

    def _ensure_plugins_dir(self):
        """Ensure the plugins directory exists."""
        Path(self._plugins_dir).mkdir(parents=True, exist_ok=True)

    def register_manifest(self, manifest: PluginManifest) -> PluginInstance:
        """Register a plugin manifest for later installation."""
        if manifest.id in self._plugins:
            logger.warning(f"Plugin {manifest.id} already registered")
            return self._plugins[manifest.id]

        instance = PluginInstance(
            manifest=manifest,
            status=PluginStatus.REGISTERED,
        )
        self._plugins[manifest.id] = instance
        logger.info(f"Plugin registered: {manifest.name} v{manifest.version}")
        return instance

    async def install(self, plugin_id: str) -> bool:
        """Install a registered plugin."""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin {plugin_id} not registered")
            return False

        instance = self._plugins[plugin_id]
        instance.status = PluginStatus.INSTALLING

        try:
            # Resolve dependencies
            for dep_id in instance.manifest.dependencies:
                if dep_id not in self._plugins:
                    logger.error(f"Dependency {dep_id} not found for plugin {plugin_id}")
                    instance.status = PluginStatus.ERROR
                    instance.error_message = f"Missing dependency: {dep_id}"
                    return False
                if not self._plugins[dep_id].is_active:
                    await self.activate(dep_id)

            # Load the plugin module if entry point specified
            if instance.manifest.entry_point:
                await self._load_plugin_module(instance)

            instance.status = PluginStatus.INSTALLED
            instance.installed_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Plugin installed: {instance.manifest.name}")
            return True

        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"Plugin installation failed: {plugin_id} - {e}")
            return False

    async def _load_plugin_module(self, instance: PluginInstance):
        """Dynamically load a plugin's Python module."""
        try:
            module_path = os.path.join(self._plugins_dir, instance.manifest.id)
            if module_path not in sys.path:
                sys.path.insert(0, self._plugins_dir)

            module = importlib.import_module(
                f"{instance.manifest.id}.{instance.manifest.entry_point}"
            )
            instance._module = module

            # Discover lifecycle hooks
            for hook_name in self._hooks:
                if hasattr(module, hook_name):
                    hook_fn = getattr(module, hook_name)
                    if callable(hook_fn):
                        instance._hooks[hook_name] = hook_fn

        except ImportError as e:
            logger.warning(f"Could not load plugin module for {instance.manifest.id}: {e}")
            # Plugin without module is valid - it may be config-only

    async def activate(self, plugin_id: str) -> bool:
        """Activate an installed plugin."""
        if plugin_id not in self._plugins:
            logger.error(f"Plugin {plugin_id} not found")
            return False

        instance = self._plugins[plugin_id]
        if instance.status not in (PluginStatus.INSTALLED, PluginStatus.INACTIVE):
            logger.error(f"Plugin {plugin_id} cannot be activated from status {instance.status}")
            return False

        instance.status = PluginStatus.ACTIVATING

        try:
            # Verify permissions
            self._validate_permissions(instance)

            # Register hooks
            for hook_name, hook_fn in instance._hooks.items():
                self._hooks[hook_name].append((plugin_id, hook_fn))

            # Call on_activate if module has it
            if instance._module and hasattr(instance._module, "on_activate"):
                if inspect.iscoroutinefunction(instance._module.on_activate):
                    await instance._module.on_activate(instance.config)
                else:
                    instance._module.on_activate(instance.config)

            instance.status = PluginStatus.ACTIVE
            instance.activated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Plugin activated: {instance.manifest.name}")
            return True

        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"Plugin activation failed: {plugin_id} - {e}")
            return False

    async def deactivate(self, plugin_id: str) -> bool:
        """Deactivate an active plugin."""
        if plugin_id not in self._plugins:
            return False

        instance = self._plugins[plugin_id]
        if instance.status != PluginStatus.ACTIVE:
            return False

        instance.status = PluginStatus.DEACTIVATING

        try:
            # Call on_deactivate if module has it
            if instance._module and hasattr(instance._module, "on_deactivate"):
                if inspect.iscoroutinefunction(instance._module.on_deactivate):
                    await instance._module.on_deactivate()
                else:
                    instance._module.on_deactivate()

            # Unregister hooks
            for hook_name in self._hooks:
                self._hooks[hook_name] = [
                    (pid, fn)
                    for pid, fn in self._hooks[hook_name]
                    if pid != plugin_id
                ]

            instance.status = PluginStatus.INACTIVE
            logger.info(f"Plugin deactivated: {instance.manifest.name}")
            return True

        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"Plugin deactivation failed: {plugin_id} - {e}")
            return False

    async def uninstall(self, plugin_id: str):
        """Uninstall a plugin completely."""
        if plugin_id not in self._plugins:
            return

        instance = self._plugins[plugin_id]

        if instance.is_active:
            await self.deactivate(plugin_id)

        instance.status = PluginStatus.UNINSTALLING

        # Clean up module references
        if instance._module:
            module_name = instance._module.__name__
            if module_name in sys.modules:
                del sys.modules[module_name]

        del self._plugins[plugin_id]
        logger.info(f"Plugin uninstalled: {plugin_id}")

    async def fire_hook(self, hook_name: str, *args, **kwargs):
        """Fire a lifecycle hook to all registered plugins."""
        if hook_name not in self._hooks:
            return

        for plugin_id, hook_fn in self._hooks[hook_name]:
            try:
                if inspect.iscoroutinefunction(hook_fn):
                    await hook_fn(*args, **kwargs)
                else:
                    hook_fn(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook {hook_name} failed for plugin {plugin_id}: {e}")

    def _validate_permissions(self, instance: PluginInstance):
        """Validate that a plugin's requested permissions are acceptable."""
        dangerous_permissions = {
            PluginPermission.MANAGE_AGENTS,
            PluginPermission.SYSTEM_CONFIG,
        }
        requested = set(instance.manifest.permissions)
        if requested & dangerous_permissions:
            logger.warning(
                f"Plugin {instance.manifest.id} requests dangerous permissions: "
                f"{requested & dangerous_permissions}"
            )

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstance]:
        """Get a plugin instance by ID."""
        return self._plugins.get(plugin_id)

    def list_plugins(self, status_filter: Optional[PluginStatus] = None) -> list[dict]:
        """List all plugins, optionally filtered by status."""
        result = []
        for plugin_id, instance in self._plugins.items():
            if status_filter and instance.status != status_filter:
                continue
            result.append({
                "id": plugin_id,
                "name": instance.manifest.name,
                "version": instance.manifest.version,
                "description": instance.manifest.description,
                "author": instance.manifest.author,
                "status": instance.status.value,
                "capabilities": instance.manifest.capabilities,
                "permissions": [p.value for p in instance.manifest.permissions],
                "tags": instance.manifest.tags,
                "installed_at": instance.installed_at,
                "activated_at": instance.activated_at,
                "error": instance.error_message if instance.status == PluginStatus.ERROR else "",
            })
        return result

    def get_stats(self) -> dict:
        """Get plugin system statistics."""
        status_counts = {}
        for instance in self._plugins.values():
            status_counts[instance.status.value] = status_counts.get(instance.status.value, 0) + 1

        return {
            "total_plugins": len(self._plugins),
            "active_plugins": status_counts.get("active", 0),
            "status_counts": status_counts,
            "hooks_registered": {
                hook_name: len(hooks) for hook_name, hooks in self._hooks.items()
            },
            "plugins_dir": self._plugins_dir,
        }


# Global singleton
plugin_system = PluginSystem()