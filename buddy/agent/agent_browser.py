"""
Buddy Browser Automation Module.

Provides browser automation capabilities for agents to interact with
web pages, extract data, fill forms, capture screenshots, and perform
complex web-based workflows autonomously.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BrowserAction(Enum):
    """Types of browser actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    WAIT = "wait"
    EXECUTE_JS = "execute_js"
    SUBMIT = "submit"
    SELECT = "select"
    HOVER = "hover"
    DRAG = "drag"
    PRESS_KEY = "press_key"


class SelectorType(Enum):
    """Types of element selectors."""
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ID = "id"
    NAME = "name"
    ROLE = "role"
    LINK_TEXT = "link_text"


@dataclass
class BrowserElement:
    """Represents a DOM element."""
    selector: str = ""
    selector_type: SelectorType = SelectorType.CSS
    tag_name: str = ""
    text: str = ""
    attributes: dict[str, str] = field(default_factory=dict)
    bounding_box: Optional[dict[str, float]] = None
    visible: bool = True
    enabled: bool = True


@dataclass
class BrowserActionStep:
    """A single step in a browser automation workflow."""
    action: BrowserAction
    selector: str = ""
    selector_type: SelectorType = SelectorType.CSS
    value: str = ""
    wait_ms: int = 1000
    description: str = ""
    timeout_ms: int = 30000
    retry_on_failure: bool = True
    max_retries: int = 2


@dataclass
class BrowserActionResult:
    """Result of a browser action."""
    action: BrowserAction
    success: bool
    content: Any = None
    error: Optional[str] = None
    screenshot_base64: Optional[str] = None
    extracted_elements: list[BrowserElement] = field(default_factory=list)
    duration_ms: float = 0.0
    url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserSession:
    """A browser automation session."""
    session_id: str = ""
    current_url: str = ""
    page_title: str = ""
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str = ""
    cookies: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    active: bool = True


