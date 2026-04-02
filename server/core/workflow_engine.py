"""
PrimeFlow AI - Workflow Creation Engine

GHL does NOT expose workflow creation via public API.
This engine bypasses that limitation using 4 combined strategies:

STRATEGY 1: BROWSER AUTOMATION (Primary - builds ANY workflow)
    - Uses Playwright to control the GHL Workflow Builder UI
    - AI navigates the builder, adds triggers/actions, configures each node
    - Works with the GHL "Workflow AI Builder" feature (type prompt → get workflow)
    - Fallback: manually click through builder step-by-step

STRATEGY 2: SNAPSHOT CLONING (Fast - for template workflows)
    - Pre-build common workflow templates in a "master" sub-account
    - Use Snapshot API to package and push to target sub-accounts
    - Then use browser automation to customize cloned workflows

STRATEGY 3: INTERNAL API INTERCEPTION (Advanced - direct creation)
    - Capture the internal API calls GHL makes when YOU build a workflow
    - Replay those calls programmatically to create workflows without the UI
    - Requires session auth from browser, not public API key

STRATEGY 4: MARKETPLACE CUSTOM ACTIONS/TRIGGERS (Extend workflows)
    - Register custom actions/triggers in the GHL Marketplace
    - These become available as workflow nodes that call YOUR backend
    - Gives your AI a "hook" inside every workflow

All strategies can be combined. Example flow:
    1. User says: "Build me a lead follow-up workflow"
    2. AI checks if a snapshot template exists → clone it (Strategy 2)
    3. If not, AI checks if internal API structure is known → create directly (Strategy 3)
    4. If not, AI opens browser → uses GHL Workflow AI Builder (Strategy 1)
    5. AI adds custom actions that call back to PrimeFlow (Strategy 4)
    6. AI verifies the workflow was created correctly
"""

import json
import os
from typing import Any


# ============================================================================
# WORKFLOW KNOWLEDGE BASE
# All GHL workflow triggers and actions with their configuration schemas
# ============================================================================

