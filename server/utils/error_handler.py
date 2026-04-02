"""
PrimeFlow Error Handler — Smart Error Classification & Retry Logic

Classifies GHL API errors and determines retry strategy.
No AI. Pure code logic.
"""

from __future__ import annotations

import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


# ===========================================================================
# ERROR CLASSIFICATION
# ===========================================================================

@dataclass
class ClassifiedError:
    """A classified API error with retry guidance."""
    category: str           # auth, validation, rate_limit, server, network, duplicate, unknown
    status_code: int
    message: str
    response_body: str
    should_retry: bool
    max_retries: int
    retry_delays: list[float]
    action: str = ""        # The action that caused the error
    timestamp: str = ""


class ErrorClassifier:
    """
    Classify GHL API errors into actionable categories.
    Determines if/how to retry based on error type.
    """

    # Error patterns for duplicate detection
    DUPLICATE_PATTERNS = [
        "duplicate", "already exists", "conflict", "unique constraint",
        "can not create duplicate",
    ]

    @staticmethod
    def classify(result: dict, action: str = "") -> ClassifiedError:
        """
        Classify an API error result into a category.

        Args:
            result: The API response dict (from ghl.request())
            action: The action name that caused the error

        Returns:
            ClassifiedError with retry guidance
        """
        status = result.get("status_code", 0)
        error_msg = result.get("error", "")
        response_body = result.get("response_body", "")
        combined_text = f"{error_msg} {response_body}".lower()

        # Check for duplicate patterns first (even in 400 responses)
        if any(pat in combined_text for pat in ErrorClassifier.DUPLICATE_PATTERNS):
            return ClassifiedError(
                category="duplicate",
                status_code=status,
                message=error_msg,
                response_body=response_body,
                should_retry=False,
                max_retries=0,
                retry_delays=[],
                action=action,
                timestamp=datetime.now().isoformat(),
            )

        # Auth errors (401, 403)
        if status in (401, 403):
            return ClassifiedError(
                category="auth",
                status_code=status,
                message=error_msg,
                response_body=response_body,
                should_retry=False,
                max_retries=0,
                retry_delays=[],
                action=action,
                timestamp=datetime.now().isoformat(),
            )

        # Validation errors (400, 422)
        if status in (400, 422):
            return ClassifiedError(
                category="validation",
                status_code=status,
                message=error_msg,
                response_body=response_body,
                should_retry=False,
                max_retries=0,
                retry_delays=[],
                action=action,
                timestamp=datetime.now().isoformat(),
            )

        # Rate limit (429)
        if status == 429:
            return ClassifiedError(
                category="rate_limit",
                status_code=status,
                message=error_msg,
                response_body=response_body,
                should_retry=True,
                max_retries=5,
                retry_delays=[2.0, 4.0, 8.0, 16.0, 32.0],
                action=action,
                timestamp=datetime.now().isoformat(),
            )

        # Server errors (500-599)
        if 500 <= status < 600:
            return ClassifiedError(
                category="server",
                status_code=status,
                message=error_msg,
                response_body=response_body,
                should_retry=True,
                max_retries=3,
                retry_delays=[1.0, 3.0, 5.0],
                action=action,
                timestamp=datetime.now().isoformat(),
            )

        # Network errors (no status code — timeouts, connection refused, etc.)
        if status == 0:
            return ClassifiedError(
                category="network",
                status_code=0,
                message=error_msg,
                response_body=response_body,
                should_retry=True,
                max_retries=2,
                retry_delays=[3.0, 5.0],
                action=action,
                timestamp=datetime.now().isoformat(),
            )

        # Unknown
        return ClassifiedError(
            category="unknown",
            status_code=status,
            message=error_msg,
            response_body=response_body,
            should_retry=False,
            max_retries=0,
            retry_delays=[],
            action=action,
            timestamp=datetime.now().isoformat(),
        )


# ===========================================================================
# SMART RETRY
# ===========================================================================