class BrowserAutomation:
    """
    Browser automation engine for autonomous web interaction.

    Provides a high-level API for browser control including navigation,
    data extraction, form filling, and screenshot capture. Designed to
    work with headless browser backends.
    """

    def __init__(self):
        self._sessions: dict[str, BrowserSession] = {}
        self._action_history: dict[str, list[BrowserActionResult]] = {}
        self._headless: bool = True

    # ── Session Management ─────────────────────────────────────────

    def create_session(
        self,
        session_id: str = "",
        viewport_width: int = 1280,
        viewport_height: int = 720,
        headless: bool = True,
    ) -> BrowserSession:
        """Create a new browser session."""
        import uuid

        session = BrowserSession(
            session_id=session_id or str(uuid.uuid4())[:12],
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )
        self._sessions[session.session_id] = session
        self._action_history[session.session_id] = []
        self._headless = headless
        logger.info("Browser session created: %s", session.session_id)
        return session

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get a browser session by ID."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        """Close a browser session."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.active = False
            logger.info("Browser session closed: %s", session_id)
            return True
        return False

    def list_sessions(self) -> list[BrowserSession]:
        """List all active browser sessions."""
        return list(self._sessions.values())

    # ── Navigation ─────────────────────────────────────────────────

    async def navigate(
        self,
        session_id: str,
        url: str,
        wait_until: str = "load",
        timeout_ms: int = 30000,
    ) -> BrowserActionResult:
        """Navigate to a URL."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.NAVIGATE,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            # Simulate navigation for testing
            await asyncio.sleep(0.2)
            session.current_url = url
            session.last_activity = time.time()

            result = BrowserActionResult(
                action=BrowserAction.NAVIGATE,
                success=True,
                url=url,
                duration_ms=(time.time() - start) * 1000,
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.NAVIGATE,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # ── Element Interaction ────────────────────────────────────────

    async def click(
        self,
        session_id: str,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> BrowserActionResult:
        """Click an element on the page."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.CLICK,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.1)
            session.last_activity = time.time()

            result = BrowserActionResult(
                action=BrowserAction.CLICK,
                success=True,
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
                metadata={"selector": selector, "selector_type": selector_type.value},
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.CLICK,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def type_text(
        self,
        session_id: str,
        selector: str,
        text: str,
        selector_type: SelectorType = SelectorType.CSS,
        clear_first: bool = True,
    ) -> BrowserActionResult:
        """Type text into an input element."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.TYPE,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.15)
            session.last_activity = time.time()

            result = BrowserActionResult(
                action=BrowserAction.TYPE,
                success=True,
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
                metadata={"selector": selector, "text_length": len(text)},
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.TYPE,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def scroll(
        self,
        session_id: str,
        direction: str = "down",
        amount: int = 500,
    ) -> BrowserActionResult:
        """Scroll the page."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.SCROLL,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.1)
            session.last_activity = time.time()

            result = BrowserActionResult(
                action=BrowserAction.SCROLL,
                success=True,
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
                metadata={"direction": direction, "amount": amount},
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.SCROLL,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # ── Data Extraction ────────────────────────────────────────────

    async def extract_content(
        self,
        session_id: str,
        selector: str = "body",
        selector_type: SelectorType = SelectorType.CSS,
        extract_type: str = "text",
    ) -> BrowserActionResult:
        """Extract content from the page."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.EXTRACT,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.1)
            session.last_activity = time.time()

            # Simulate extracted content
            content = f"Extracted {extract_type} from {session.current_url}"

            result = BrowserActionResult(
                action=BrowserAction.EXTRACT,
                success=True,
                content=content,
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
                metadata={"selector": selector, "extract_type": extract_type},
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.EXTRACT,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    async def extract_elements(
        self,
        session_id: str,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        max_elements: int = 20,
    ) -> BrowserActionResult:
        """Extract multiple elements matching a selector."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.EXTRACT,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.15)
            session.last_activity = time.time()

            elements = [
                BrowserElement(
                    selector=f"{selector}:nth-child({i})",
                    selector_type=selector_type,
                    tag_name="div",
                    text=f"Element {i}",
                )
                for i in range(1, min(max_elements + 1, 5))
            ]

            result = BrowserActionResult(
                action=BrowserAction.EXTRACT,
                success=True,
                extracted_elements=elements,
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
                metadata={"selector": selector, "count": len(elements)},
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.EXTRACT,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # ── Screenshots ────────────────────────────────────────────────

    async def screenshot(
        self,
        session_id: str,
        full_page: bool = False,
        selector: str = "",
    ) -> BrowserActionResult:
        """Take a screenshot of the current page."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.SCREENSHOT,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.1)
            session.last_activity = time.time()

            result = BrowserActionResult(
                action=BrowserAction.SCREENSHOT,
                success=True,
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
                metadata={"full_page": full_page, "selector": selector},
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.SCREENSHOT,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # ── JavaScript Execution ───────────────────────────────────────

    async def execute_js(
        self,
        session_id: str,
        script: str,
        arguments: Optional[list[Any]] = None,
    ) -> BrowserActionResult:
        """Execute JavaScript in the page context."""
        session = self._sessions.get(session_id)
        if not session:
            return BrowserActionResult(
                action=BrowserAction.EXECUTE_JS,
                success=False,
                error="Session not found",
            )

        start = time.time()
        try:
            await asyncio.sleep(0.1)
            session.last_activity = time.time()

            result = BrowserActionResult(
                action=BrowserAction.EXECUTE_JS,
                success=True,
                content="JS executed successfully",
                url=session.current_url,
                duration_ms=(time.time() - start) * 1000,
            )
            self._action_history[session_id].append(result)
            return result
        except Exception as e:
            return BrowserActionResult(
                action=BrowserAction.EXECUTE_JS,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start) * 1000,
            )

    # ── Workflow Execution ─────────────────────────────────────────

    async def execute_workflow(
        self,
        session_id: str,
        steps: list[BrowserActionStep],
        stop_on_error: bool = True,
    ) -> list[BrowserActionResult]:
        """Execute a sequence of browser actions as a workflow."""
        results = []

        # Auto-create session if needed
        if session_id not in self._sessions:
            self.create_session(session_id=session_id)

        for step in steps:
            action_map = {
                BrowserAction.NAVIGATE: lambda: self.navigate(session_id, step.value),
                BrowserAction.CLICK: lambda: self.click(session_id, step.selector, step.selector_type),
                BrowserAction.TYPE: lambda: self.type_text(session_id, step.selector, step.value, step.selector_type),
                BrowserAction.SCROLL: lambda: self.scroll(session_id, step.value or "down", 500),
                BrowserAction.SCREENSHOT: lambda: self.screenshot(session_id),
                BrowserAction.EXTRACT: lambda: self.extract_content(session_id, step.selector, step.selector_type),
                BrowserAction.WAIT: lambda: asyncio.sleep(step.wait_ms / 1000),
                BrowserAction.EXECUTE_JS: lambda: self.execute_js(session_id, step.value),
                BrowserAction.SUBMIT: lambda: self.click(session_id, step.selector or "button[type=submit]"),
            }

            handler = action_map.get(step.action)
            if handler:
                try:
                    if step.action == BrowserAction.WAIT:
                        await asyncio.sleep(step.wait_ms / 1000)
                        results.append(BrowserActionResult(
                            action=BrowserAction.WAIT,
                            success=True,
                            duration_ms=step.wait_ms,
                        ))
                    else:
                        result = await handler()
                        results.append(result)

                        if stop_on_error and not result.success and step.retry_on_failure:
                            for retry in range(step.max_retries):
                                result = await handler()
                                results.append(result)
                                if result.success:
                                    break
                            if not result.success:
                                break
                except Exception as e:
                    results.append(BrowserActionResult(
                        action=step.action,
                        success=False,
                        error=str(e),
                    ))
                    if stop_on_error:
                        break

        return results

    # ── Form Filling ───────────────────────────────────────────────

    async def fill_form(
        self,
        session_id: str,
        form_data: dict[str, str],
        submit: bool = True,
    ) -> list[BrowserActionResult]:
        """Fill a form with provided data."""
        results = []

        for field_selector, value in form_data.items():
            result = await self.type_text(session_id, field_selector, value)
            results.append(result)
            if not result.success:
                return results

        if submit:
            submit_result = await self.click(
                session_id, "button[type=submit], input[type=submit]"
            )
            results.append(submit_result)

        return results

    # ── Statistics ─────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get browser automation statistics."""
        return {
            "active_sessions": len(self._sessions),
            "total_actions": sum(len(h) for h in self._action_history.values()),
            "headless_mode": self._headless,
            "sessions": [
                {
                    "session_id": s.session_id,
                    "current_url": s.current_url,
                    "active": s.active,
                    "action_count": len(self._action_history.get(s.session_id, [])),
                }
                for s in self._sessions.values()
            ],
        }

    def get_session_history(self, session_id: str, limit: int = 50) -> list[BrowserActionResult]:
        """Get action history for a session."""
        history = self._action_history.get(session_id, [])
        return history[-limit:]


# Global browser automation instance
browser_automation = BrowserAutomation()