WORKFLOW_TRIGGERS = {
    # --- Contact Triggers ---
    "birthday_reminder": {
        "category": "Contact",
        "name": "Birthday Reminder",
        "config": {"daysBeforeBirthday": "int"},
    },
    "contact_changed": {
        "category": "Contact",
        "name": "Contact Changed",
        "config": {"field": "string", "previousValue": "any", "newValue": "any"},
    },
    "contact_created": {
        "category": "Contact",
        "name": "Contact Created",
        "config": {"filters": "object"},
    },
    "contact_dnd": {
        "category": "Contact",
        "name": "Contact DND",
        "config": {"status": "enabled|disabled"},
    },
    "contact_tag": {
        "category": "Contact",
        "name": "Contact Tag",
        "config": {"tag": "string", "action": "added|removed"},
    },
    "custom_date_reminder": {
        "category": "Contact",
        "name": "Custom Date Reminder",
        "config": {"customFieldId": "string", "daysBefore": "int"},
    },
    "note_added": {"category": "Contact", "name": "Note Added", "config": {}},
    "note_changed": {"category": "Contact", "name": "Note Changed", "config": {}},
    "task_added": {"category": "Contact", "name": "Task Added", "config": {}},
    "task_reminder": {"category": "Contact", "name": "Task Reminder", "config": {}},
    "task_completed": {"category": "Contact", "name": "Task Completed", "config": {}},
    "contact_engagement_score": {
        "category": "Contact",
        "name": "Contact Engagement Score",
        "config": {"threshold": "int", "direction": "above|below"},
    },

    # --- Event Triggers ---
    "inbound_webhook": {
        "category": "Events",
        "name": "Inbound Webhook",
        "config": {},
        "note": "Generates a unique webhook URL that external systems can POST to",
    },
    "scheduler": {
        "category": "Events",
        "name": "Scheduler",
        "config": {"schedule": "cron_expression"},
    },
    "call_details": {"category": "Events", "name": "Call Details", "config": {}},
    "email_events": {
        "category": "Events",
        "name": "Email Events",
        "config": {"event": "opened|clicked|bounced|complained|unsubscribed"},
    },
    "customer_replied": {
        "category": "Events",
        "name": "Customer Replied",
        "config": {"channel": "sms|email|facebook|instagram|whatsapp|live_chat"},
    },
    "conversation_ai_trigger": {
        "category": "Events",
        "name": "Conversation AI Trigger",
        "config": {},
    },
    "form_submitted": {
        "category": "Events",
        "name": "Form Submitted",
        "config": {"formId": "string"},
    },
    "survey_submitted": {
        "category": "Events",
        "name": "Survey Submitted",
        "config": {"surveyId": "string"},
    },
    "trigger_link_clicked": {
        "category": "Events",
        "name": "Trigger Link Clicked",
        "config": {"linkId": "string"},
    },
    "facebook_lead_form": {
        "category": "Events",
        "name": "Facebook Lead Form Submitted",
        "config": {"formId": "string"},
    },
    "tiktok_form": {
        "category": "Events",
        "name": "TikTok Form Submitted",
        "config": {},
    },
    "funnel_pageview": {
        "category": "Events",
        "name": "Funnel/Website PageView",
        "config": {"funnelId": "string", "pageId": "string"},
    },
    "new_review_received": {
        "category": "Events",
        "name": "New Review Received",
        "config": {},
    },
    "linkedin_lead_form": {
        "category": "Events",
        "name": "LinkedIn Lead Form Submitted",
        "config": {},
    },

    # --- Appointment Triggers ---
    "appointment_status": {
        "category": "Appointments",
        "name": "Appointment Status",
        "config": {"status": "booked|confirmed|showed|noshow|cancelled|rescheduled"},
    },
    "customer_booked_appointment": {
        "category": "Appointments",
        "name": "Customer Booked Appointment",
        "config": {"calendarId": "string"},
    },

    # --- Opportunity Triggers ---
    "opportunity_status_changed": {
        "category": "Opportunities",
        "name": "Opportunity Status Changed",
        "config": {"status": "open|won|lost|abandoned"},
    },
    "opportunity_created": {
        "category": "Opportunities",
        "name": "Opportunity Created",
        "config": {"pipelineId": "string"},
    },
    "pipeline_stage_changed": {
        "category": "Opportunities",
        "name": "Pipeline Stage Changed",
        "config": {"pipelineId": "string", "stageId": "string"},
    },
    "stale_opportunities": {
        "category": "Opportunities",
        "name": "Stale Opportunities",
        "config": {"daysStale": "int", "pipelineId": "string"},
    },

    # --- Payment Triggers ---
    "invoice_trigger": {
        "category": "Payments",
        "name": "Invoice",
        "config": {"event": "created|paid|partially_paid|sent|voided"},
    },
    "payment_received": {
        "category": "Payments",
        "name": "Payment Received",
        "config": {},
    },
    "order_form_submission": {
        "category": "Payments",
        "name": "Order Form Submission",
        "config": {},
    },
    "subscription_trigger": {
        "category": "Payments",
        "name": "Subscription",
        "config": {"event": "created|cancelled|expired|renewed"},
    },

    # --- Course Triggers ---
    "course_lesson_completed": {
        "category": "Courses",
        "name": "Lesson Completed",
        "config": {"courseId": "string"},
    },
    "course_new_signup": {
        "category": "Courses",
        "name": "New Signup",
        "config": {},
    },

    # --- Community Triggers ---
    "group_access_granted": {
        "category": "Communities",
        "name": "Group Access Granted",
        "config": {"groupId": "string"},
    },
    "group_access_revoked": {
        "category": "Communities",
        "name": "Group Access Revoked",
        "config": {"groupId": "string"},
    },

    # --- Social Triggers ---
    "facebook_comment": {
        "category": "Facebook",
        "name": "Facebook – Comment(s) On A Post",
        "config": {"postId": "string"},
    },
    "instagram_comment": {
        "category": "Instagram",
        "name": "Instagram – Comment(s) On A Post",
        "config": {"postId": "string"},
    },
}


