"""
PrimeFlow AI Super Worker - Main Server

FastAPI application that serves:
1. WebSocket endpoint for real-time chat with the AI agent
2. REST endpoints for file uploads and configuration
3. Webhook receivers for GHL and external services
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import uuid

from server.core.agent import PrimeFlowAgent
from server.core.prompt_runner import PromptRunner
from server.webhooks.prompt_webhook import router as prompt_webhook_router

app = FastAPI(
    title="PrimeFlow AI Super Worker",
    description="AI agent that operates the GoHighLevel platform",
    version="0.1.0"
)

# Allow the GHL-embedded widget to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production to your GHL domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active agents per session
active_agents: dict[str, PrimeFlowAgent] = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "primeflow-ai"}


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat with the AI agent.
    The chat widget connects here for streaming communication.
    """
    await websocket.accept()

    # Create or retrieve agent for this session
    if session_id not in active_agents:
        active_agents[session_id] = PrimeFlowAgent()

    agent = active_agents[session_id]

    try:
        while True:
            # Receive message from chat widget
            data = await websocket.receive_text()
            message = json.loads(data)

            # Send "thinking" status
            await websocket.send_json({
                "type": "status",
                "status": "thinking",
                "message": "Processing your request..."
            })

            # Process through the agent
            result = await agent.process_message(message.get("text", ""))

            # Send actions taken (for progress display)
            for action in result.get("actions", []):
                await websocket.send_json({
                    "type": "action",
                    "tool": action["tool"],
                    "input": action["input"],
                    "result": action["result"]
                })

            # Send final response
            await websocket.send_json({
                "type": "response",
                "text": result["response"],
                "iterations": result["iterations"]
            })

    except WebSocketDisconnect:
        # Clean up on disconnect
        if session_id in active_agents:
            del active_agents[session_id]


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file for AI processing.
    Supports: PDF, DOCX, XLSX, CSV, PNG, JPG, MP4
    """
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_id = str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "file_id": file_id,
        "filename": file.filename,
        "path": file_path,
        "size": len(content),
        "type": file.content_type
    }


@app.post("/api/run-prompt")
async def run_prompt(payload: dict):
    """
    Execute a PrimeFlow structured JSON prompt.

    Body: {
        "location_id": "...",
        "api_key": "...",
        "commands": [{"action": "create_tag", "name": "..."}, ...]
    }

    Optional query params:
        ?send_report=false   — skip email report
    """
    approval_code = payload.pop("approval_code", "")
    result = await PromptRunner.execute(
        payload, source="api", approval_code=approval_code
    )
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
    return {
        "success": result.success,
        "valid": result.is_valid,
        "run_id": result.run_id,
        "commands_count": result.commands_count,
        "summary": result.summary_text,
        "validation_errors": result.validation_errors,
        "report": report_data,
        "duration_seconds": result.duration_seconds,
    }


@app.post("/api/validate-prompt")
async def validate_prompt(payload: dict):
    """
    Validate a PrimeFlow prompt without executing (dry-run).
    Returns validation info only — no API calls are made.
    """
    result = PromptRunner.validate(payload)
    return {
        "valid": result.is_valid,
        "commands_count": result.commands_count,
        "summary": result.summary_text,
        "errors": result.validation_errors,
        "warnings": result.validation_warnings,
    }


# ---------------------------------------------------------------------------
# 2FA Approval Endpoints — Email-based approve/reject
# ---------------------------------------------------------------------------

@app.get("/api/approve-run/{pending_id}")
async def approve_run(pending_id: str):
    """
    Step 1: Show confirmation page — "Are you sure you want to APPROVE?"
    Does NOT execute yet. User must click Yes to confirm.
    """
    from fastapi.responses import HTMLResponse

    pending_info = PromptRunner.get_pending_run(pending_id)
    if not pending_info:
        return HTMLResponse(_approval_response_html(
            "❌ Run Not Found",
            f"Pending run <code>{pending_id}</code> was not found or has expired.",
            "#e53e3e"
        ))

    if pending_info["status"] != "pending":
        return HTMLResponse(_approval_response_html(
            f"ℹ️ Run Already {pending_info['status'].title()}",
            f"This run was already <strong>{pending_info['status']}</strong>.",
            "#dd6b20"
        ))

    # Show confirmation page — NOT executing yet
    return HTMLResponse(_confirmation_page_html(
        pending_id=pending_id,
        action="APPROVE",
        location_name=pending_info.get("location_name", "Unknown"),
        commands_count=pending_info.get("commands_count", 0),
        confirm_url=f"/api/confirm-approve/{pending_id}",
        cancel_text="No, go back",
        color="#38a169",
        icon="✅",
    ))


@app.get("/api/confirm-approve/{pending_id}")
async def confirm_approve_run(pending_id: str):
    """
    Step 2: Actually execute the approved run after user confirmed.
    """
    from fastapi.responses import HTMLResponse

    pending_info = PromptRunner.get_pending_run(pending_id)
    if not pending_info:
        return HTMLResponse(_approval_response_html(
            "❌ Run Not Found",
            f"Pending run <code>{pending_id}</code> was not found or has expired.",
            "#e53e3e"
        ))

    if pending_info["status"] != "pending":
        return HTMLResponse(_approval_response_html(
            f"ℹ️ Run Already {pending_info['status'].title()}",
            f"This run was already <strong>{pending_info['status']}</strong>.",
            "#dd6b20"
        ))

    result = await PromptRunner.execute_approved_run(pending_id)

    if result.get("success"):
        return HTMLResponse(_approval_response_html(
            "✅ Run Approved & Executed!",
            f"<strong>Run ID:</strong> {result.get('run_id', 'N/A')}<br>"
            f"<strong>Commands:</strong> {result.get('commands_count', 0)}<br>"
            f"<strong>Duration:</strong> {result.get('duration_seconds', 0):.1f}s<br><br>"
            f"The execution report has been sent to your email.",
            "#38a169"
        ))
    else:
        return HTMLResponse(_approval_response_html(
            "⚠️ Execution Error",
            f"Run was approved but encountered an error:<br>"
            f"<code>{result.get('error', 'Unknown error')}</code>",
            "#dd6b20"
        ))


@app.get("/api/reject-run/{pending_id}")
async def reject_run(pending_id: str):
    """
    Step 1: Show confirmation page — "Are you sure you want to DISAPPROVE?"
    Does NOT reject yet. User must click Yes to confirm.
    """
    from fastapi.responses import HTMLResponse

    pending_info = PromptRunner.get_pending_run(pending_id)
    if not pending_info:
        return HTMLResponse(_approval_response_html(
            "❌ Run Not Found",
            f"Pending run <code>{pending_id}</code> was not found or has expired.",
            "#e53e3e"
        ))

    if pending_info["status"] != "pending":
        return HTMLResponse(_approval_response_html(
            f"ℹ️ Run Already {pending_info['status'].title()}",
            f"This run was already <strong>{pending_info['status']}</strong>.",
            "#dd6b20"
        ))

    # Show confirmation page — NOT rejecting yet
    return HTMLResponse(_confirmation_page_html(
        pending_id=pending_id,
        action="DISAPPROVE",
        location_name=pending_info.get("location_name", "Unknown"),
        commands_count=pending_info.get("commands_count", 0),
        confirm_url=f"/api/confirm-reject/{pending_id}",
        cancel_text="No, go back",
        color="#e53e3e",
        icon="🚫",
    ))


@app.get("/api/confirm-reject/{pending_id}")
async def confirm_reject_run(pending_id: str):
    """
    Step 2: Actually reject the run after user confirmed.
    """
    from fastapi.responses import HTMLResponse

    pending_info = PromptRunner.get_pending_run(pending_id)
    if not pending_info:
        return HTMLResponse(_approval_response_html(
            "❌ Run Not Found",
            f"Pending run <code>{pending_id}</code> was not found or has expired.",
            "#e53e3e"
        ))

    if pending_info["status"] != "pending":
        return HTMLResponse(_approval_response_html(
            f"ℹ️ Run Already {pending_info['status'].title()}",
            f"This run was already <strong>{pending_info['status']}</strong>.",
            "#dd6b20"
        ))

    result = PromptRunner.reject_pending_run(pending_id)

    return HTMLResponse(_approval_response_html(
        "🚫 Run Disapproved",
        f"The run for <strong>{result.get('location_name', 'Unknown')}</strong> "
        f"({result.get('commands_count', 0)} commands) has been rejected.<br><br>"
        f"The prompt data has been preserved for review but will NOT be executed.",
        "#e53e3e"
    ))


@app.get("/api/pending-runs")
async def list_pending_runs():
    """List all pending runs (without sensitive data)."""
    from server.core.prompt_runner import PENDING_RUNS
    runs = []
    for pid, data in PENDING_RUNS.items():
        runs.append(PromptRunner.get_pending_run(pid))
    return {"pending_runs": [r for r in runs if r]}


def _confirmation_page_html(
    pending_id: str,
    action: str,
    location_name: str,
    commands_count: int,
    confirm_url: str,
    cancel_text: str,
    color: str,
    icon: str,
) -> str:
    """Generate an HTML confirmation page with Yes/No buttons."""
    action_lower = action.lower()
    bg_light = "#f0fff4" if action == "APPROVE" else "#fff5f5"
    border_color = "#48bb78" if action == "APPROVE" else "#fc8181"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>PrimeFlow — Confirm {action}</title></head>
<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,
     Arial,sans-serif;max-width:520px;margin:60px auto;padding:20px;
     background:#f0f2f5;color:#1a202c;'>
    <div style='background:white;padding:32px;border-radius:12px;
         box-shadow:0 4px 16px rgba(0,0,0,0.12);text-align:center;'>

        <div style='font-size:56px;margin-bottom:12px;'>{icon}</div>

        <h2 style='margin:0 0 8px;color:{color};font-size:22px;font-weight:700;'>
            Are you sure you want to {action} this run?</h2>

        <div style='background:{bg_light};border:1px solid {border_color};
             border-radius:8px;padding:16px;margin:20px 0;text-align:left;'>
            <table style='width:100%;border-collapse:collapse;font-size:14px;'>
                <tr>
                    <td style='padding:6px 0;color:#718096;width:130px;'>Sub Account:</td>
                    <td style='padding:6px 0;font-weight:600;'>{location_name}</td>
                </tr>
                <tr>
                    <td style='padding:6px 0;color:#718096;'>Pending ID:</td>
                    <td style='padding:6px 0;font-weight:600;'>
                        <code style='background:#edf2f7;padding:2px 6px;
                        border-radius:3px;font-size:12px;'>{pending_id}</code></td>
                </tr>
                <tr>
                    <td style='padding:6px 0;color:#718096;'>Total Commands:</td>
                    <td style='padding:6px 0;font-weight:600;'>{commands_count}</td>
                </tr>
            </table>
        </div>

        <p style='font-size:13px;color:#718096;margin:16px 0 24px;'>
            This action cannot be undone. Please confirm your choice.</p>

        <div style='display:flex;gap:16px;justify-content:center;'>
            <a href="{confirm_url}"
               style='display:inline-block;padding:14px 40px;background:{color};
               color:white;text-decoration:none;border-radius:8px;font-size:16px;
               font-weight:700;flex:1;text-align:center;'>
                Yes, {action}</a>
            <a href="javascript:window.close();"
               onclick="window.close(); return false;"
               style='display:inline-block;padding:14px 40px;background:#a0aec0;
               color:white;text-decoration:none;border-radius:8px;font-size:16px;
               font-weight:700;flex:1;text-align:center;'>
                {cancel_text}</a>
        </div>
    </div>

    <p style='text-align:center;font-size:11px;color:#a0aec0;margin-top:16px;'>
        PrimeFlow AI &bull; 2FA Run Approval System</p>
</body>
</html>"""


