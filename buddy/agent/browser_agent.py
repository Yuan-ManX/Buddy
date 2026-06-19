"""
Buddy Browser Agent - Web Automation Engine

Provides browser automation capabilities for agents, enabling web page
navigation, content extraction, form filling, and screenshot capture.
Uses a simulated browser interface for safe operation.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BrowserAction(str, Enum):
    """Types of browser actions."""
    NAVIGATE = "navigate"        # Navigate to URL
    CLICK = "click"              # Click element
    TYPE = "type"                # Type into element
    SCROLL = "scroll"            # Scroll page
    EXTRACT = "extract"          # Extract content
    SCREENSHOT = "screenshot"    # Take screenshot
    WAIT = "wait"                # Wait for element
    EXECUTE_JS = "execute_js"    # Execute JavaScript
    GO_BACK = "go_back"          # Navigate back
    GO_FORWARD = "go_forward"    # Navigate forward
    REFRESH = "refresh"          # Refresh page


@dataclass
class BrowserState:
    """Current state of the browser session."""
    url: str = ""
    title: str = ""
    content_preview: str = ""
    elements: list[dict] = field(default_factory=list)
    scroll_position: int = 0
    cookies: dict = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
    history_index: int = -1


class BrowserSession:
    """A single browser automation session for an agent."""

    def __init__(self, session_id: str, agent_id: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self.state = BrowserState()
        self._action_log: list[dict] = []
        self._created_at = time.time()
        self._closed = False

    async def navigate(self, url: str) -> dict:
        """Navigate to a URL."""
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        self.state.history.append(url)
        self.state.history_index = len(self.state.history) - 1
        self.state.url = url

        self._log_action(BrowserAction.NAVIGATE, {"url": url})

        # Simulated response - in production, this would use Playwright/Selenium
        return {
            "url": url,
            "status": "navigated",
            "title": self.state.title or f"Page: {url}",
            "note": "Browser navigation simulated. Configure BROWSER_ENGINE for real automation.",
        }

    async def click(self, selector: str) -> dict:
        """Click an element on the page."""
        self._log_action(BrowserAction.CLICK, {"selector": selector})
        return {"action": "click", "selector": selector, "status": "simulated"}

    async def type_text(self, selector: str, text: str) -> dict:
        """Type text into an element."""
        self._log_action(BrowserAction.TYPE, {"selector": selector, "text_length": len(text)})
        return {"action": "type", "selector": selector, "text_length": len(text), "status": "simulated"}

    async def scroll(self, direction: str = "down", amount: int = 300) -> dict:
        """Scroll the page."""
        if direction == "down":
            self.state.scroll_position += amount
        elif direction == "up":
            self.state.scroll_position = max(0, self.state.scroll_position - amount)

        self._log_action(BrowserAction.SCROLL, {"direction": direction, "amount": amount})
        return {"scroll_position": self.state.scroll_position, "status": "simulated"}

    async def extract_content(self, selector: str = "body") -> dict:
        """Extract content from the page."""
        self._log_action(BrowserAction.EXTRACT, {"selector": selector})
        return {
            "content": self.state.content_preview or "[Content extraction requires browser engine]",
            "selector": selector,
            "word_count": 0,
            "status": "simulated",
        }

    async def take_screenshot(self) -> dict:
        """Take a screenshot of the current page."""
        self._log_action(BrowserAction.SCREENSHOT, {})
        return {
            "screenshot": None,
            "note": "Screenshot capture requires browser engine configuration.",
            "status": "simulated",
        }

    async def execute_js(self, code: str) -> dict:
        """Execute JavaScript on the page."""
        self._log_action(BrowserAction.EXECUTE_JS, {"code_length": len(code)})
        return {"result": None, "status": "simulated"}

    async def go_back(self) -> dict:
        """Navigate back in history."""
        if self.state.history_index > 0:
            self.state.history_index -= 1
            self.state.url = self.state.history[self.state.history_index]
        self._log_action(BrowserAction.GO_BACK, {})
        return {"url": self.state.url, "status": "simulated"}

    async def go_forward(self) -> dict:
        """Navigate forward in history."""
        if self.state.history_index < len(self.state.history) - 1:
            self.state.history_index += 1
            self.state.url = self.state.history[self.state.history_index]
        self._log_action(BrowserAction.GO_FORWARD, {})
        return {"url": self.state.url, "status": "simulated"}

    async def refresh(self) -> dict:
        """Refresh the current page."""
        self._log_action(BrowserAction.REFRESH, {})
        return {"url": self.state.url, "status": "simulated"}

    def _log_action(self, action: BrowserAction, details: dict):
        self._action_log.append({
            "action": action.value,
            "details": details,
            "timestamp": time.time(),
        })

    def get_action_log(self) -> list[dict]:
        return self._action_log

    def close(self):
        """Close the browser session."""
        self._closed = True


class BrowserAgent:
    """Web automation agent for browser-based operations.

    Provides agents with the ability to navigate websites, extract
    information, fill forms, and interact with web applications.
    Supports both simulated and real browser engine modes.
    """

    def __init__(self):
        self._sessions: dict[str, BrowserSession] = {}
        self._total_actions = 0
        self._total_sessions = 0

    def create_session(self, agent_id: str) -> BrowserSession:
        """Create a new browser session."""
        session_id = f"browser-{uuid.uuid4().hex[:12]}"
        session = BrowserSession(session_id, agent_id)
        self._sessions[session_id] = session
        self._total_sessions += 1
        return session

    def get_session(self, session_id: str) -> BrowserSession | None:
        """Get an existing browser session."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str):
        """Close a browser session."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.close()

    async def execute_action(
        self,
        session_id: str,
        action: BrowserAction,
        **kwargs,
    ) -> dict:
        """Execute a browser action in a session."""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        action_map = {
            BrowserAction.NAVIGATE: session.navigate,
            BrowserAction.CLICK: session.click,
            BrowserAction.TYPE: session.type_text,
            BrowserAction.SCROLL: session.scroll,
            BrowserAction.EXTRACT: session.extract_content,
            BrowserAction.SCREENSHOT: session.take_screenshot,
            BrowserAction.EXECUTE_JS: session.execute_js,
            BrowserAction.GO_BACK: session.go_back,
            BrowserAction.GO_FORWARD: session.go_forward,
            BrowserAction.REFRESH: session.refresh,
        }

        handler = action_map.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}

        self._total_actions += 1
        return await handler(**kwargs)

    def get_stats(self) -> dict:
        return {
            "active_sessions": len(self._sessions),
            "total_sessions": self._total_sessions,
            "total_actions": self._total_actions,
            "sessions": [
                {"id": s.session_id, "agent_id": s.agent_id, "url": s.state.url}
                for s in self._sessions.values()
            ],
        }


# Global browser agent instance
_browser_agent: BrowserAgent | None = None


def get_browser_agent() -> BrowserAgent:
    """Get or create the global browser agent."""
    global _browser_agent
    if _browser_agent is None:
        _browser_agent = BrowserAgent()
    return _browser_agent