WORKFLOW_ACTIONS = {
    # --- Contact Actions ---
    "create_contact": {
        "category": "Contact",
        "name": "Create Contact",
        "config": {"firstName": "string", "lastName": "string", "email": "string",
                   "phone": "string", "tags": "list", "customFields": "object"},
    },
    "find_contact": {
        "category": "Contact",
        "name": "Find Contact",
        "config": {"searchBy": "email|phone|id", "value": "string"},
    },
    "update_contact_field": {
        "category": "Contact",
        "name": "Update Contact Field",
        "config": {"field": "string", "value": "any"},
    },
    "add_tag": {
        "category": "Contact",
        "name": "Add Contact Tag",
        "config": {"tag": "string"},
    },
    "remove_tag": {
        "category": "Contact",
        "name": "Remove Contact Tag",
        "config": {"tag": "string"},
    },
    "assign_to_user": {
        "category": "Contact",
        "name": "Assign to User",
        "config": {"userId": "string"},
    },
    "add_note": {
        "category": "Contact",
        "name": "Add Note",
        "config": {"body": "string"},
    },
    "add_task": {
        "category": "Contact",
        "name": "Add Task",
        "config": {"title": "string", "dueDate": "string", "assignedTo": "string"},
    },
    "delete_contact": {
        "category": "Contact",
        "name": "Delete Contact",
        "config": {},
    },

    # --- Communication Actions ---
    "send_email": {
        "category": "Communication",
        "name": "Send Email",
        "config": {"subject": "string", "body": "html", "from": "string",
                   "templateId": "string"},
    },
    "send_sms": {
        "category": "Communication",
        "name": "Send SMS",
        "config": {"message": "string"},
    },
    "send_whatsapp": {
        "category": "Communication",
        "name": "WhatsApp",
        "config": {"message": "string", "templateId": "string"},
    },
    "send_slack": {
        "category": "Communication",
        "name": "Send Slack Message",
        "config": {"channel": "string", "message": "string"},
    },
    "call": {
        "category": "Communication",
        "name": "Call",
        "config": {"fromNumber": "string"},
    },
    "instagram_dm": {
        "category": "Communication",
        "name": "Instagram DM",
        "config": {"message": "string"},
    },
    "send_internal_notification": {
        "category": "Communication",
        "name": "Send Internal Notification",
        "config": {"userId": "string", "message": "string"},
    },
    "send_review_request": {
        "category": "Communication",
        "name": "Send Review Request",
        "config": {"channel": "sms|email"},
    },
    "conversation_ai": {
        "category": "Communication",
        "name": "Conversation AI",
        "config": {},
    },
    "reply_in_comments": {
        "category": "Communication",
        "name": "Reply in Comments",
        "config": {"message": "string"},
    },

    # --- Logic / Internal Tools ---
    "if_else": {
        "category": "Internal Tools",
        "name": "If Else",
        "config": {"conditions": "list[condition]"},
        "note": "Branch logic: evaluate conditions and route to different paths",
    },
    "wait": {
        "category": "Internal Tools",
        "name": "Wait Step",
        "config": {"waitType": "delay|specific_time|event",
                   "delayValue": "int", "delayUnit": "minutes|hours|days"},
    },
    "goal_event": {
        "category": "Internal Tools",
        "name": "Goal Event",
        "config": {"goalType": "string"},
    },
    "split": {
        "category": "Internal Tools",
        "name": "Split",
        "config": {"distribution": "list[percentage]"},
        "note": "A/B split testing",
    },
    "update_custom_value": {
        "category": "Internal Tools",
        "name": "Update Custom Value",
        "config": {"customValueId": "string", "value": "string"},
    },
    "go_to": {
        "category": "Internal Tools",
        "name": "Go To",
        "config": {"targetActionId": "string"},
    },
    "remove_from_workflow": {
        "category": "Internal Tools",
        "name": "Remove from Workflow",
        "config": {"workflowId": "string"},
    },
    "custom_code": {
        "category": "Internal Tools",
        "name": "Custom Code",
        "config": {"code": "string", "language": "javascript"},
        "note": "Execute custom JavaScript code with access to InputData",
    },
    "text_formatter": {
        "category": "Internal Tools",
        "name": "Text Formatter",
        "config": {"action": "string", "input": "string"},
    },
    "drip_mode": {
        "category": "Internal Tools",
        "name": "Drip Mode",
        "config": {"batchSize": "int", "interval": "string"},
    },

    # --- Data / External ---
    "webhook": {
        "category": "Send Data",
        "name": "Webhook/Custom Webhook",
        "config": {"url": "string", "method": "GET|POST|PUT|DELETE",
                   "headers": "object", "body": "object"},
    },
    "google_sheets": {
        "category": "Send Data",
        "name": "Google Sheets",
        "config": {"action": "insert_row|update_row|lookup",
                   "spreadsheetId": "string", "sheetName": "string"},
    },

    # --- AI ---
    "ai_prompt": {
        "category": "Workflow AI",
        "name": "AI Prompt",
        "config": {"prompt": "string", "model": "string", "outputVariable": "string"},
    },

    # --- Opportunity Actions ---
    "create_opportunity": {
        "category": "Opportunities",
        "name": "Create/Update Opportunity",
        "config": {"pipelineId": "string", "stageId": "string", "name": "string",
                   "monetaryValue": "number", "status": "open|won|lost|abandoned"},
    },
    "remove_opportunity": {
        "category": "Opportunities",
        "name": "Remove Opportunity",
        "config": {"opportunityId": "string"},
    },

    # --- Appointment Actions ---
    "update_appointment_status": {
        "category": "Appointments",
        "name": "Update Appointment Status",
        "config": {"status": "confirmed|showed|noshow|cancelled"},
    },
    "generate_booking_link": {
        "category": "Appointments",
        "name": "Generate One Time Booking Link",
        "config": {"calendarId": "string"},
    },

    # --- Payment Actions ---
    "stripe_charge": {
        "category": "Payments",
        "name": "Stripe One-Time Charge",
        "config": {"amount": "number", "currency": "string", "description": "string"},
    },
    "send_invoice": {
        "category": "Payments",
        "name": "Send Invoice",
        "config": {"templateId": "string"},
    },

    # --- Marketing Actions ---
    "facebook_custom_audience_add": {
        "category": "Marketing",
        "name": "Add to Custom Audience (Facebook)",
        "config": {"audienceId": "string"},
    },
    "facebook_custom_audience_remove": {
        "category": "Marketing",
        "name": "Remove from Custom Audience (Facebook)",
        "config": {"audienceId": "string"},
    },
    "facebook_conversion_api": {
        "category": "Marketing",
        "name": "Facebook Conversion API",
        "config": {"eventName": "string", "eventValue": "number"},
    },

    # --- Course Actions ---
    "course_grant_offer": {
        "category": "Courses",
        "name": "Course Grant Offer",
        "config": {"offerId": "string"},
    },
    "course_revoke_offer": {
        "category": "Courses",
        "name": "Course Revoke Offer",
        "config": {"offerId": "string"},
    },

    # --- Community Actions ---
    "grant_group_access": {
        "category": "Communities",
        "name": "Grant Group Access",
        "config": {"groupId": "string"},
    },
    "revoke_group_access": {
        "category": "Communities",
        "name": "Revoke Group Access",
        "config": {"groupId": "string"},
    },
}


