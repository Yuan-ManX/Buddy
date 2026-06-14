"""Buddy API Middleware — Rate limiting, caching, and security middleware

Provides FastAPI middleware for request rate limiting, response caching,
and security headers.
"""
from __future__ import annotations
import time
import logging
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("buddy.middleware")


class RateLimiter:
    """Simple in-memory sliding window rate limiter.

    Usage:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        app.add_middleware(RateLimitMiddleware, limiter=limiter)
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)
        self._blocked: dict[str, float] = {}

    def is_allowed(self, client_id: str) -> tuple[bool, int, int]:
        """Check if a client is allowed to make a request.

        Returns:
            Tuple of (allowed, remaining_requests, reset_seconds).
        """
        now = time.time()

        # Check if client is blocked
        if client_id in self._blocked:
            if now < self._blocked[client_id]:
                return False, 0, int(self._blocked[client_id] - now)
            del self._blocked[client_id]

        # Clean old entries
        cutoff = now - self.window_seconds
        self._clients[client_id] = [
            t for t in self._clients[client_id] if t > cutoff
        ]

        request_count = len(self._clients[client_id])
        if request_count >= self.max_requests:
            # Block for window duration
            self._blocked[client_id] = now + self.window_seconds
            return False, 0, self.window_seconds

        self._clients[client_id].append(now)
        remaining = self.max_requests - request_count - 1
        reset_seconds = self.window_seconds

        return True, remaining, reset_seconds

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        now = time.time()
        active_clients = sum(
            1 for times in self._clients.values()
            if any(t > now - self.window_seconds for t in times)
        )
        return {
            "active_clients": active_clients,
            "blocked_clients": len(self._blocked),
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
        }


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=200, window_seconds=60)


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, limiter: RateLimiter | None = None):
        self.app = app
        self.limiter = limiter or rate_limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        # Skip rate limiting for health, static, and docs endpoints
        skip_paths = ["/api/health", "/docs", "/openapi.json", "/redoc"]
        if any(path.startswith(p) for p in skip_paths):
            await self.app(scope, receive, send)
            return

        # Get client identifier (IP or forwarded header)
        client_id = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")

        allowed, remaining, reset = self.limiter.is_allowed(client_id)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": reset,
                },
            )
            response.headers["Retry-After"] = str(reset)
            response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(reset)
            await response(scope, receive, send)
            return

        # Add rate limit headers to the response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-ratelimit-limit"] = str(self.limiter.max_requests).encode()
                headers[b"x-ratelimit-remaining"] = str(remaining).encode()
                headers[b"x-ratelimit-reset"] = str(reset).encode()
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)


class SecurityHeadersMiddleware:
    """FastAPI middleware that adds security headers to all responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"x-xss-protection"] = b"1; mode=block"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"permissions-policy"] = b"camera=(), microphone=(), geolocation=()"
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send)


class ResponseCacheMiddleware:
    """Simple in-memory response cache for GET requests."""

    def __init__(self, app, ttl_seconds: int = 30, max_size: int = 1000):
        self.app = app
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: dict[str, tuple[float, bytes, str]] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        cache_key = path

        # Check cache
        if cache_key in self._cache:
            timestamp, body, content_type = self._cache[cache_key]
            if time.time() - timestamp < self.ttl_seconds:
                # Serve cached response
                async def send_cached(message):
                    if message["type"] == "http.response.start":
                        message["status"] = 200
                        headers = dict(message.get("headers", []))
                        headers[b"content-type"] = content_type.encode()
                        headers[b"x-cache"] = b"HIT"
                        message["headers"] = list(headers.items())
                        await send(message)
                    elif message["type"] == "http.response.body":
                        message["body"] = body
                        await send(message)
                await send_cached({"type": "http.response.start", "status": 200, "headers": []})
                await send_cached({"type": "http.response.body", "body": body})
                return

        # Collect response for caching
        collected_body = bytearray()
        collected_status = 200
        collected_headers: list[tuple[bytes, bytes]] = []
        content_type = "application/json"

        async def send_wrapper(message):
            nonlocal collected_status, collected_headers, content_type
            if message["type"] == "http.response.start":
                collected_status = message.get("status", 200)
                collected_headers = message.get("headers", [])
                for k, v in collected_headers:
                    if k == b"content-type":
                        content_type = v.decode()
                new_headers = list(collected_headers) + [(b"x-cache", b"MISS")]
                message["headers"] = new_headers
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                collected_body.extend(body)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # Cache successful GET responses
        if collected_status == 200 and collected_body and cache_key:
            if len(self._cache) >= self.max_size:
                # Evict oldest entry
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
                del self._cache[oldest_key]
            self._cache[cache_key] = (time.time(), bytes(collected_body), content_type)

    def get_stats(self) -> dict:
        return {
            "cached_entries": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
        }