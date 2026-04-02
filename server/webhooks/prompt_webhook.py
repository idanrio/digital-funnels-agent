"""
PrimeFlow Prompt Webhook — Receive prompts from external website.

This module provides a FastAPI router that:
1. Receives structured JSON prompts via HTTP POST from an external website
2. Authenticates using a shared secret (WEBHOOK_SECRET in .env)
3. Validates the prompt structure (dry-run first)
4. Executes it through PromptRunner → Orchestrator → Report
5. Returns a structured result

Endpoint: POST /webhooks/prompt
Authentication: Header  X-Webhook-Secret: <secret>

⚠️ TEST MODULE — Can be reverted by removing:
   - This file (server/webhooks/prompt_webhook.py)
   - The __init__.py (server/webhooks/__init__.py)
   - The router include in server/main.py
   - The WEBHOOK_SECRET line in .env
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field

from server.core.prompt_runner import PromptRunner

logger = logging.getLogger("primeflow.webhook")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# ---------------------------------------------------------------------------
# Pydantic models for request/response
# ---------------------------------------------------------------------------


class WebhookCommand(BaseModel):
    """A single command within the prompt."""
    action: str
    # All other fields are dynamic — allow extra
    model_config = {"extra": "allow"}


class WebhookPayload(BaseModel):
    """The full prompt payload received from the external website."""
    location_id: str = Field(..., min_length=1, description="GHL Location ID")
    api_key: str = Field(..., min_length=1, description="GHL API Key (pit-...)")
    commands: List[WebhookCommand] = Field(
        ..., min_length=1, description="List of PrimeFlow commands to execute"
    )
    # 2FA approval code (required for execution)
    approval_code: str = Field(
        default="", description="2FA approval code (must match APPROVAL_SECRET in .env)"
    )
    # Optional metadata from the external website
    source: str = Field(default="webhook", description="Source identifier")
    callback_url: Optional[str] = Field(
        default=None, description="URL to POST results back to when done"
    )
    report_email: Optional[str] = Field(
        default=None, description="Override email for the report"
    )


class WebhookResponse(BaseModel):
    """Response returned to the external website."""
    success: bool
    run_id: str
    received_at: str
    commands_count: int
    summary: str
    validation_errors: List[str] = []
    report: Optional[Dict[str, int]] = None
    duration_seconds: float = 0.0
    message: str = ""


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _verify_secret(provided: Optional[str]) -> None:
    """
    Verify that the webhook secret matches.
    If WEBHOOK_SECRET is not set in .env → accept all (dev mode).
    If set → require exact match.
    """
    if not WEBHOOK_SECRET:
        # Dev mode — no secret configured, allow all
        logger.warning("WEBHOOK_SECRET not set — accepting request without auth (dev mode)")
        return

    if not provided or provided != WEBHOOK_SECRET:
        logger.warning("Webhook auth failed — invalid or missing X-Webhook-Secret header")
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — invalid or missing X-Webhook-Secret header.",
        )


# ---------------------------------------------------------------------------
# Endpoint: Receive & Execute Prompt
# ---------------------------------------------------------------------------

@router.post(
    "/prompt",
    response_model=WebhookResponse,
    summary="Receive a prompt from external website and execute it",
    description=(
        "Receives a structured PrimeFlow JSON prompt, validates it, "
        "executes all commands through the engine, and returns results. "
        "Authentication: X-Webhook-Secret header."
    ),
)
async def receive_prompt(
    payload: WebhookPayload,
    x_webhook_secret: Optional[str] = Header(default=None),
) -> WebhookResponse:
    """
    Main webhook endpoint for receiving prompts from the external website.

    Flow:
        1. Authenticate via X-Webhook-Secret header
        2. Convert Pydantic model → dict for PromptRunner
        3. Validate (dry-run)
        4. Execute through PromptRunner → Orchestrator → Report
        5. Return structured result
    """
    received_at = datetime.now().isoformat()
    run_id = f"wh-{int(time.time())}-{hash(payload.location_id) % 10000:04d}"

    # --- Auth ---
    _verify_secret(x_webhook_secret)

    # --- Convert to raw dict for PromptRunner ---
    raw_payload = {
        "location_id": payload.location_id,
        "api_key": payload.api_key,
        "commands": [cmd.model_dump() for cmd in payload.commands],
    }

    logger.info(
        f"[{run_id}] Webhook received: {len(payload.commands)} commands "
        f"from source={payload.source}"
    )

    # --- Step 1: Validate (fast, no API calls) ---
    validation = PromptRunner.validate(raw_payload)
    if not validation.is_valid:
        logger.warning(f"[{run_id}] Validation failed: {validation.validation_errors}")
        return WebhookResponse(
            success=False,
            run_id=run_id,
            received_at=received_at,
            commands_count=validation.commands_count,
            summary=validation.summary_text if validation.commands_count > 0 else "N/A",
            validation_errors=validation.validation_errors,
            message="Prompt validation failed — no commands were executed.",
        )

    # --- Step 2: Execute ---
    try:
        result = await PromptRunner.execute(
            raw_payload,
            send_report=True,
            source="webhook",
            run_id=run_id,
            approval_code=payload.approval_code,
            report_subject=(
                f"PrimeFlow Webhook Run [{run_id}] — "
                f"{validation.commands_count} commands — "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ),
        )
    except Exception as e:
        logger.error(f"[{run_id}] Execution error: {e}", exc_info=True)
        return WebhookResponse(
            success=False,
            run_id=run_id,
            received_at=received_at,
            commands_count=validation.commands_count,
            summary=validation.summary_text,
            validation_errors=[f"Execution error: {str(e)}"],
            message="Prompt execution failed with an unexpected error.",
        )

    # --- Step 3: Build response ---
    report_data = None
    if result.orchestrator_result:
        rd = result.orchestrator_result.get("report_data")
        if rd:
            report_data = {
                "created": len(rd.created),
                "updated": len(rd.updated),
                "duplicates": len(rd.duplicates),
                "errors": len(rd.errors),
            }

    logger.info(
        f"[{run_id}] Execution complete — "
        f"success={result.success}, duration={result.duration_seconds:.1f}s"
    )

    return WebhookResponse(
        success=result.success,
        run_id=run_id,
        received_at=received_at,
        commands_count=result.commands_count,
        summary=result.summary_text,
        validation_errors=result.validation_errors,
        report=report_data,
        duration_seconds=result.duration_seconds,
        message=(
            "Prompt executed successfully. Report sent via email."
            if result.success
            else "Prompt execution completed with issues."
        ),
    )


# ---------------------------------------------------------------------------
# Endpoint: Validate Only (dry-run from external website)
# ---------------------------------------------------------------------------

@router.post(
    "/prompt/validate",
    response_model=WebhookResponse,
    summary="Validate a prompt without executing",
    description="Dry-run validation — checks structure and fields, no API calls.",
)
async def validate_prompt(
    payload: WebhookPayload,
    x_webhook_secret: Optional[str] = Header(default=None),
) -> WebhookResponse:
    """
    Validate a prompt from external website without executing.
    Useful for the website to check before submitting.
    """
    received_at = datetime.now().isoformat()
    run_id = f"wh-val-{int(time.time())}"

    # --- Auth ---
    _verify_secret(x_webhook_secret)

    # --- Convert to raw dict ---
    raw_payload = {
        "location_id": payload.location_id,
        "api_key": payload.api_key,
        "commands": [cmd.model_dump() for cmd in payload.commands],
    }

    # --- Validate ---
    validation = PromptRunner.validate(raw_payload)

    return WebhookResponse(
        success=validation.is_valid,
        run_id=run_id,
        received_at=received_at,
        commands_count=validation.commands_count,
        summary=validation.summary_text if validation.commands_count > 0 else "N/A",
        validation_errors=validation.validation_errors,
        message=(
            "Prompt is valid — ready to execute."
            if validation.is_valid
            else "Prompt validation failed."
        ),
    )


# ---------------------------------------------------------------------------
# Endpoint: Health check for webhook
# ---------------------------------------------------------------------------

@router.get(
    "/prompt/health",
    summary="Webhook health check",
    description="Quick check that the webhook endpoint is alive.",
)
async def webhook_health():
    """Health check for the webhook endpoint."""
    return {
        "status": "ok",
        "service": "primeflow-webhook",
        "auth_enabled": bool(WEBHOOK_SECRET),
        "timestamp": datetime.now().isoformat(),
    }