# ============================================================================
# WORKFLOW TEMPLATES (Pre-built patterns for common funnels)
# ============================================================================

WORKFLOW_TEMPLATES = {
    "lead_followup": {
        "name": "Lead Follow-Up Sequence",
        "description": "Triggered when form submitted. Sends welcome email, waits 5 min, sends SMS, waits 1 day, sends follow-up email.",
        "trigger": "form_submitted",
        "actions": [
            {"type": "send_email", "config": {"subject": "!subject", "body": "!body"}},
            {"type": "wait", "config": {"delayValue": 5, "delayUnit": "minutes"}},
            {"type": "send_sms", "config": {"message": "!message"}},
            {"type": "add_tag", "config": {"tag": "lead-followup"}},
            {"type": "wait", "config": {"delayValue": 1, "delayUnit": "days"}},
            {"type": "send_email", "config": {"subject": "!subject2", "body": "!body2"}},
            {"type": "create_opportunity", "config": {
                "pipelineId": "!pipelineId", "stageId": "!stageId",
                "name": "!name", "status": "open"
            }},
        ],
    },

    "appointment_reminder": {
        "name": "Appointment Reminder Sequence",
        "description": "Sends reminders before appointment: 24h email, 1h SMS, 15min SMS.",
        "trigger": "customer_booked_appointment",
        "actions": [
            {"type": "send_email", "config": {"subject": "!subject", "body": "!body"}},
            {"type": "add_tag", "config": {"tag": "appointment-booked"}},
            {"type": "wait", "config": {"waitType": "specific_time",
                                         "beforeEvent": "24h"}},
            {"type": "send_email", "config": {"subject": "!reminder_subject",
                                               "body": "!reminder_body"}},
            {"type": "wait", "config": {"waitType": "specific_time",
                                         "beforeEvent": "1h"}},
            {"type": "send_sms", "config": {"message": "!sms_reminder"}},
            {"type": "wait", "config": {"waitType": "specific_time",
                                         "beforeEvent": "15min"}},
            {"type": "send_sms", "config": {"message": "!sms_final_reminder"}},
        ],
    },

    "new_customer_onboarding": {
        "name": "New Customer Onboarding",
        "description": "Payment received → welcome email → task for team → wait 3 days → check-in email.",
        "trigger": "payment_received",
        "actions": [
            {"type": "send_email", "config": {"subject": "!welcome_subject",
                                               "body": "!welcome_body"}},
            {"type": "send_internal_notification", "config": {
                "message": "!internal_message"}},
            {"type": "add_tag", "config": {"tag": "customer"}},
            {"type": "create_opportunity", "config": {
                "pipelineId": "!pipelineId", "stageId": "!stageId",
                "name": "!name", "status": "open",
            }},
            {"type": "wait", "config": {"delayValue": 3, "delayUnit": "days"}},
            {"type": "send_email", "config": {"subject": "!checkin_subject",
                                               "body": "!checkin_body"}},
        ],
    },

    "stale_lead_reengagement": {
        "name": "Stale Lead Re-engagement",
        "description": "Triggered when opportunity is stale for 7 days. Sends re-engagement sequence.",
        "trigger": "stale_opportunities",
        "trigger_config": {"daysStale": 7},
        "actions": [
            {"type": "send_email", "config": {"subject": "!subject", "body": "!body"}},
            {"type": "wait", "config": {"delayValue": 2, "delayUnit": "days"}},
            {"type": "send_sms", "config": {"message": "!message"}},
            {"type": "wait", "config": {"delayValue": 3, "delayUnit": "days"}},
            {"type": "if_else", "config": {"conditions": [
                {"field": "contact.lastActivity", "operator": "olderThan",
                 "value": "12days"}
            ]}},
            {"type": "send_email", "config": {"subject": "!final_subject",
                                               "body": "!final_body"}},
        ],
    },

    "review_request": {
        "name": "Review Request After Service",
        "description": "Appointment showed → wait 2 hours → send review request → follow up if no review.",
        "trigger": "appointment_status",
        "trigger_config": {"status": "showed"},
        "actions": [
            {"type": "wait", "config": {"delayValue": 2, "delayUnit": "hours"}},
            {"type": "send_review_request", "config": {"channel": "sms"}},
            {"type": "wait", "config": {"delayValue": 3, "delayUnit": "days"}},
            {"type": "send_review_request", "config": {"channel": "email"}},
        ],
    },

    "webinar_registration": {
        "name": "Webinar Registration Funnel",
        "description": "Form submit → confirmation email → reminder 24h before → reminder 1h before → follow-up after.",
        "trigger": "form_submitted",
        "actions": [
            {"type": "send_email", "config": {"subject": "!confirm_subject",
                                               "body": "!confirm_body"}},
            {"type": "add_tag", "config": {"tag": "webinar-registered"}},
            {"type": "create_opportunity", "config": {
                "pipelineId": "!pipelineId", "stageId": "registered",
                "name": "!contact_name", "status": "open",
            }},
            {"type": "wait", "config": {"waitType": "specific_time",
                                         "beforeEvent": "24h"}},
            {"type": "send_email", "config": {"subject": "!reminder_subject",
                                               "body": "!reminder_body"}},
            {"type": "wait", "config": {"waitType": "specific_time",
                                         "beforeEvent": "1h"}},
            {"type": "send_sms", "config": {"message": "!sms_reminder"}},
            {"type": "wait", "config": {"delayValue": 1, "delayUnit": "days"}},
            {"type": "send_email", "config": {"subject": "!followup_subject",
                                               "body": "!followup_body"}},
        ],
    },
}


