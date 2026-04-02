"""
PrimeFlow Prompt Runner — JSON Input → Orchestrator → Auto Report

Accepts a structured JSON payload (from landing page AI or direct input),
validates it, creates engine with the provided credentials,
runs all commands through the Orchestrator, and auto-generates a report.

NO AI. Pure code. Deterministic.

JSON payload format:
{
    "location_id": "abc123",
    "api_key": "pit-xxxxx",
    "commands": [
        {"action": "create_tag", "name": "hot-lead"},
        {"action": "create_contact", "first_name": "Yossi", ...},
        ...
    ]
}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import smtplib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from server.core.engine import PrimeFlowEngine, REQUIRED_FIELDS
from server.core.orchestrator import PrimeFlowOrchestrator, DEDUP_MAP
from server.integrations.ghl import GHLClient

logger = logging.getLogger("primeflow.runner")

# ---------------------------------------------------------------------------
# Run history directory
# ---------------------------------------------------------------------------
RUNS_DIR = Path(__file__).parent.parent.parent / "runs"

# ---------------------------------------------------------------------------
# 2FA Approval config
# ---------------------------------------------------------------------------
APPROVAL_SECRET = os.getenv("APPROVAL_SECRET", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "primeflow.ai@gmail.com")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Pending runs store (in-memory — survives only while server is running)
# Each entry: { pending_id: { payload, result, location_name, timestamp, status } }
# ---------------------------------------------------------------------------
PENDING_RUNS: dict[str, dict] = {}


# ===========================================================================
# VALIDATION RESULT
# ===========================================================================

@dataclass
class PromptRunResult:
    """Result of a prompt validation + execution."""
    run_id: str = ""
    location_id: str = ""
    api_key: str = ""
    commands_count: int = 0
    commands_summary: dict[str, int] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    orchestrator_result: dict | None = None
    duration_seconds: float = 0.0
    source: str = ""  # "cli", "api", "webhook"

    @property
    def is_valid(self) -> bool:
        return bool(
            self.location_id
            and self.api_key
            and self.commands_count > 0
            and not self.validation_errors
        )

    @property
    def success(self) -> bool:
        # Note: credentials are cleared after execution, so check
        # orchestrator_result directly (not is_valid, which requires api_key)
        return (
            self.orchestrator_result is not None
            and self.commands_count > 0
            and not self.validation_errors
        )

    @property
    def summary_text(self) -> str:
        parts = [f"{count}x {action}" for action, count in self.commands_summary.items()]
        return f"{self.commands_count} commands: {', '.join(parts)}"


# ===========================================================================
# VALIDATOR
# ===========================================================================

class _Validator:
    """Validate a JSON payload before execution."""

    # Actions that the orchestrator knows how to handle
    KNOWN_ACTIONS: set[str] = set(DEDUP_MAP.keys()) | set(REQUIRED_FIELDS.keys()) | {"raw"}

    @classmethod
    def validate(cls, payload: dict) -> PromptRunResult:
        """
        Validate payload structure, credentials, and all commands.
        Returns a PromptRunResult with errors/warnings populated.
        """
        result = PromptRunResult()
        errors = result.validation_errors
        warnings = result.validation_warnings

        # --- Credentials ---
        location_id = payload.get("location_id", "")
        api_key = payload.get("api_key", "")

        if not location_id:
            errors.append("Missing 'location_id' — location_id is required.")
        elif not isinstance(location_id, str):
            errors.append("'location_id' must be a string.")
        else:
            result.location_id = location_id.strip()

        if not api_key:
            errors.append("Missing 'api_key' — API key is required.")
        elif not isinstance(api_key, str):
            errors.append("'api_key' must be a string.")
        else:
            result.api_key = api_key.strip()

        # --- Commands ---
        commands = payload.get("commands")
        if commands is None:
            errors.append("Missing 'commands' — commands list is required.")
            return result
        if not isinstance(commands, list):
            errors.append("'commands' must be a list of command objects.")
            return result
        if len(commands) == 0:
            errors.append("'commands' list is empty — at least one command is required.")
            return result

        # --- Validate each command ---
        action_counts: dict[str, int] = {}
        for i, cmd in enumerate(commands, 1):
            if not isinstance(cmd, dict):
                errors.append(f"Command #{i}: must be a JSON object, got {type(cmd).__name__}.")
                continue

            action = cmd.get("action", "")
            if not action:
                errors.append(f"Command #{i}: missing 'action' field.")
                continue
            if not isinstance(action, str):
                errors.append(f"Command #{i}: 'action' must be a string.")
                continue

            action = action.strip()

            # Check if action is known
            if action not in cls.KNOWN_ACTIONS:
                errors.append(
                    f"Command #{i}: unknown action '{action}'. "
                    f"Check the action name or refer to the API reference."
                )
                continue

            # Check required fields
            required = REQUIRED_FIELDS.get(action, [])
            for field_spec in required:
                # field_spec can be "field_a|field_b" meaning either is acceptable
                alternatives = field_spec.split("|")
                if not any(cmd.get(alt) for alt in alternatives):
                    errors.append(
                        f"Command #{i} ({action}): missing required field "
                        f"'{alternatives[0]}'"
                        + (f" (or '{alternatives[1]}')" if len(alternatives) > 1 else "")
                        + "."
                    )

            action_counts[action] = action_counts.get(action, 0) + 1

        result.commands_count = len(commands)
        result.commands_summary = action_counts

        return result


# ===========================================================================
# PROMPT RUNNER
# ===========================================================================

class PromptRunner:
    """
    Main entry point for running PrimeFlow prompts.

    Takes a JSON payload → validates → creates engine → runs orchestrator
    → auto-generates report (PDF + HTML + Text + Email).

    Usage:
        result = await PromptRunner.execute(payload)
        result = await PromptRunner.execute_from_file("prompt.json")
        result = PromptRunner.validate(payload)  # dry-run
    """

    @staticmethod
    def _generate_run_id(source: str = "") -> str:
        """Generate a unique run ID: pf-{source}-{timestamp}-{short_uuid}"""
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        short = uuid.uuid4().hex[:6]
        prefix = f"pf-{source}-" if source else "pf-"
        return f"{prefix}{ts}-{short}"

    @staticmethod
    def _save_run_history(result: PromptRunResult, commands: list) -> None:
        """
        Save a lightweight JSON summary of the run to runs/ directory.
        ~2-5 KB per run. Non-blocking — errors are silently logged.
        """
        try:
            RUNS_DIR.mkdir(parents=True, exist_ok=True)

            # Build summary
            report_summary = None
            results_detail = []
            if result.orchestrator_result:
                rd = result.orchestrator_result.get("report_data")
                if rd:
                    report_summary = {
                        "created": len(rd.created),
                        "updated": len(rd.updated),
                        "duplicates": len(rd.duplicates),
                        "errors": len(rd.errors),
                    }
                    # Per-action summary (lightweight — no full API responses)
                    for ar in rd.results:
                        results_detail.append({
                            "action": ar.action,
                            "status": ar.status,
                            "category": ar.category,
                            "name": ar.resource_name,
                            "id": ar.resource_id,
                            "error": ar.error or None,
                        })

            run_data = {
                "run_id": result.run_id,
                "timestamp": datetime.now().isoformat(),
                "source": result.source,
                "location_id": result.location_id,
                "api_key_prefix": result.api_key[:12] + "..." if result.api_key else "",
                "success": result.success,
                "commands_count": result.commands_count,
                "commands_summary": result.commands_summary,
                "report": report_summary,
                "results": results_detail,
                "duration_seconds": round(result.duration_seconds, 2),
                "validation_errors": result.validation_errors or None,
            }

            # Save file: runs/pf-webhook-20260315-203700-a1b2c3.json
            file_path = RUNS_DIR / f"{result.run_id}.json"
            file_path.write_text(
                json.dumps(run_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"[{result.run_id}] Run history saved → {file_path}")

        except Exception as e:
            # Never let history saving break execution
            logger.warning(f"Failed to save run history: {e}")

    @staticmethod
    async def _fetch_location_name(api_key: str, location_id: str) -> str:
        """Quick GHL call to get sub-account name for approval display."""
        try:
            client = GHLClient(api_key=api_key, location_id=location_id)
            result = await client.get_location(location_id)
            await client.close()
            loc = result.get("data", {})
            # Handle both nested and flat response
            if "location" in loc:
                loc = loc["location"]
            return loc.get("name", loc.get("businessName", "Unknown"))
        except Exception:
            return "Unable to fetch"

    @staticmethod
    async def _request_approval_cli(
        result: "PromptRunResult",
        location_name: str,
    ) -> bool:
        """
        Interactive CLI 2FA approval.
        Shows run details and requires the user to type APPROVE to proceed.
        """
        print("\n" + "=" * 65)
        print("  🔒 RUN APPROVAL REQUIRED (2FA)")
        print("=" * 65)
        print(f"  Location ID:    {result.location_id}")
        print(f"  Sub Account:    {location_name}")
        print(f"  API Key:        {result.api_key[:12]}...")
        print(f"  Commands:       {result.commands_count}")
        print(f"  Summary:        {result.summary_text}")
        print("=" * 65)
        print()
        try:
            answer = input("  ⚠️  Type APPROVE to execute, or anything else to cancel: ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer != "APPROVE":
            print("\n  ❌ Run CANCELLED — approval not granted.\n")
            return False
        print("\n  ✅ Approved — starting execution...\n")
        return True

    @staticmethod
    def _verify_approval_code(approval_code: str) -> bool:
        """
        Verify the approval code for API/webhook 2FA.
        If APPROVAL_SECRET is not set in .env → require CLI approval.
        If set → code must match exactly.
        """
        if not APPROVAL_SECRET:
            return False
        return approval_code == APPROVAL_SECRET

    @staticmethod
    def _generate_pending_id() -> str:
        """Generate a short unique ID for a pending run."""
        return f"pending-{uuid.uuid4().hex[:10]}"

    @staticmethod
    def _extract_resource_name(cmd: dict) -> str:
        """Extract the human-readable name from a command."""
        for key in ("name", "title", "business_name", "businessName",
                     "question", "key", "label"):
            if cmd.get(key):
                val = str(cmd[key])
                return val[:60] + "..." if len(val) > 60 else val
        # Fallback: email for users/contacts, first_name+last_name
        if cmd.get("email"):
            name_parts = []
            for k in ("first_name", "firstName"):
                if cmd.get(k):
                    name_parts.append(cmd[k])
            for k in ("last_name", "lastName"):
                if cmd.get(k):
                    name_parts.append(cmd[k])
            if name_parts:
                return f"{' '.join(name_parts)} ({cmd['email']})"
            return cmd["email"]
        return cmd.get("action", "unknown")

    @staticmethod
    def _extract_resource_details(cmd: dict) -> list[tuple[str, str]]:
        """Extract key detail pairs from a command for display."""
        details = []
        action = cmd.get("action", "")

        # Map of action → fields to show
        detail_map = {
            "create_custom_field": [
                ("data_type", "Type"), ("dataType", "Type"),
                ("options", "Options"),
            ],
            "create_template": [
                ("type", "Type"), ("subject", "Subject"),
                ("body", "Body"),
            ],
            "create_calendar": [
                ("calendarType", "Type"), ("slotDuration", "Duration"),
                ("description", "Description"),
            ],
            "create_user": [
                ("email", "Email"), ("phone", "Phone"), ("role", "Role"),
            ],
            "create_contact": [
                ("email", "Email"), ("phone", "Phone"), ("tags", "Tags"),
            ],
            "create_custom_object": [
                ("key", "Key"), ("description", "Description"),
            ],
            "create_association": [
                ("firstObjectKey", "Object A"), ("secondObjectKey", "Object B"),
                ("relationship", "Relationship"),
            ],
            "create_ai_agent": [
                ("business_name", "Business"), ("businessName", "Business"),
                ("mode", "Mode"), ("personality", "Personality"),
            ],
            "create_membership": [
                ("description", "Description"),
            ],
            "create_opportunity": [
                ("monetary_value", "Value"), ("monetaryValue", "Value"),
                ("status", "Status"),
            ],
        }

        keys = detail_map.get(action, [])
        seen_labels: set[str] = set()
        for cmd_key, label in keys:
            if label in seen_labels:
                continue
            val = cmd.get(cmd_key)
            if val is not None and val != "":
                if isinstance(val, list):
                    if len(val) <= 5:
                        val = ", ".join(str(v) for v in val)
                    else:
                        val = ", ".join(str(v) for v in val[:4]) + f"... (+{len(val)-4})"
                else:
                    val = str(val)
                if len(val) > 80:
                    val = val[:77] + "..."
                details.append((label, val))
                seen_labels.add(label)
        return details

    @staticmethod
    def _build_approval_email(
        pending_id: str,
        result: "PromptRunResult",
        location_name: str,
        commands: list,
    ) -> str:
        """Build an HTML approval email that mirrors the execution report layout."""
        approve_url = f"{SERVER_URL}/api/approve-run/{pending_id}"
        reject_url = f"{SERVER_URL}/api/reject-run/{pending_id}"

        # ── Group commands by category ──
        # Same category mapping as the orchestrator
        category_map = {
            "create_custom_field": "custom_fields",
            "create_tag": "tags",
            "create_contact": "contacts",
            "create_template": "templates",
            "create_calendar": "calendars",
            "create_user": "users",
            "create_custom_object": "custom_objects",
            "create_association": "associations",
            "create_ai_agent": "ai_agents",
            "create_membership": "memberships",
            "create_opportunity": "opportunities",
            "create_knowledge_base": "knowledge_bases",
            "create_kb_faq": "kb_faqs",
            "create_custom_value": "custom_values",
            "create_product": "products",
            "create_appointment": "appointments",
            "create_pipeline": "pipelines",
        }

        categories: dict[str, list[dict]] = {}
        for cmd in commands:
            action = cmd.get("action", "")
            cat = category_map.get(action, action.replace("create_", "").replace("update_", ""))
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(cmd)

        # ── Build category sections HTML ──
        cat_sections = ""
        for category, cmds in categories.items():
            cat_label = category.upper().replace("_", " ")

            # Build items list
            items_html = ""
            for cmd in cmds:
                name = PromptRunner._extract_resource_name(cmd)
                details = PromptRunner._extract_resource_details(cmd)

                # Properties sub-table
                props_html = ""
                if details:
                    prop_rows = ""
                    for label, val in details:
                        prop_rows += (
                            f"<tr>"
                            f"<td style='padding:2px 8px 2px 0;color:#718096;"
                            f"font-size:11px;white-space:nowrap;'>{label}:</td>"
                            f"<td style='padding:2px 0;font-size:11px;color:#4a5568;'>"
                            f"{val}</td></tr>"
                        )
                    props_html = (
                        f"<table style='margin:4px 0 0 16px;border-collapse:collapse;'>"
                        f"{prop_rows}</table>"
                    )

                items_html += (
                    f"<div style='padding:6px 12px;border-bottom:1px solid #edf2f7;'>"
                    f"<span style='font-size:13px;font-weight:600;color:#2d3748;'>"
                    f"⏳ {name}</span>"
                    f"{props_html}"
                    f"</div>"
                )

            cat_sections += f"""
            <div style='margin-bottom:6px;border:1px solid #e2e8f0;border-radius:8px;
                 overflow:hidden;background:white;'>
                <div style='padding:12px 16px;background:#f7fafc;
                     border-bottom:1px solid #e2e8f0;'>
                    <span style='font-weight:700;color:#2d3748;font-size:14px;'>
                        <span style='display:inline-block;margin-right:8px;
                              font-size:12px;color:#a0aec0;'>&#9654;</span>
                        {cat_label}
                    </span>
                    <span style='color:#718096;font-size:13px;margin-left:8px;'>
                        ({len(cmds)} pending)</span>
                    <span style='display:inline-block;margin-left:8px;padding:2px 8px;
                          background:#ebf8ff;color:#2b6cb0;border-radius:99px;
                          font-size:11px;font-weight:600;'>
                        {len(cmds)} to create</span>
                </div>
                <div style='padding:4px 0;'>
                    {items_html}
                </div>
            </div>"""

        # ── Summary bar ──
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,
     Arial,sans-serif;max-width:900px;margin:0 auto;padding:20px;
     background:#f0f2f5;color:#1a202c;'>

    <!-- HEADER — same as execution report -->
    <div style='background:linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
         color:white;padding:24px;border-radius:12px 12px 0 0;'>
        <h1 style='margin:0;font-size:22px;font-weight:700;letter-spacing:-0.3px;'>
            🔒 PrimeFlow Run Approval Required</h1>
        <p style='margin:6px 0 0;font-size:13px;color:#fbbf24;font-weight:600;'>
            {location_name} — {result.run_id}
        </p>
        <table style='color:#e2e8f0;margin-top:12px;font-size:13px;
               border-collapse:collapse;'>
            <tr><td style='padding:3px 18px 3px 0;color:#94a3b8;'>Location ID:</td>
                <td style='font-weight:500;'>{result.location_id}</td></tr>
            <tr><td style='padding:3px 18px 3px 0;color:#94a3b8;'>Sub Account:</td>
                <td style='font-weight:500;'>{location_name}</td></tr>
            <tr><td style='padding:3px 18px 3px 0;color:#94a3b8;'>Pending ID:</td>
                <td style='font-weight:500;'>{pending_id}</td></tr>
            <tr><td style='padding:3px 18px 3px 0;color:#94a3b8;'>Submitted:</td>
                <td style='font-weight:500;'>{now_str}</td></tr>
        </table>
    </div>

    <!-- SUMMARY BAR — same style as report -->
    <div style='background:#ffffff;padding:14px 20px;
         border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;
         display:flex;'>
        <table style='width:100%;border-collapse:collapse;'>
            <tr>
                <td style='text-align:center;padding:8px;'>
                    <div style='font-size:24px;font-weight:800;color:#2d3748;'>
                        {result.commands_count}</div>
                    <div style='font-size:11px;color:#718096;font-weight:600;
                         text-transform:uppercase;'>Total Commands</div>
                </td>
                <td style='text-align:center;padding:8px;'>
                    <div style='font-size:24px;font-weight:800;color:#3182ce;'>
                        {len(categories)}</div>
                    <div style='font-size:11px;color:#718096;font-weight:600;
                         text-transform:uppercase;'>Categories</div>
                </td>
                <td style='text-align:center;padding:8px;'>
                    <div style='font-size:24px;font-weight:800;color:#dd6b20;'>
                        ⏳</div>
                    <div style='font-size:11px;color:#718096;font-weight:600;
                         text-transform:uppercase;'>Awaiting Approval</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- APPROVE / DISAPPROVE BUTTONS — TOP -->
    <div style='background:#ffffff;padding:16px 20px;text-align:center;
         border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;
         border-bottom:1px solid #e2e8f0;'>
        <a href="{approve_url}"
           style='display:inline-block;padding:14px 48px;background:#38a169;
           color:white;text-decoration:none;border-radius:8px;font-size:16px;
           font-weight:700;margin-right:16px;'>
            ✅ APPROVE</a>
        <a href="{reject_url}"
           style='display:inline-block;padding:14px 48px;background:#e53e3e;
           color:white;text-decoration:none;border-radius:8px;font-size:16px;
           font-weight:700;'>
            ❌ DISAPPROVE</a>
        <p style='margin:8px 0 0;font-size:11px;color:#a0aec0;'>
            Expires in 30 minutes</p>
    </div>

    <!-- BODY — Category Sections (same layout as execution report) -->
    <div style='background:#f7fafc;padding:16px;
         border-left:1px solid #e2e8f0;border-right:1px solid #e2e8f0;'>
        {cat_sections}
    </div>

    <!-- APPROVE / DISAPPROVE BUTTONS — BOTTOM -->
    <div style='background:#ffffff;padding:16px 20px;text-align:center;
         border:1px solid #e2e8f0;border-top:none;'>
        <a href="{approve_url}"
           style='display:inline-block;padding:14px 48px;background:#38a169;
           color:white;text-decoration:none;border-radius:8px;font-size:16px;
           font-weight:700;margin-right:16px;'>
            ✅ APPROVE</a>
        <a href="{reject_url}"
           style='display:inline-block;padding:14px 48px;background:#e53e3e;
           color:white;text-decoration:none;border-radius:8px;font-size:16px;
           font-weight:700;'>
            ❌ DISAPPROVE</a>
    </div>

    <!-- FOOTER -->
    <div style='padding:16px;text-align:center;font-size:11px;color:#a0aec0;
         border-radius:0 0 12px 12px;background:#f7fafc;
         border:1px solid #e2e8f0;border-top:none;'>
        PrimeFlow AI &bull; 2FA Run Approval &bull; {now_str}
    </div>
</body>
</html>"""

    @staticmethod
    def _send_approval_email(
        pending_id: str, email_html: str, location_name: str = "",
        commands_summary: str = "",
    ) -> bool:
        """Send the approval email via SMTP with plain text fallback for Gmail deliverability."""
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")

        if not smtp_user or not smtp_pass:
            logger.warning("SMTP credentials not configured — cannot send approval email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = "PrimeFlow AI <support@primeflow.ai>"
            msg["To"] = ADMIN_EMAIL
            loc_label = f" {location_name} —" if location_name else ""
            msg["Subject"] = f"PrimeFlow Run Approval Required —{loc_label} {pending_id}"

            # Plain text version (critical for Gmail inbox delivery)
            approve_url = f"{SERVER_URL}/api/approve-run/{pending_id}"
            reject_url = f"{SERVER_URL}/api/reject-run/{pending_id}"
            plain_text = (
                f"PrimeFlow Run Approval Required\n"
                f"{'=' * 40}\n\n"
                f"Pending ID: {pending_id}\n"
                f"Sub Account: {location_name}\n"
                f"Commands: {commands_summary}\n\n"
                f"APPROVE: {approve_url}\n"
                f"DISAPPROVE: {reject_url}\n\n"
                f"This approval expires in 30 minutes.\n"
                f"PrimeFlow AI - 2FA Run Approval System"
            )
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(email_html, "html", "utf-8"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"Approval email sent to {ADMIN_EMAIL} for {pending_id}")
            print(f"  📧 Approval email sent to {ADMIN_EMAIL}")
            return True

        except Exception as e:
            logger.error(f"Failed to send approval email: {e}")
            print(f"  ❌ Failed to send approval email: {e}")
            return False

    @staticmethod
    def store_pending_run(
        pending_id: str,
        payload: dict,
        result: "PromptRunResult",
        location_name: str,
    ) -> None:
        """Store a run as pending, awaiting approval."""
        PENDING_RUNS[pending_id] = {
            "payload": payload,
            "result": result,
            "location_name": location_name,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",  # pending | approved | rejected | expired
        }
        logger.info(f"[{pending_id}] Stored as pending run")

    @staticmethod
    async def execute_approved_run(pending_id: str) -> dict:
        """
        Execute a previously stored pending run after admin approval.
        Returns the full execution result dict.
        """
        if pending_id not in PENDING_RUNS:
            return {"success": False, "error": "Pending run not found or expired."}

        pending = PENDING_RUNS[pending_id]

        if pending["status"] != "pending":
            return {"success": False, "error": f"Run already {pending['status']}."}

        # Check expiry (30 minutes)
        submitted = datetime.fromisoformat(pending["timestamp"])
        elapsed = (datetime.now() - submitted).total_seconds()
        if elapsed > 1800:  # 30 minutes
            pending["status"] = "expired"
            return {"success": False, "error": "Approval link expired (30 min limit)."}

        # Mark as approved
        pending["status"] = "approved"
        logger.info(f"[{pending_id}] Run APPROVED — executing...")
        print(f"\n  ✅ [{pending_id}] Run APPROVED via email — starting execution...")

        payload = pending["payload"]
        result = pending["result"]

        # Execute the run
        exec_result = await PromptRunner.execute(
            payload,
            source=result.source or "api",
            run_id=result.run_id,
            approval_code=APPROVAL_SECRET or "__email_approved__",
        )

        # Clean up after execution
        pending["status"] = "completed"
        pending.pop("payload", None)  # Free memory — don't keep credentials

        return {
            "success": exec_result.success,
            "run_id": exec_result.run_id,
            "commands_count": exec_result.commands_count,
            "summary": exec_result.summary_text,
            "duration_seconds": exec_result.duration_seconds,
            "report": None,
        }

    @staticmethod
    def reject_pending_run(pending_id: str) -> dict:
        """
        Reject a pending run. Data is preserved for review but run won't execute.
        """
        if pending_id not in PENDING_RUNS:
            return {"success": False, "error": "Pending run not found or expired."}

        pending = PENDING_RUNS[pending_id]

        if pending["status"] != "pending":
            return {"success": False, "error": f"Run already {pending['status']}."}

        pending["status"] = "rejected"
        # Clear credentials but keep summary for review
        if "payload" in pending:
            pending["payload"].pop("api_key", None)
            pending["payload"].pop("location_id", None)

        logger.info(f"[{pending_id}] Run REJECTED by admin")
        print(f"\n  ❌ [{pending_id}] Run REJECTED by admin")

        return {
            "success": True,
            "status": "rejected",
            "message": "Run has been disapproved. Data preserved for review.",
            "location_name": pending.get("location_name", ""),
            "commands_count": pending.get("result", PromptRunResult()).commands_count,
        }

    @staticmethod
    def get_pending_run(pending_id: str) -> dict | None:
        """Get info about a pending run (without sensitive data)."""
        if pending_id not in PENDING_RUNS:
            return None
        p = PENDING_RUNS[pending_id]
        r = p.get("result", PromptRunResult())
        return {
            "pending_id": pending_id,
            "status": p["status"],
            "location_name": p.get("location_name", ""),
            "commands_count": r.commands_count,
            "summary": r.summary_text,
            "submitted": p.get("timestamp", ""),
        }

    @staticmethod
    def _clear_credentials(result: "PromptRunResult") -> None:
        """
        Wipe sensitive credentials from the result object after run completes.
        Ensures api_key and location_id don't persist in memory.
        """
        result.api_key = ""
        result.location_id = ""
        logger.info(f"[{result.run_id}] Credentials cleared from result object")

    @staticmethod
    def _clear_file_credentials(file_path: str) -> None:
        """
        Remove api_key and location_id from the JSON template file
        after execution, so credentials don't remain on disk.
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return
            data = json.loads(path.read_text(encoding="utf-8"))
            changed = False
            if "api_key" in data:
                data["api_key"] = ""
                changed = True
            if "location_id" in data:
                data["location_id"] = ""
                changed = True
            if changed:
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(f"Credentials cleared from file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clear credentials from file: {e}")

    @staticmethod
    async def execute(
        payload: dict | str,
        send_report: bool = True,
        report_subject: str = "",
        source: str = "",
        run_id: str = "",
        approval_code: str = "",
        skip_approval: bool = False,
    ) -> PromptRunResult:
        """
        Parse, validate, and execute a JSON prompt.

        Args:
            payload: JSON dict or JSON string
            send_report: Whether to email the report (default True)
            report_subject: Custom email subject
            source: Origin of the prompt ("cli", "api", "webhook")
            run_id: Optional pre-generated run ID (webhook passes its own)

        Returns:
            PromptRunResult with validation info + orchestrator results
        """
        start = time.time()

        # Generate run_id
        _run_id = run_id or PromptRunner._generate_run_id(source)

        # Step 1: Parse JSON if string
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                result = PromptRunResult(run_id=_run_id, source=source)
                result.validation_errors.append(f"Invalid JSON: {e}")
                return result

        if not isinstance(payload, dict):
            result = PromptRunResult(run_id=_run_id, source=source)
            result.validation_errors.append("Payload must be a JSON object.")
            return result

        # Step 2: Validate
        result = _Validator.validate(payload)
        result.run_id = _run_id
        result.source = source
        if not result.is_valid:
            return result

        # Step 2.5: 2FA APPROVAL GATE
        # Fetch location name for display
        location_name = await PromptRunner._fetch_location_name(
            result.api_key, result.location_id
        )

        if skip_approval:
            logger.info(f"[{_run_id}] 2FA skipped — skip_approval=True (batch mode)")
        else:
            # ALL sources (cli, api, webhook) use email-based 2FA
            # If approval_code matches secret → pre-approved (e.g. from email callback)
            if not PromptRunner._verify_approval_code(approval_code):
                # Store as pending and send approval email
                pending_id = PromptRunner._generate_pending_id()
                commands = payload.get("commands", [])

                # Build and send approval email
                email_html = PromptRunner._build_approval_email(
                    pending_id, result, location_name, commands
                )
                email_sent = PromptRunner._send_approval_email(
                    pending_id, email_html, location_name
                )

                # Store the pending run
                PromptRunner.store_pending_run(
                    pending_id, payload, result, location_name
                )

                logger.warning(f"[{_run_id}] 2FA approval required — "
                               f"pending_id={pending_id}, email_sent={email_sent}")

                result.orchestrator_result = {
                    "approval_required": True,
                    "pending_id": pending_id,
                    "location_name": location_name,
                    "location_id": result.location_id,
                    "commands_count": result.commands_count,
                    "summary": result.summary_text,
                    "email_sent": email_sent,
                    "admin_email": ADMIN_EMAIL,
                    "message": (
                        f"Approval email sent to {ADMIN_EMAIL}. "
                        f"Click APPROVE in the email to start the run, "
                        f"or DISAPPROVE to cancel."
                    ),
                }
                # Don't clear credentials yet — they're stored in pending run
                return result

        logger.info(f"[{_run_id}] 2FA approved — source={source}")

        # Step 3: Print header
        print("\n" + "=" * 65)
        print("  PrimeFlow Prompt Runner")
        print(f"  Run ID:   {result.run_id}")
        print(f"  Source:   {result.source or 'direct'}")
        print(f"  Location: {result.location_id}")
        print(f"  Sub Acct: {location_name}")
        print(f"  Commands: {result.commands_count}")
        print(f"  Summary:  {result.summary_text}")
        print(f"  Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 65)

        # Step 4: Create engine with provided credentials
        ghl_client = GHLClient(
            api_key=result.api_key,
            location_id=result.location_id,
        )
        engine = PrimeFlowEngine(ghl_client=ghl_client)
        orchestrator = PrimeFlowOrchestrator(engine)

        # Step 5: Run orchestrator
        commands = payload.get("commands", [])
        try:
            subject = report_subject or (
                f"PrimeFlow Run [{_run_id}] — "
                f"{result.commands_count} commands — "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            orch_result = await orchestrator.run(
                commands,
                send_report=send_report,
                report_subject=subject,
            )

            result.orchestrator_result = orch_result
            result.duration_seconds = time.time() - start

            # Print summary
            report_data = orch_result.get("report_data")
            email_result = orch_result.get("email_result", {})
            print(f"\n{'='*65}")
            print(f"  PROMPT RUN — COMPLETE  [{result.run_id}]")
            print(f"{'='*65}")
            if report_data:
                print(f"  Created:    {len(report_data.created)}")
                print(f"  Updated:    {len(report_data.updated)}")
                print(f"  Duplicates: {len(report_data.duplicates)}")
                print(f"  Errors:     {len(report_data.errors)}")
            print(f"  Duration:   {result.duration_seconds:.1f}s")
            print(f"  Report:     {email_result.get('method', 'N/A')}")
            print(f"{'='*65}\n")

        except Exception as e:
            result.validation_errors.append(f"Execution error: {e}")
            result.duration_seconds = time.time() - start

        # Step 6: Save run history (non-blocking, never fails main flow)
        PromptRunner._save_run_history(result, commands)

        # Step 7: CLEAR CREDENTIALS — wipe api_key and location_id
        # from result object so they don't persist in memory
        PromptRunner._clear_credentials(result)

        # Also wipe from the payload dict in memory
        if isinstance(payload, dict):
            payload.pop("api_key", None)
            payload.pop("location_id", None)

        print("  🔒 Credentials cleared from memory.")

        return result

    @staticmethod
    def validate(payload: dict | str) -> PromptRunResult:
        """
        Validate a prompt without executing (dry-run).

        Args:
            payload: JSON dict or JSON string

        Returns:
            PromptRunResult with validation info only
        """
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError as e:
                result = PromptRunResult()
                result.validation_errors.append(f"Invalid JSON: {e}")
                return result

        if not isinstance(payload, dict):
            result = PromptRunResult()
            result.validation_errors.append("Payload must be a JSON object.")
            return result

        return _Validator.validate(payload)

    @staticmethod
    async def execute_from_file(
        file_path: str,
        send_report: bool = True,
        report_subject: str = "",
        source: str = "",
    ) -> PromptRunResult:
        """
        Read a JSON file and execute it.

        Args:
            file_path: Path to JSON file
            send_report: Whether to email the report
            report_subject: Custom email subject
            source: Origin of the prompt

        Returns:
            PromptRunResult
        """
        path = Path(file_path)
        if not path.exists():
            result = PromptRunResult()
            result.validation_errors.append(f"File not found: {file_path}")
            return result

        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            result = PromptRunResult()
            result.validation_errors.append(f"Error reading file: {e}")
            return result

        result = await PromptRunner.execute(
            text,
            send_report=send_report,
            report_subject=report_subject,
            source=source,
        )

        # Clear credentials from the JSON file after execution
        if result.success:
            PromptRunner._clear_file_credentials(file_path)

        return result
