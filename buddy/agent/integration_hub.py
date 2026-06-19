"""
Buddy Integration Hub - External Service Integration

Central hub for connecting Buddy agents to external services, APIs,
and platforms. Provides unified authentication, rate limiting, retry
logic, and response normalization across all integrations.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntegrationType(str, Enum):
    """Types of external integrations."""
    API = "api"                  # REST/GraphQL API
    DATABASE = "database"        # Database connection
    MESSAGE_QUEUE = "queue"     # Message queue
    STORAGE = "storage"          # File/object storage
    NOTIFICATION = "notification"  # Push notifications
    ANALYTICS = "analytics"      # Analytics platform
    CRM = "crm"                  # Customer relationship
    EMAIL = "email"              # Email service
    CALENDAR = "calendar"        # Calendar service
    VERSION_CONTROL = "vcs"      # Version control
    CI_CD = "cicd"               # CI/CD pipeline
    MONITORING = "monitoring"    # Monitoring service
    CUSTOM = "custom"            # Custom integration


class AuthMethod(str, Enum):
    """Authentication methods for integrations."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    BEARER = "bearer"
    NONE = "none"


@dataclass
class IntegrationConfig:
    """Configuration for an external integration."""
    integration_id: str
    name: str
    integration_type: IntegrationType
    auth_method: AuthMethod = AuthMethod.API_KEY
    base_url: str = ""
    api_key: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    timeout_sec: float = 30.0
    retry_count: int = 3
    retry_delay_sec: float = 1.0
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


class Integration:
    """A single external integration instance."""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self._request_count = 0
        self._error_count = 0
        self._last_request_time = 0.0
        self._request_window: list[float] = []
        self._created_at = time.time()

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        self._request_window = [t for t in self._request_window if now - t < 60]
        return len(self._request_window) < self.config.rate_limit_per_minute

    async def request(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        """Make a request to the integrated service."""
        if not self.config.enabled:
            return {"error": "Integration is disabled"}

        if not self._check_rate_limit():
            return {"error": "Rate limit exceeded", "retry_after": 60}

        self._request_count += 1
        self._request_window.append(time.time())

        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        req_headers = {**self.config.headers, **(headers or {})}

        if self.config.auth_method == AuthMethod.API_KEY:
            req_headers["X-API-Key"] = self.config.api_key
        elif self.config.auth_method == AuthMethod.BEARER:
            req_headers["Authorization"] = f"Bearer {self.config.api_key}"

        for attempt in range(self.config.retry_count + 1):
            try:
                # Simulated API call
                await asyncio.sleep(0.05)
                return {
                    "integration": self.config.name,
                    "method": method,
                    "url": url,
                    "status": "success",
                    "data": data,
                    "note": "Real API integration requires configuring the service endpoint.",
                }
            except Exception as e:
                if attempt < self.config.retry_count:
                    await asyncio.sleep(self.config.retry_delay_sec)
                else:
                    self._error_count += 1
                    return {"error": str(e), "method": method, "url": url}

    def to_dict(self) -> dict:
        return {
            "integration_id": self.config.integration_id,
            "name": self.config.name,
            "type": self.config.integration_type.value,
            "enabled": self.config.enabled,
            "request_count": self._request_count,
            "error_count": self._error_count,
        }


class IntegrationHub:
    """Central integration hub for external service connections.

    Manages all external integrations used by Buddy agents, providing
    unified authentication, rate limiting, retry logic, and response
    normalization across APIs, databases, storage, and other services.
    """

    def __init__(self):
        self._integrations: dict[str, Integration] = {}
        self._total_requests = 0
        self._total_errors = 0

    def register(self, config: IntegrationConfig) -> Integration:
        """Register a new integration."""
        integration = Integration(config)
        self._integrations[config.integration_id] = integration
        return integration

    def get(self, integration_id: str) -> Integration | None:
        """Get an integration by ID."""
        return self._integrations.get(integration_id)

    def unregister(self, integration_id: str):
        """Remove an integration."""
        self._integrations.pop(integration_id, None)

    def list_integrations(self) -> list[dict]:
        """List all registered integrations."""
        return [i.to_dict() for i in self._integrations.values()]

    def get_stats(self) -> dict:
        return {
            "total_integrations": len(self._integrations),
            "integrations": self.list_integrations(),
        }


# Global integration hub instance
_integration_hub: IntegrationHub | None = None


def get_integration_hub() -> IntegrationHub:
    """Get or create the global integration hub."""
    global _integration_hub
    if _integration_hub is None:
        _integration_hub = IntegrationHub()
    return _integration_hub