class SmartRetry:
    """
    Execute an async function with smart retry logic based on error classification.
    """

    @staticmethod
    async def execute(
        func: Callable,
        *args: Any,
        action_name: str = "",
        **kwargs: Any,
    ) -> dict:
        """
        Execute func with retries based on ErrorClassifier.

        Returns:
            {
                "success": bool,
                "data": Any,
                "attempts": int,
                "error_type": str | None,
                "error_detail": str | None,
                "classified_error": ClassifiedError | None,
            }
        """
        raw = await func(*args, **kwargs)

        # engine.run() returns {"result": {...}} — unwrap if needed
        result = raw.get("result", raw) if isinstance(raw, dict) else raw

        # If first attempt succeeds, return immediately
        if result.get("success"):
            return {
                "success": True,
                "data": result.get("data"),
                "attempts": 1,
                "error_type": None,
                "error_detail": None,
                "classified_error": None,
            }

        # Classify the error
        classified = ErrorClassifier.classify(result, action=action_name)

        # If shouldn't retry, return immediately with classification
        if not classified.should_retry:
            return {
                "success": False,
                "data": raw,
                "attempts": 1,
                "error_type": classified.category,
                "error_detail": classified.message,
                "classified_error": classified,
            }

        # Retry loop
        for attempt in range(classified.max_retries):
            delay = (classified.retry_delays[attempt]
                     if attempt < len(classified.retry_delays)
                     else classified.retry_delays[-1])
            print(f"    ⏳ Retry {attempt + 1}/{classified.max_retries} "
                  f"({classified.category}) in {delay}s...")
            await asyncio.sleep(delay)

            raw = await func(*args, **kwargs)
            result = raw.get("result", raw) if isinstance(raw, dict) else raw
            if result.get("success"):
                return {
                    "success": True,
                    "data": result.get("data"),
                    "attempts": attempt + 2,  # +1 for initial, +1 for 0-index
                    "error_type": None,
                    "error_detail": None,
                    "classified_error": None,
                }

        # All retries exhausted
        final_classified = ErrorClassifier.classify(result, action=action_name)
        return {
            "success": False,
            "data": raw,
            "attempts": classified.max_retries + 1,
            "error_type": final_classified.category,
            "error_detail": final_classified.message,
            "classified_error": final_classified,
        }


# ===========================================================================
# ERROR TRACKER (aggregates errors across a full orchestration run)
# ===========================================================================

@dataclass
class ErrorEntry:
    """Single error entry for tracking."""
    action: str
    category: str
    status_code: int
    message: str
    response_body: str
    timestamp: str
    traceback_info: str = ""


class ErrorTracker:
    """Track all errors during an orchestration run."""

    def __init__(self):
        self.errors: list[ErrorEntry] = []

    def add(self, classified: ClassifiedError, traceback_info: str = ""):
        """Add an error from a ClassifiedError."""
        self.errors.append(ErrorEntry(
            action=classified.action,
            category=classified.category,
            status_code=classified.status_code,
            message=classified.message,
            response_body=classified.response_body,
            timestamp=classified.timestamp,
            traceback_info=traceback_info,
        ))

    def add_exception(self, action: str, exc: Exception):
        """Add a Python exception."""
        self.errors.append(ErrorEntry(
            action=action,
            category="exception",
            status_code=0,
            message=str(exc),
            response_body="",
            timestamp=datetime.now().isoformat(),
            traceback_info=traceback.format_exc(),
        ))

    @property
    def count(self) -> int:
        return len(self.errors)

    def summary(self) -> dict:
        """Return summary grouped by category."""
        by_category: dict[str, list[ErrorEntry]] = {}
        for e in self.errors:
            by_category.setdefault(e.category, []).append(e)
        return {
            "total": self.count,
            "by_category": {
                cat: len(entries) for cat, entries in by_category.items()
            },
            "entries": [
                {
                    "action": e.action,
                    "category": e.category,
                    "status_code": e.status_code,
                    "message": e.message,
                    "response_body": e.response_body[:200],
                    "timestamp": e.timestamp,
                }
                for e in self.errors
            ],
        }