def _approval_response_html(title: str, message: str, color: str) -> str:
    """Generate a clean HTML response page for approval/rejection results."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>PrimeFlow — {title}</title></head>
<body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,
     Arial,sans-serif;max-width:500px;margin:60px auto;padding:20px;
     background:#f0f2f5;color:#1a202c;'>
    <div style='background:white;padding:32px;border-radius:12px;
         box-shadow:0 4px 12px rgba(0,0,0,0.1);text-align:center;'>
        <div style='font-size:48px;margin-bottom:16px;'>{title.split(' ')[0]}</div>
        <h2 style='margin:0 0 16px;color:{color};font-size:20px;'>
            {title}</h2>
        <p style='font-size:14px;color:#4a5568;line-height:1.6;'>
            {message}</p>
        <hr style='border:none;border-top:1px solid #e2e8f0;margin:24px 0;'>
        <p style='font-size:11px;color:#a0aec0;'>
            PrimeFlow AI &bull; 2FA Run Approval System</p>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Industry Templates — 1-click customer onboarding
# ---------------------------------------------------------------------------

@app.get("/api/industry-templates")
async def list_industry_templates():
    """List all available industry templates with metadata."""
    from server.core.industry_templates import IndustryTemplateEngine
    engine = IndustryTemplateEngine()
    return {"templates": engine.list_templates()}


@app.get("/api/industry-templates/{template_id}")
async def get_industry_template(template_id: str):
    """Get a specific industry template with full details."""
    from server.core.industry_templates import IndustryTemplateEngine
    engine = IndustryTemplateEngine()
    tmpl = engine.get_template(template_id)
    if not tmpl:
        return {"error": f"Template '{template_id}' not found."}
    return {
        "id": tmpl.id,
        "name": tmpl.name,
        "name_he": tmpl.name_he,
        "description": tmpl.description,
        "command_count": tmpl.command_count,
        "required_variables": [
            {"name": v.name, "description": v.description}
            for v in tmpl.get_required_variables()
        ],
        "optional_variables": [
            {"name": v.name, "description": v.description, "default": v.default}
            for v in tmpl.get_optional_variables()
        ],
    }


@app.post("/api/run-industry-template")
async def run_industry_template(payload: dict):
    """
    Generate commands from an industry template and execute.

    Body: {
        "location_id": "...",
        "api_key": "...",
        "template": "car_dealer",
        "variables": {
            "business_name": "...",
            "owner_name": "...",
            "owner_email": "...",
            "owner_phone": "..."
        }
    }
    """
    from server.core.industry_templates import IndustryTemplateEngine

    template_id = payload.get("template", "")
    variables = payload.get("variables", {})

    if not template_id:
        return {"success": False, "error": "Missing 'template' field."}

    # Step 1: Generate commands from template
    engine = IndustryTemplateEngine()
    gen_result = engine.generate(template_id, variables)

    if not gen_result.is_valid:
        return {
            "success": False,
            "template_id": template_id,
            "errors": gen_result.errors,
            "warnings": gen_result.warnings,
        }

    # Step 2: Build standard payload and execute
    structured_payload = {
        "location_id": payload.get("location_id", ""),
        "api_key": payload.get("api_key", ""),
        "commands": gen_result.commands,
    }

    approval_code = payload.get("approval_code", "")
    result = await PromptRunner.execute(
        structured_payload, source="industry-template", approval_code=approval_code
    )

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

    return {
        "success": result.success,
        "valid": result.is_valid,
        "run_id": result.run_id,
        "template_id": template_id,
        "template_name": gen_result.template_name,
        "commands_generated": gen_result.commands_count,
        "commands_count": result.commands_count,
        "summary": result.summary_text,
        "variables_used": gen_result.variables_used,
        "parse_warnings": gen_result.warnings,
        "validation_errors": result.validation_errors,
        "report": report_data,
        "duration_seconds": result.duration_seconds,
    }


# ---------------------------------------------------------------------------
# Multi-Location Batch Run — deploy to many locations at once
# ---------------------------------------------------------------------------

@app.post("/api/run-batch")
async def run_batch(payload: dict):
    """
    Run the same commands (or industry template) across multiple locations.

    Body: {
        "locations": [
            {"location_id": "loc1", "api_key": "pit-xxx"},
            {"location_id": "loc2", "api_key": "pit-yyy"},
        ],
        "commands": [...],
        // OR use a template:
        "template": "car_dealer",
        "variables": {"business_name": "...", ...}
    }

    Returns a combined report with per-location results.
    """
    import asyncio
    from server.core.industry_templates import IndustryTemplateEngine

    locations = payload.get("locations", [])
    if not locations or not isinstance(locations, list):
        return {"success": False, "error": "Missing or empty 'locations' list."}

    # Determine commands source
    template_id = payload.get("template", "")
    variables = payload.get("variables", {})
    commands = payload.get("commands", [])

    if template_id:
        tmpl_engine = IndustryTemplateEngine()
        gen_result = tmpl_engine.generate(template_id, variables)
        if not gen_result.is_valid:
            return {
                "success": False,
                "errors": gen_result.errors,
                "warnings": gen_result.warnings,
            }
        commands = gen_result.commands

    if not commands:
        return {"success": False, "error": "No commands provided and no valid template."}

    # Run each location sequentially (to respect rate limits)
    batch_results = []
    total_created = 0
    total_errors = 0

    for i, loc in enumerate(locations, 1):
        loc_id = loc.get("location_id", "")
        api_key = loc.get("api_key", "")

        if not loc_id or not api_key:
            batch_results.append({
                "location_id": loc_id,
                "success": False,
                "error": "Missing location_id or api_key",
            })
            continue

        print(f"\n{'='*60}")
        print(f"  BATCH [{i}/{len(locations)}] — Location: {loc_id}")
        print(f"{'='*60}")

        # Override per-location variables if provided
        loc_vars = loc.get("variables", {})
        loc_commands = commands
        if loc_vars and template_id:
            merged_vars = {**variables, **loc_vars}
            tmpl_engine = IndustryTemplateEngine()
            loc_gen = tmpl_engine.generate(template_id, merged_vars)
            if loc_gen.is_valid:
                loc_commands = loc_gen.commands

        loc_payload = {
            "location_id": loc_id,
            "api_key": api_key,
            "commands": loc_commands,
        }

        try:
            result = await PromptRunner.execute(
                loc_payload, source="batch",
                approval_code=payload.get("approval_code", ""),
                skip_approval=True,  # Batch runs are pre-approved
            )

            loc_report = {"created": 0, "updated": 0, "duplicates": 0, "errors": 0}
            loc_name = ""
            if result.orchestrator_result:
                rd = result.orchestrator_result.get("report_data")
                if rd:
                    loc_report = {
                        "created": len(rd.created),
                        "updated": len(rd.updated),
                        "duplicates": len(rd.duplicates),
                        "errors": len(rd.errors),
                    }
                    loc_name = rd.location_name

            total_created += loc_report["created"]
            total_errors += loc_report["errors"]

            batch_results.append({
                "location_id": loc_id,
                "location_name": loc_name,
                "success": result.success,
                "run_id": result.run_id,
                "report": loc_report,
            })
        except Exception as e:
            total_errors += 1
            batch_results.append({
                "location_id": loc_id,
                "success": False,
                "error": str(e),
            })

    return {
        "success": total_errors == 0,
        "batch_size": len(locations),
        "total_created": total_created,
        "total_errors": total_errors,
        "results": batch_results,
    }


# ---------------------------------------------------------------------------
# Prompt Webhook Router (external website → PrimeFlow)
# ---------------------------------------------------------------------------
app.include_router(prompt_webhook_router)


@app.post("/webhooks/ghl")
async def ghl_webhook(payload: dict):
    """
    Receive webhooks from GHL.
    These can trigger automated responses or update internal state.
    """
    event_type = payload.get("type", "unknown")
    # TODO: Route events to appropriate handlers
    return {"received": True, "event_type": event_type}


@app.post("/webhooks/generic")
async def generic_webhook(payload: dict):
    """
    Generic webhook receiver for Make.com, n8n, or any external service.
    """
    return {"received": True, "payload_keys": list(payload.keys())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server.main:app",
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("SERVER_PORT", "8000")),
        reload=True
    )