# ============================================================================
# WORKFLOW BUILDER ENGINE
# ============================================================================

class WorkflowBuilder:
    """
    Creates GHL workflows using 4 combined strategies.
    Priority: Internal API → Snapshot Clone → GHL AI Builder → Manual Browser
    """

    def __init__(self, ghl_client, browser_engine=None):
        self.ghl = ghl_client
        self.browser = browser_engine
        self.internal_api_available = False
        self._intercepted_endpoints: dict[str, Any] = {}

    # ========================================================================
    # STRATEGY 1: BROWSER AUTOMATION (Always works)
    # ========================================================================

    async def build_via_browser(self, workflow_spec: dict) -> dict:
        """
        Build a workflow by controlling the GHL UI via Playwright.

        Sub-strategy A: Use GHL's built-in "Workflow AI Builder"
          - Navigate to Workflows page
          - Click "Build using AI"
          - Type the natural language prompt
          - Let GHL's AI build the workflow
          - Review and publish

        Sub-strategy B: Manual step-by-step builder
          - Navigate to Workflows → Create New
          - Add trigger (click through UI)
          - Add each action node one by one
          - Configure each node's settings
          - Save and publish
        """
        if not self.browser:
            return {"success": False, "error": "Browser engine not initialized"}

        workflow_name = workflow_spec.get("name", "AI-Built Workflow")
        use_ai_builder = workflow_spec.get("use_ai_builder", True)

        if use_ai_builder:
            return await self._build_with_ghl_ai_builder(workflow_spec)
        else:
            return await self._build_manually_via_browser(workflow_spec)

    async def _build_with_ghl_ai_builder(self, spec: dict) -> dict:
        """
        Use GHL's native Workflow AI Builder feature.
        This is the fastest browser-based approach.

        Steps:
        1. Navigate to /workflows
        2. Click "Build using AI" button
        3. Enter the natural language description
        4. Click "Build Workflow"
        5. Wait for AI to generate (~30 seconds)
        6. Review the generated workflow
        7. Make adjustments if needed
        8. Publish
        """
        steps = [
            {
                "action": "navigate",
                "url": f"https://app.gohighlevel.com/v2/location/"
                       f"{self.ghl.location_id}/workflows",
                "description": "Navigate to Workflows page",
            },
            {
                "action": "click",
                "selector": '[data-testid="ai-workflow-builder"],'
                            'button:has-text("Build using AI"),'
                            '.workflow-ai-builder-btn',
                "description": "Click 'Build using AI' button",
            },
            {
                "action": "type",
                "selector": 'textarea[placeholder*="Describe"],'
                            '.ai-prompt-input,'
                            'textarea.workflow-ai-prompt',
                "text": spec.get("ai_prompt", spec.get("description", "")),
                "description": "Type workflow description prompt",
            },
            {
                "action": "click",
                "selector": 'button:has-text("Build Workflow"),'
                            'button:has-text("Generate"),'
                            '.build-workflow-btn',
                "description": "Click Build Workflow",
            },
            {
                "action": "wait",
                "duration": 35000,
                "description": "Wait for AI to generate workflow (~30s)",
            },
            {
                "action": "screenshot",
                "description": "Capture generated workflow for verification",
            },
            {
                "action": "click",
                "selector": 'button:has-text("Publish"),'
                            'button:has-text("Save"),'
                            '.publish-workflow-btn',
                "description": "Publish the workflow",
            },
        ]

        return {
            "strategy": "ghl_ai_builder",
            "steps": steps,
            "spec": spec,
            "status": "ready_for_execution",
        }

    async def _build_manually_via_browser(self, spec: dict) -> dict:
        """
        Build workflow step by step through the GHL UI.
        Used when AI builder isn't suitable or for precise control.

        Steps:
        1. Create new workflow
        2. Name it
        3. Add trigger
        4. Configure trigger
        5. For each action: add node → select type → configure
        6. Connect nodes
        7. Save and publish
        """
        trigger_key = spec.get("trigger", "")
        trigger_info = WORKFLOW_TRIGGERS.get(trigger_key, {})
        actions = spec.get("actions", [])

        steps = [
            # Step 1: Navigate and create
            {
                "action": "navigate",
                "url": f"https://app.gohighlevel.com/v2/location/"
                       f"{self.ghl.location_id}/workflows",
            },
            {
                "action": "click",
                "selector": 'button:has-text("Create Workflow"),'
                            'button:has-text("New Workflow"),'
                            '[data-testid="create-workflow"]',
            },
            {
                "action": "click",
                "selector": 'button:has-text("Start from Scratch"),'
                            '.from-scratch-option',
            },
            # Step 2: Name the workflow
            {
                "action": "click",
                "selector": '.workflow-name, [contenteditable="true"],'
                            'input[placeholder*="workflow name"]',
            },
            {
                "action": "type",
                "text": spec.get("name", "AI-Built Workflow"),
            },
            # Step 3: Add trigger
            {
                "action": "click",
                "selector": 'button:has-text("Add New Trigger"),'
                            '.add-trigger-btn',
            },
            {
                "action": "click",
                "selector": f'[data-trigger="{trigger_key}"],'
                            f'span:has-text("{trigger_info.get("name", "")}")',
                "description": f"Select trigger: {trigger_info.get('name', trigger_key)}",
            },
        ]

        # Step 4: Add each action
        for i, action_spec in enumerate(actions):
            action_key = action_spec.get("type", "")
            action_info = WORKFLOW_ACTIONS.get(action_key, {})

            steps.append({
                "action": "click",
                "selector": '.add-action-btn, button:has-text("+")',
                "description": f"Add action {i + 1}",
            })
            steps.append({
                "action": "click",
                "selector": f'[data-action="{action_key}"],'
                            f'span:has-text("{action_info.get("name", "")}")',
                "description": f"Select action: {action_info.get('name', action_key)}",
            })

            # Configure the action's fields
            for field, value in action_spec.get("config", {}).items():
                if isinstance(value, str) and value.startswith("!"):
                    # Placeholder — needs user input
                    continue
                steps.append({
                    "action": "fill_field",
                    "field": field,
                    "value": value,
                    "description": f"Set {field} = {value}",
                })

        # Step 5: Save
        steps.append({
            "action": "click",
            "selector": 'button:has-text("Save"), .save-workflow-btn',
        })
        steps.append({
            "action": "screenshot",
            "description": "Verify workflow was created",
        })

        return {
            "strategy": "manual_browser",
            "steps": steps,
            "spec": spec,
            "status": "ready_for_execution",
        }

    # ========================================================================
    # STRATEGY 2: SNAPSHOT CLONING
    # ========================================================================

    async def build_via_snapshot(self, template_name: str,
                                 target_location_id: str,
                                 customizations: dict | None = None) -> dict:
        """
        Clone a pre-built workflow from a master sub-account via snapshot.

        Prerequisites:
        - Master sub-account with pre-built workflow templates
        - Snapshot created from master containing the workflows
        - Agency-level API access

        Steps:
        1. Find the snapshot containing the workflow template
        2. Push snapshot to target sub-account
        3. Wait for push to complete
        4. Use browser automation to rename/customize the cloned workflow
        """
        # Step 1: Find snapshot
        # (requires company_id — should be in env)
        company_id = os.getenv("GHL_COMPANY_ID", "")

        result = await self.ghl.get_snapshots(company_id)
        if not result.get("success"):
            return {"success": False, "error": "Could not fetch snapshots",
                    "details": result}

        snapshots = result.get("data", {}).get("snapshots", [])
        target_snapshot = None
        for snap in snapshots:
            if template_name.lower() in snap.get("name", "").lower():
                target_snapshot = snap
                break

        if not target_snapshot:
            return {"success": False,
                    "error": f"No snapshot found matching '{template_name}'",
                    "available": [s.get("name") for s in snapshots]}

        # Step 2: Create share link and push
        share_result = await self.ghl.create_snapshot_share_link(
            company_id,
            {"snapshotId": target_snapshot["id"],
             "locationId": target_location_id,
             "shareType": "link"}
        )

        return {
            "strategy": "snapshot_clone",
            "snapshot": target_snapshot,
            "share_result": share_result,
            "customizations": customizations,
            "next_step": "Use browser automation to customize cloned workflow",
        }

    # ========================================================================
    # STRATEGY 3: INTERNAL API INTERCEPTION
    # ========================================================================

    async def intercept_workflow_api(self) -> dict:
        """
        Capture the internal API calls that GHL makes when a user
        creates a workflow through the UI.

        How it works:
        1. Open GHL workflow builder in Playwright
        2. Enable network request interception
        3. Create a simple test workflow manually
        4. Capture all API calls made during creation
        5. Store the endpoint patterns and payloads
        6. Use these to create workflows directly via HTTP

        The captured endpoints typically look like:
        - POST /workflows/create (or similar internal path)
        - PUT /workflows/{id}/nodes
        - POST /workflows/{id}/actions
        - PUT /workflows/{id}/triggers

        IMPORTANT: These are INTERNAL APIs that can change without notice.
        Always fall back to browser automation if they break.
        """
        if not self.browser:
            return {"success": False, "error": "Browser engine needed for interception"}

        interception_steps = [
            {
                "action": "enable_network_capture",
                "filter": "**/workflows/**",
                "description": "Start capturing all workflow-related API calls",
            },
            {
                "action": "navigate",
                "url": f"https://app.gohighlevel.com/v2/location/"
                       f"{self.ghl.location_id}/workflows",
            },
            {
                "action": "perform_manual_workflow_creation",
                "description": "Create a test workflow to capture API calls",
            },
            {
                "action": "extract_captured_requests",
                "description": "Extract and store all intercepted API endpoints and payloads",
            },
        ]

        return {
            "strategy": "internal_api_interception",
            "steps": interception_steps,
            "status": "ready_for_execution",
            "note": "Run this once to learn the internal API structure. "
                    "Then use replay_internal_api() for subsequent creations.",
        }

    async def replay_internal_api(self, workflow_spec: dict,
                                   session_token: str) -> dict:
        """
        Replay captured internal API calls to create a workflow without UI.

        Requires:
        - Previously captured endpoint patterns (from intercept_workflow_api)
        - A valid session token (from browser login)

        This is the FASTEST method but most fragile.
        """
        if not self._intercepted_endpoints:
            return {
                "success": False,
                "error": "No intercepted endpoints available. "
                         "Run intercept_workflow_api() first.",
            }

        # Use the captured endpoint patterns to create workflow
        # The actual implementation depends on what we capture
        return {
            "strategy": "internal_api_replay",
            "spec": workflow_spec,
            "status": "requires_intercepted_endpoints",
        }

    # ========================================================================
    # STRATEGY 4: MARKETPLACE CUSTOM ACTIONS/TRIGGERS
    # ========================================================================

    async def register_custom_trigger(self, trigger_config: dict) -> dict:
        """
        Register a custom workflow trigger in the GHL Marketplace.
        This creates a trigger node that appears in the workflow builder,
        which calls YOUR backend when activated.

        Once registered, ANY workflow can use this trigger.
        Your AI can then fire the trigger via API to start workflows.
        """
        return {
            "strategy": "marketplace_custom_trigger",
            "config": trigger_config,
            "status": "requires_marketplace_app_registration",
            "docs": "https://marketplace.gohighlevel.com/docs/marketplace-modules/CustomTriggers/",
        }

    async def register_custom_action(self, action_config: dict) -> dict:
        """
        Register a custom workflow action in the GHL Marketplace.
        This creates an action node that appears in the workflow builder,
        which calls YOUR backend when the workflow reaches this step.

        This is how PrimeFlow AI gets a "hook" inside every workflow.
        When the workflow reaches the PrimeFlow action, it calls your
        backend, which can do ANYTHING — make API calls, process data,
        trigger other workflows, etc.
        """
        return {
            "strategy": "marketplace_custom_action",
            "config": action_config,
            "status": "requires_marketplace_app_registration",
            "docs": "https://marketplace.gohighlevel.com/docs/marketplace-modules/CustomActions/",
        }

    # ========================================================================
    # ORCHESTRATOR — Smart routing between strategies
    # ========================================================================

    async def build_workflow(self, request: dict) -> dict:
        """
        Main entry point. Takes a workflow request and routes to the
        best strategy automatically.

        Args:
            request: {
                "name": "My Workflow",
                "description": "Natural language description of what the workflow does",
                "trigger": "form_submitted",  # trigger key from WORKFLOW_TRIGGERS
                "trigger_config": {...},
                "actions": [...],  # list of action specs from WORKFLOW_ACTIONS
                "template": "lead_followup",  # optional: use a pre-built template
                "strategy": "auto",  # auto, browser, snapshot, internal_api
            }

        Returns execution plan or result.
        """
        strategy = request.get("strategy", "auto")
        template_name = request.get("template")

        # If a template is specified, use it as the base
        if template_name and template_name in WORKFLOW_TEMPLATES:
            template = WORKFLOW_TEMPLATES[template_name].copy()
            # Merge user overrides into template
            template.update({k: v for k, v in request.items() if v and k != "template"})
            request = template

        # Auto-select best strategy
        if strategy == "auto":
            # Priority 1: Internal API (fastest, if available)
            if self._intercepted_endpoints:
                return await self.replay_internal_api(
                    request, session_token="from_browser")

            # Priority 2: Snapshot clone (if template exists)
            if template_name:
                try:
                    result = await self.build_via_snapshot(
                        template_name, self.ghl.location_id)
                    if result.get("success") is not False:
                        return result
                except Exception:
                    pass  # Fall through to browser

            # Priority 3: GHL AI Builder (good for complex workflows)
            if request.get("description") and len(request.get("actions", [])) > 3:
                return await self.build_via_browser({
                    **request,
                    "use_ai_builder": True,
                    "ai_prompt": request["description"],
                })

            # Priority 4: Manual browser build (always works)
            return await self.build_via_browser({
                **request,
                "use_ai_builder": False,
            })

        elif strategy == "browser":
            return await self.build_via_browser(request)
        elif strategy == "snapshot":
            return await self.build_via_snapshot(
                request.get("name", ""), self.ghl.location_id)
        elif strategy == "internal_api":
            return await self.replay_internal_api(request, session_token="from_browser")
        else:
            return {"success": False, "error": f"Unknown strategy: {strategy}"}

    def get_available_triggers(self) -> dict:
        """Return all available workflow triggers."""
        return WORKFLOW_TRIGGERS

    def get_available_actions(self) -> dict:
        """Return all available workflow actions."""
        return WORKFLOW_ACTIONS

    def get_templates(self) -> dict:
        """Return all pre-built workflow templates."""
        return WORKFLOW_TEMPLATES

    def describe_workflow(self, spec: dict) -> str:
        """Generate a human-readable description of a workflow spec."""
        trigger = WORKFLOW_TRIGGERS.get(spec.get("trigger", ""), {})
        actions = spec.get("actions", [])

        lines = [
            f"Workflow: {spec.get('name', 'Unnamed')}",
            f"Trigger: {trigger.get('name', spec.get('trigger', 'Unknown'))}",
            f"Actions ({len(actions)}):",
        ]
        for i, action in enumerate(actions, 1):
            action_info = WORKFLOW_ACTIONS.get(action.get("type", ""), {})
            lines.append(f"  {i}. {action_info.get('name', action.get('type', 'Unknown'))}")

        return "\n".join(lines)
