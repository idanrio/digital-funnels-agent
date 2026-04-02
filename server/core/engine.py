from __future__ import annotations

"""
PrimeFlow Engine - Code-Based Funnel & Automation Builder

NO AI. Pure code logic. Deterministic. Fast.

How it works:
    1. You write a command (dict or JSON)
    2. The engine parses it into a sequence of API calls
    3. Each API call runs in order against your GHL account
    4. Results are collected and returned

Commands are simple dicts:
    {
        "action": "create_funnel",
        "name": "Real Estate Lead Gen",
        "language": "he",
        "contacts": [...],
        "tags": [...],
        "pipeline": {...},
        "custom_fields": [...],
        "workflow_template": "lead_followup",
        "email_templates": [...],
    }

The engine knows WHAT to call and IN WHAT ORDER.
No guessing. No AI tokens. Just code.
"""

import asyncio
import json
import os
import sys
from typing import Any
from datetime import datetime

# Add parent to path so we can import from server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from server.integrations.ghl import GHLClient


# ===========================================================================
# INPUT VALIDATION SCHEMAS
# ===========================================================================

REQUIRED_FIELDS = {
    # Contacts
    "create_contact": ["first_name|firstName"],
    "update_contact": ["contact_id|email"],
    "delete_contact": ["contact_id"],
    "upsert_contact": ["email|phone"],
    "get_contact": ["contact_id"],
    "add_contact_tags": ["contact_id", "tags"],
    "remove_contact_tags": ["contact_id", "tags"],
    # Users
    "create_user": ["first_name|firstName", "last_name|lastName", "email"],
    "update_user": ["user_id|email"],
    "delete_user": ["user_id"],
    # Tags
    "create_tag": ["name"],
    "delete_tag": ["tag_id"],
    # Custom Fields & Values
    "create_custom_field": ["name", "data_type|dataType"],
    "delete_custom_field": ["field_id"],
    "create_custom_value": ["name", "value"],
    "update_custom_value": ["value_id|name"],
    # Opportunities
    "create_opportunity": ["pipeline_id|pipelineId", "name"],
    "update_opportunity": ["opportunity_id|current_name"],
    "delete_opportunity": ["opportunity_id"],
    "update_opportunity_status": ["opportunity_id", "status"],
    # Templates
    "create_template": ["name"],
    "delete_email_template": ["template_id"],
    # Calendars
    "create_calendar": ["name"],
    "create_calendar_notification": ["channel", "notificationType"],
    "update_calendar": ["calendar_id|current_name"],
    "delete_calendar": ["calendar_id"],
    "create_appointment": ["calendar_id|calendarId", "start_time|startTime",
                            "end_time|endTime"],
    "update_appointment": ["event_id|appointment_id"],
    "get_free_slots": ["calendar_id", "start_date|startDate", "end_date|endDate"],
    # Messages
    "send_sms": ["contact_id", "message"],
    "send_email": ["contact_id", "subject"],
    "send_message": ["contact_id", "type", "message|body"],
    "create_conversation": ["contact_id"],
    # Products
    "create_product": ["name"],
    "update_product": ["product_id"],
    "delete_product": ["product_id"],
    "create_product_price": ["product_id"],
    # Memberships/Courses
    "create_membership": ["title|name"],
    # Blogs
    "create_blog_post": ["title", "content", "blog_id|blogId"],
    "update_blog_post": ["post_id"],
    # Notes & Tasks
    "create_note": ["contact_id", "body"],
    "create_task": ["contact_id", "title"],
    # Workflows & Campaigns
    "add_contact_to_workflow": ["contact_id", "workflow_id"],
    "remove_contact_from_workflow": ["contact_id", "workflow_id"],
    "add_contact_to_campaign": ["contact_id", "campaign_id"],
    "remove_contact_from_campaign": ["contact_id", "campaign_id"],
    # Conversation AI
    "create_ai_agent": ["name", "business_name|businessName"],
    "update_ai_agent": ["agent_id|current_name"],
    "delete_ai_agent": ["agent_id"],
    "add_agent_action": ["agent_id", "type"],
    # Knowledge Base
    "create_knowledge_base": ["name"],
    "create_kb_faq": ["kb_id|knowledgeBaseId", "question", "answer"],
    "update_kb_faq": ["faq_id|current_question"],
    "delete_kb_faq": ["faq_id"],
    # Voice AI
    "create_voice_agent": ["name"],
    "update_voice_agent": ["agent_id"],
    "delete_voice_agent": ["agent_id"],
    # Invoices
    "create_invoice": ["contactId|contact_id"],
    "update_invoice": ["invoice_id"],
    "delete_invoice": ["invoice_id"],
    "send_invoice": ["invoice_id"],
    "void_invoice": ["invoice_id"],
    "record_invoice_payment": ["invoice_id"],
    # Payments
    "get_order": ["order_id"],
    "create_order_fulfillment": ["order_id"],
    "create_coupon": ["name"],
    # Custom Objects
    "create_custom_object": ["labels|name"],
    "create_object_record": ["schema_key|schemaKey"],
    "search_object_records": ["schema_key|schemaKey"],
    # Store
    "create_shipping_zone": ["name"],
    "create_shipping_rate": ["zone_id"],
    "create_shipping_carrier": ["name"],
    # Custom Menus
    "create_custom_menu": ["name"],
    "update_custom_menu": ["menu_id"],
    "delete_custom_menu": ["menu_id"],
    # Documents
    "send_document": ["documentId|document_id"],
    "send_document_template": ["templateId|template_id"],
    # Businesses
    "create_business": ["name"],
    "update_business": ["business_id"],
    "delete_business": ["business_id"],
    # Links
    "create_link": ["name", "redirect_to|redirectTo"],
    "update_link": ["link_id", "name"],
    "delete_link": ["link_id"],
    # Social Media
    "update_social_post": ["post_id"],
    "delete_social_post": ["post_id"],
    # Email
    "verify_email": ["email"],
    "get_snapshots": ["company_id"],
    # Funnel
    "create_funnel": ["name"],
    # Raw
    "raw": ["method", "endpoint"],
    # --- NEW: Full Coverage Additions ---
    # Contacts Extended
    "get_contacts_by_business": ["business_id"],
    "update_contact_note": ["contact_id", "note_id"],
    "delete_contact_note": ["contact_id", "note_id"],
    "update_contact_task": ["contact_id", "task_id"],
    "delete_contact_task": ["contact_id", "task_id"],
    "update_task_completed": ["contact_id", "task_id"],
    "add_contact_followers": ["contact_id"],
    "remove_contact_followers": ["contact_id"],
    # Opportunities Extended
    "add_opportunity_followers": ["opportunity_id"],
    "remove_opportunity_followers": ["opportunity_id"],
    # Calendar Groups
    "create_calendar_group": ["name"],
    "update_calendar_group": ["group_id"],
    "delete_calendar_group": ["group_id"],
    # Appointment Notes
    "create_appointment_note": ["appointment_id"],
    "update_appointment_note": ["appointment_id", "note_id"],
    "delete_appointment_note": ["appointment_id", "note_id"],
    # Funnels / Redirects
    "create_redirect": ["target|redirectTo"],
    "update_redirect": ["redirect_id"],
    "delete_redirect": ["redirect_id"],
    # Invoices Extended
    "create_invoice_template": ["name"],
    "update_invoice_template": ["template_id"],
    "delete_invoice_template": ["template_id"],
    "create_invoice_schedule": ["name"],
    "create_estimate": ["name"],
    "update_estimate": ["estimate_id"],
    "delete_estimate": ["estimate_id"],
    "send_estimate": ["estimate_id"],
    # Products Extended
    "create_collection": ["name"],
    "update_collection": ["collection_id"],
    "delete_collection": ["collection_id"],
    "update_product_review": ["review_id"],
    "delete_product_review": ["review_id"],
    # Custom Objects Extended
    "update_object_schema": ["key"],
    "get_object_record": ["schema_key|schemaKey", "record_id"],
    "update_object_record": ["schema_key|schemaKey", "record_id"],
    "delete_object_record": ["schema_key|schemaKey", "record_id"],
    # Associations Extended
    "create_relation": ["associationId|association_id"],
    "delete_relation": ["relation_id"],
    "update_association": ["association_id"],
    "delete_association": ["association_id"],
    # Store Extended
    "update_shipping_zone": ["zone_id"],
    "delete_shipping_zone": ["zone_id"],
    "update_shipping_rate": ["zone_id", "rate_id"],
    "delete_shipping_rate": ["zone_id", "rate_id"],
    "update_shipping_carrier": ["carrier_id"],
    "delete_shipping_carrier": ["carrier_id"],
    # Voice AI Extended
    "create_voice_action": ["agent_id"],
    "update_voice_action": ["action_id"],
    "delete_voice_action": ["action_id"],
    # Conversations Extended
    "update_conversation": ["conversation_id"],
    "delete_conversation": ["conversation_id"],
    # Media Extended
    "update_media_file": ["media_id"],
    "upload_media_file": ["file_url|url"],
    # Locations Extended
    "delete_location": ["location_id"],
    "update_tag": ["tag_id|current_name", "name"],
    # Users Extended
    "get_user": ["user_id"],
    # Blog Extended
    "create_blog_post": ["title", "content", "blog_id|blogId"],
    "update_blog_post": ["post_id"],
}


def validate_command(cmd: dict) -> list[str]:
    """Validate a command has all required fields. Returns list of missing fields."""
    action = cmd.get("action", "")
    required = REQUIRED_FIELDS.get(action, [])
    missing = []
    for field_spec in required:
        alternatives = field_spec.split("|")
        if not any(cmd.get(alt) for alt in alternatives):
            missing.append(alternatives[0])
    return missing


class PrimeFlowEngine:
    """
    The core engine. Takes structured commands, runs GHL API calls.

    Features:
        - Automatic retry on 429 (rate limit) and 5xx errors
        - Input validation for all commands
        - Batch command execution from JSON files
        - Result chaining between steps
        - Full logging with timestamps
    """

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 3, 5]  # seconds between retries

    def __init__(self, ghl_client: GHLClient | None = None):
        self.ghl = ghl_client or GHLClient()
        self.log: list[dict] = []
        self.results: dict[str, Any] = {}
        self.batch_results: list[dict] = []
        # Registry of ALL resources created during this run (for cross-command linking)
        self.created_resources: dict[str, list[dict]] = {}
        # Track auto-generated passwords for the report
        self.generated_passwords: list[dict] = []

    def _register_created(self, resource_type: str, resource_info: dict):
        """Register a newly created resource for cross-command linking."""
        if resource_type not in self.created_resources:
            self.created_resources[resource_type] = []
        self.created_resources[resource_type].append(resource_info)

    def _log(self, action: str, status: str, data: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": status,
            "data": data,
        }
        self.log.append(entry)
        icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
        print(f"  {icon} [{action}] {status}" + (f" → {data}" if data else ""))

    # ========================================================================
    # MASTER COMMAND ROUTER
    # ========================================================================

    async def run(self, command: dict) -> dict:
        """
        Main entry point. Route any command to the right handler.

        ALL GHL API v2 categories covered — 120+ actions:

        CONTACTS: create_contact, create_contacts, update_contact, delete_contact,
                  upsert_contact, get_contact, search_contacts, add_contact_tags,
                  remove_contact_tags, add_contact_to_campaign, remove_contact_from_campaign,
                  add_contact_to_workflow, remove_contact_from_workflow
        USERS: create_user, update_user, delete_user, get_users
        TAGS: create_tag, create_tags, delete_tag, get_tags
        CUSTOM FIELDS: create_custom_field, create_custom_fields, delete_custom_field, get_custom_fields
        CUSTOM VALUES: create_custom_value, get_custom_values
        OPPORTUNITIES: create_opportunity, update_opportunity, delete_opportunity,
                       update_opportunity_status, upsert_opportunity, search_opportunities, get_pipelines
        TEMPLATES: create_template, get_templates, get_email_templates, delete_email_template
        CALENDARS: create_calendar, update_calendar, delete_calendar, get_calendars,
                   create_appointment, update_appointment, get_calendar_events,
                   get_free_slots, create_block_slot, create_service_booking, get_service_bookings
        MESSAGES: send_sms, send_email, send_message, create_conversation, get_conversations
        INVOICES: create_invoice, get_invoices, get_invoice, update_invoice, delete_invoice,
                  send_invoice, void_invoice, record_invoice_payment, create_text2pay
        PAYMENTS: get_orders, get_order, create_order_fulfillment, get_transactions,
                  get_subscriptions, create_coupon, get_coupons, update_coupon, delete_coupon
        PRODUCTS: create_product, update_product, delete_product, get_products, create_product_price
        CUSTOM OBJECTS: get_object_schemas, create_custom_object, create_object_record, search_object_records
        VOICE AI: create_voice_agent, get_voice_agents, update_voice_agent, delete_voice_agent, get_voice_call_logs
        AI AGENTS: create_ai_agent, get_ai_agents, get_ai_agent, update_ai_agent, delete_ai_agent, add_agent_action
        STORE: create_shipping_zone, get_shipping_zones, create_shipping_rate,
               create_shipping_carrier, get_shipping_carriers, get_store_settings, update_store_settings
        CUSTOM MENUS: create_custom_menu, get_custom_menus, update_custom_menu, delete_custom_menu
        DOCUMENTS: get_documents, send_document, get_document_templates, send_document_template
        BLOGS: create_blog_post, update_blog_post, get_blogs, get_blog_posts
        SOCIAL: create_social_post, update_social_post, delete_social_post, get_social_accounts
        BUSINESSES: create_business, update_business, delete_business, get_businesses
        LINKS: create_link, update_link, delete_link, get_links
        MEDIA: get_media_files, delete_media_file, create_media_folder
        FORMS: get_forms, get_form_submissions
        SURVEYS: get_surveys, get_survey_submissions
        MISC: get_workflows, get_funnels, get_campaigns, get_snapshots, get_associations,
              create_association, verify_email, get_number_pools, get_active_numbers,
              get_location, update_location, list_actions, raw
        FUNNEL BUILDER: create_funnel (orchestrates tags+fields+values+templates+contacts+opportunities+products)
        """
        action = command.get("action", "")
        self.log = []
        self.results = {}

        print(f"\n{'='*50}")
        print(f"  PrimeFlow Engine — Running: {action}")
        print(f"{'='*50}\n")

        # Validate required fields
        missing = validate_command(command)
        if missing:
            error_msg = f"Missing required fields: {', '.join(missing)}"
            self._log(action, "error", error_msg)
            return {
                "action": action,
                "result": {"success": False, "error": error_msg},
                "log": self.log,
                "stored_results": self.results,
            }

        handler = getattr(self, f"_handle_{action}", None)
        if handler:
            result = await handler(command)
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
            self._log(action, "error", f"Unknown action: {action}")

        return {
            "action": action,
            "result": result,
            "log": self.log,
            "stored_results": self.results,
        }

    async def run_batch(self, commands: list[dict]) -> dict:
        """
        Run multiple commands in sequence. Results from each step are
        available to subsequent commands via self.results.
        """
        self.batch_results = []
        total = len(commands)

        print(f"\n{'='*50}")
        print(f"  PrimeFlow Engine — Batch Run ({total} commands)")
        print(f"{'='*50}\n")

        succeeded = 0
        failed = 0

        for i, cmd in enumerate(commands):
            print(f"\n  📋 [{i+1}/{total}] {cmd.get('action', '?')}")
            # Preserve results chain between batch commands
            saved_results = dict(self.results)
            result = await self.run(cmd)
            # Merge results back
            self.results.update(saved_results)
            self.results.update(result.get("stored_results", {}))

            self.batch_results.append(result)

            if result.get("result", {}).get("success"):
                succeeded += 1
            else:
                failed += 1
                # Stop on critical failure if specified
                if cmd.get("stop_on_error", False):
                    print(f"\n  🛑 Stopping batch — error in step {i+1}")
                    break

        summary = {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "results": self.batch_results,
            "stored_ids": self.results,
        }

        print(f"\n{'='*50}")
        print(f"  Batch Complete: {succeeded}/{total} succeeded, {failed} failed")
        print(f"{'='*50}\n")

        return summary

    async def _retry_on_failure(self, func, *args, **kwargs) -> dict:
        """
        Retry a GHL API call on transient failures (429 rate limit, 5xx server errors).
        """
        for attempt in range(self.MAX_RETRIES):
            result = await func(*args, **kwargs)

            if result.get("success"):
                return result

            status = result.get("status_code", 0)

            # Don't retry on client errors (except 429 rate limit)
            if 400 <= status < 500 and status != 429:
                return result

            # Retry on 429 or 5xx
            if status == 429 or status >= 500:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    self._log("retry", "running",
                               f"Attempt {attempt + 2}/{self.MAX_RETRIES} "
                               f"in {delay}s (status {status})")
                    await asyncio.sleep(delay)
                    continue

            return result

        return result

    # ========================================================================
    # CONTACTS
    # ========================================================================

    async def _handle_create_contact(self, cmd: dict) -> dict:
        """Create a single contact."""
        data = {
            "firstName": cmd.get("first_name", cmd.get("firstName", "")),
            "lastName": cmd.get("last_name", cmd.get("lastName", "")),
            "email": cmd.get("email", ""),
            "phone": cmd.get("phone", ""),
            "tags": cmd.get("tags", []),
            "source": cmd.get("source", "PrimeFlow Engine"),
        }
        # Add any custom fields
        if cmd.get("custom_fields"):
            data["customFields"] = cmd["custom_fields"]

        self._log("create_contact", "running", f"{data['firstName']} {data['lastName']}")
        result = await self._retry_on_failure(self.ghl.create_contact, data)

        if result.get("success"):
            contact_id = result.get("data", {}).get("contact", {}).get("id", "")
            self._log("create_contact", "success", f"ID: {contact_id}")
            self.results["contact_id"] = contact_id

            # Add tags if specified separately
            if cmd.get("add_tags"):
                await self._handle_add_contact_tags({
                    "contact_id": contact_id,
                    "tags": cmd["add_tags"],
                })
        else:
            self._log("create_contact", "error", result.get("error"))

        return result

    async def _handle_create_contacts(self, cmd: dict) -> dict:
        """Create multiple contacts from a list."""
        contacts = cmd.get("contacts", [])
        created = []
        failed = []

        for i, contact_data in enumerate(contacts):
            contact_data["action"] = "create_contact"
            result = await self._handle_create_contact(contact_data)
            if result.get("success"):
                created.append(result)
            else:
                failed.append({"index": i, "error": result.get("error"), "data": contact_data})

        return {
            "success": len(failed) == 0,
            "created": len(created),
            "failed": len(failed),
            "failures": failed,
        }

    async def _handle_add_contact_tags(self, cmd: dict) -> dict:
        """Add tags to a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        tags = cmd.get("tags", [])

        if not contact_id:
            return {"success": False, "error": "No contact_id provided"}

        self._log("add_tags", "running", f"{tags} → {contact_id}")
        result = await self.ghl.add_contact_tags(contact_id, tags)

        if result.get("success"):
            self._log("add_tags", "success")
        else:
            self._log("add_tags", "error", result.get("error"))

        return result

    async def _handle_update_contact(self, cmd: dict) -> dict:
        """Update an existing contact.
        Accepts flat fields (first_name, phone, etc.) OR a 'data' wrapper."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))

        if not contact_id:
            return {"success": False, "error": "No contact_id provided"}

        # Support both flat fields and 'data' wrapper
        data = cmd.get("data", None)
        if data is None:
            # Flat fields — extract everything except meta fields
            data = {k: v for k, v in cmd.items()
                    if k not in ("action", "contact_id", "contactId",
                                 "current_name")}

        self._log("update_contact", "running", f"ID: {contact_id}")
        result = await self.ghl.update_contact(contact_id, data)

        if result.get("success"):
            self._log("update_contact", "success")
        else:
            self._log("update_contact", "error", result.get("error"))

        return result

    async def _handle_search_contacts(self, cmd: dict) -> dict:
        """Search contacts."""
        query = cmd.get("query", "")
        self._log("search_contacts", "running", f"query: {query}")
        result = await self.ghl.get_contacts(query=query, limit=cmd.get("limit", 20))

        if result.get("success"):
            contacts = result.get("data", {}).get("contacts", [])
            self._log("search_contacts", "success", f"Found {len(contacts)}")
        else:
            self._log("search_contacts", "error", result.get("error"))

        return result

    # ========================================================================
    # USERS
    # ========================================================================

    async def _handle_create_user(self, cmd: dict) -> dict:
        """
        Create a user/team member in a location.

        Required from prompt: first_name, last_name, email
        Optional: phone, role (admin/user), password, company_id, permissions

        Auto-detected:
            - company_id: fetched from location if not provided
            - password: auto-generated if not provided
            - location_ids: defaults to current location
            - type: defaults to "account"
        """
        import secrets
        import string

        # Auto-detect companyId from location if not provided
        company_id = cmd.get("company_id", cmd.get("companyId", ""))
        if not company_id:
            try:
                loc_result = await self.ghl.get_location(self.ghl.location_id)
                loc_data = loc_result.get("data", {}).get(
                    "location", loc_result.get("data", {}))
                company_id = loc_data.get("companyId", "")
            except Exception:
                pass

        # Auto-generate a name-based password if not provided
        # GHL requires: 8+ chars, uppercase, lowercase, number, special char
        password = cmd.get("password", "")
        password_generated = False
        if not password:
            password_generated = True
            first = cmd.get("first_name", cmd.get("firstName", "User"))
            last = cmd.get("last_name", cmd.get("lastName", ""))
            # Transliterate Hebrew names to English for the password
            hebrew_map = {
                'א': 'A', 'ב': 'B', 'ג': 'G', 'ד': 'D', 'ה': 'H',
                'ו': 'V', 'ז': 'Z', 'ח': 'Ch', 'ט': 'T', 'י': 'Y',
                'כ': 'K', 'ך': 'K', 'ל': 'L', 'מ': 'M', 'ם': 'M',
                'נ': 'N', 'ן': 'N', 'ס': 'S', 'ע': 'A', 'פ': 'P',
                'ף': 'P', 'צ': 'Tz', 'ץ': 'Tz', 'ק': 'K', 'ר': 'R',
                'ש': 'Sh', 'ת': 'T',
            }
            def _transliterate(text: str) -> str:
                result = []
                for ch in text:
                    if ch in hebrew_map:
                        result.append(hebrew_map[ch])
                    elif ch.isascii() and ch.isalpha():
                        result.append(ch)
                return ''.join(result) or "User"

            name_part = _transliterate(first).capitalize()
            last_part = _transliterate(last).capitalize() if last else ""
            # Build: Name_Last + random 3-digit number + special char
            # e.g. "Tzahi_Levi472!" or "Eldan_BiYatziv83#"
            digits = ''.join(secrets.choice(string.digits) for _ in range(3))
            special = secrets.choice("!@#$%&*")
            if last_part:
                password = f"{name_part}_{last_part}{digits}{special}"
            else:
                password = f"{name_part}{digits}{special}"
            # Ensure minimum 8 chars (should always be met with name + 4 suffix chars)
            if len(password) < 8:
                password += ''.join(secrets.choice(string.ascii_letters) for _ in range(8 - len(password)))

        data = {
            "companyId": company_id,
            "firstName": cmd.get("first_name", cmd.get("firstName", "")),
            "lastName": cmd.get("last_name", cmd.get("lastName", "")),
            "email": cmd.get("email", ""),
            "password": password,
            "type": cmd.get("type", "account"),
            "role": cmd.get("role", "user"),
            "locationIds": cmd.get("location_ids", cmd.get("locationIds",
                                                           [self.ghl.location_id])),
        }

        if cmd.get("phone"):
            data["phone"] = cmd["phone"]
        if cmd.get("permissions"):
            data["permissions"] = cmd["permissions"]
        if cmd.get("scopes"):
            data["scopes"] = cmd["scopes"]

        self._log("create_user", "running",
                  f"{data['firstName']} {data['lastName']} ({data['email']})")
        result = await self._retry_on_failure(self.ghl.create_user, data)

        if result.get("success"):
            user_id = result.get("data", {}).get("id", "")
            self._log("create_user", "success", f"User ID: {user_id}")
            self.results["user_id"] = user_id
            self._register_created("users", {
                "id": user_id,
                "firstName": data["firstName"],
                "lastName": data["lastName"],
                "email": data["email"],
                "role": data["role"],
            })
            # Track generated password for report
            if password_generated:
                self.generated_passwords.append({
                    "name": f"{data['firstName']} {data['lastName']}".strip(),
                    "email": data["email"],
                    "password": password,
                    "role": data["role"],
                })
            # Attach password info to result for report rendering
            result["_generated_password"] = password if password_generated else None
        else:
            self._log("create_user", "error", result.get("error"))

        return result

    async def _handle_get_users(self, cmd: dict) -> dict:
        """Get all users in current location."""
        self._log("get_users", "running")
        result = await self.ghl.get_users_by_location()

        if result.get("success"):
            users = result.get("data", {}).get("users", [])
            self._log("get_users", "success", f"Found {len(users)} users")
        else:
            self._log("get_users", "error", result.get("error"))

        return result

    # ========================================================================
    # TAGS
    # ========================================================================

    async def _handle_create_tag(self, cmd: dict) -> dict:
        """Create a location tag."""
        name = cmd.get("name", "")
        self._log("create_tag", "running", name)
        result = await self._retry_on_failure(self.ghl.create_tag, name)

        if result.get("success"):
            tag_id = result.get("data", {}).get("tag", {}).get("id", "")
            self._log("create_tag", "success", f"Tag ID: {tag_id}")
            self.results.setdefault("tag_ids", []).append(tag_id)
        else:
            self._log("create_tag", "error", result.get("error"))

        return result

    async def _handle_create_tags(self, cmd: dict) -> dict:
        """Create multiple tags."""
        tags = cmd.get("tags", [])
        results = []
        for tag_name in tags:
            r = await self._handle_create_tag({"name": tag_name})
            results.append(r)
        return {"success": all(r.get("success") for r in results), "results": results}

    # ========================================================================
    # CUSTOM FIELDS
    # ========================================================================

    async def _handle_create_custom_field(self, cmd: dict) -> dict:
        """
        Create a custom field.

        Required: name, data_type
        data_type options: TEXT, LARGE_TEXT, NUMERICAL, PHONE, MONETORY,
                          CHECKBOX, SINGLE_OPTIONS, MULTIPLE_OPTIONS, DATE,
                          TEXTBOX_LIST, FILE_UPLOAD, RADIO, FLOAT, TIME,
                          SIGNATURE
        Optional: fieldKey (English key — critical for Hebrew names to avoid
                  GHL fieldKey collisions), placeholder,
                  options (for SINGLE_OPTIONS/MULTIPLE_OPTIONS)
        """
        name = cmd.get("name", "")
        data_type = cmd.get("data_type", cmd.get("dataType", "TEXT"))

        kwargs = {}
        if cmd.get("fieldKey"):
            kwargs["fieldKey"] = cmd["fieldKey"]
        if cmd.get("placeholder"):
            kwargs["placeholder"] = cmd["placeholder"]
        if cmd.get("options"):
            kwargs["options"] = cmd["options"]
        if cmd.get("textBoxListOptions"):
            raw_opts = cmd["textBoxListOptions"]
            # GHL expects [{label, prefillValue}] — auto-convert from strings
            if raw_opts and isinstance(raw_opts[0], str):
                kwargs["textBoxListOptions"] = [
                    {"label": opt, "prefillValue": ""} for opt in raw_opts
                ]
            else:
                kwargs["textBoxListOptions"] = raw_opts
        if cmd.get("model"):
            kwargs["model"] = cmd["model"]

        self._log("create_custom_field", "running", f"{name} ({data_type})")
        result = await self._retry_on_failure(self.ghl.create_custom_field,
                                               name, data_type, **kwargs)

        if result.get("success"):
            field_id = result.get("data", {}).get("customField", {}).get("id", "")
            field_key = result.get("data", {}).get("customField", {}).get("fieldKey", cmd.get("fieldKey", ""))
            self._log("create_custom_field", "success", f"Field ID: {field_id}")
            self.results.setdefault("custom_field_ids", []).append(field_id)
            self._register_created("custom_fields", {
                "id": field_id,
                "name": name,
                "fieldKey": field_key,
                "dataType": data_type,
                "options": cmd.get("options", []),
            })
        else:
            self._log("create_custom_field", "error", result.get("error"))

        return result

    async def _handle_create_custom_fields(self, cmd: dict) -> dict:
        """Create multiple custom fields."""
        fields = cmd.get("fields", [])
        results = []
        for field in fields:
            field["action"] = "create_custom_field"
            r = await self._handle_create_custom_field(field)
            results.append(r)
        return {"success": all(r.get("success") for r in results), "results": results}

    # ========================================================================
    # CUSTOM VALUES
    # ========================================================================

    async def _handle_create_custom_value(self, cmd: dict) -> dict:
        """Create a custom value (location-level variable)."""
        name = cmd.get("name", "")
        value = cmd.get("value", "")

        self._log("create_custom_value", "running", f"{name} = {value}")
        result = await self._retry_on_failure(self.ghl.create_custom_value, name, value)

        if result.get("success"):
            self._log("create_custom_value", "success")
        else:
            self._log("create_custom_value", "error", result.get("error"))

        return result

    # ========================================================================
    # OPPORTUNITIES / PIPELINES
    # ========================================================================

    async def _handle_create_opportunity(self, cmd: dict) -> dict:
        """Create an opportunity in a pipeline."""
        data = {
            "pipelineId": cmd.get("pipeline_id", cmd.get("pipelineId", "")),
            "name": cmd.get("name", ""),
            "status": cmd.get("status", "open"),
            "contactId": cmd.get("contact_id", cmd.get("contactId",
                                  self.results.get("contact_id", ""))),
        }
        if cmd.get("stage_id") or cmd.get("stageId"):
            data["pipelineStageId"] = cmd.get("stage_id", cmd.get("stageId", ""))
        if cmd.get("monetary_value") or cmd.get("monetaryValue"):
            data["monetaryValue"] = cmd.get("monetary_value", cmd.get("monetaryValue", 0))

        self._log("create_opportunity", "running", f"{data['name']}")
        result = await self._retry_on_failure(self.ghl.create_opportunity, data)

        if result.get("success"):
            opp_id = result.get("data", {}).get("opportunity", {}).get("id", "")
            self._log("create_opportunity", "success", f"Opportunity ID: {opp_id}")
            self.results["opportunity_id"] = opp_id
        else:
            self._log("create_opportunity", "error", result.get("error"))

        return result

    async def _handle_get_pipelines(self, cmd: dict) -> dict:
        """Get all pipelines."""
        self._log("get_pipelines", "running")
        result = await self.ghl.get_pipelines()
        if result.get("success"):
            pipelines = result.get("data", {}).get("pipelines", [])
            self._log("get_pipelines", "success", f"Found {len(pipelines)}")
        else:
            self._log("get_pipelines", "error", result.get("error"))
        return result

    # ========================================================================
    # TEMPLATES (Email / SMS)
    # ========================================================================

    def _generate_email_html(self, cmd: dict) -> str:
        """
        Generate professional HTML email template based on business context.

        Reads niche, business_name, subject, purpose, services, and language
        from the command and generates a responsive HTML email.
        """
        business_name = cmd.get("business_name", cmd.get("businessName", ""))
        subject = cmd.get("subject", cmd.get("name", ""))
        purpose = cmd.get("purpose", "general").lower()
        language = cmd.get("language", "he")
        is_he = language == "he"
        direction = "rtl" if is_he else "ltr"
        align = "right" if is_he else "left"
        services = cmd.get("services", [])
        cta_text = cmd.get("cta_text", "")
        cta_url = cmd.get("cta_url", "{{contact.calendar_link}}")
        body_text = cmd.get("body_text", "")

        # Purpose-based content generation
        if purpose == "welcome":
            if is_he:
                headline = f"ברוכים הבאים ל-{business_name}!"
                if not body_text:
                    body_text = f"היי {{{{contact.first_name}}}},\n\nשמחים שהצטרפת אלינו! אנחנו ב-{business_name} כאן כדי לעזור לך להצליח."
                if not cta_text:
                    cta_text = "בוא/י נתחיל →"
            else:
                headline = f"Welcome to {business_name}!"
                if not body_text:
                    body_text = f"Hey {{{{contact.first_name}}}},\n\nWe're glad you joined! At {business_name}, we're here to help you succeed."
                if not cta_text:
                    cta_text = "Let's get started →"

        elif purpose == "followup":
            if is_he:
                headline = f"רק רצינו לבדוק..."
                if not body_text:
                    body_text = f"היי {{{{contact.first_name}}}},\n\nרצינו לשמוע ממך. ראינו שהתעניינת ורצינו לוודא שיש לך את כל המידע שאתה צריך."
                if not cta_text:
                    cta_text = "קבע/י שיחה קצרה"
            else:
                headline = "Just checking in..."
                if not body_text:
                    body_text = f"Hey {{{{contact.first_name}}}},\n\nWe noticed you were interested and wanted to make sure you have everything you need."
                if not cta_text:
                    cta_text = "Schedule a quick call"

        elif purpose == "booking_confirmation":
            if is_he:
                headline = "הפגישה שלך אושרה!"
                if not body_text:
                    body_text = f"היי {{{{contact.first_name}}}},\n\nהפגישה שלך עם {business_name} אושרה. נשמח לראות אותך!"
                if not cta_text:
                    cta_text = "הוסף ליומן"
            else:
                headline = "Your appointment is confirmed!"
                if not body_text:
                    body_text = f"Hey {{{{contact.first_name}}}},\n\nYour appointment with {business_name} is confirmed. Looking forward to meeting you!"
                if not cta_text:
                    cta_text = "Add to calendar"

        elif purpose == "promotion":
            if is_he:
                headline = cmd.get("headline", f"הצעה מיוחדת מ-{business_name}")
                if not body_text:
                    body_text = f"היי {{{{contact.first_name}}}},\n\nיש לנו משהו מיוחד בשבילך."
                if not cta_text:
                    cta_text = "לפרטים נוספים →"
            else:
                headline = cmd.get("headline", f"Special offer from {business_name}")
                if not body_text:
                    body_text = f"Hey {{{{contact.first_name}}}},\n\nWe have something special for you."
                if not cta_text:
                    cta_text = "Learn more →"

        else:  # general
            headline = cmd.get("headline", business_name)
            if not body_text:
                if is_he:
                    body_text = f"היי {{{{contact.first_name}}}},\n\nתודה שפנית אלינו."
                else:
                    body_text = f"Hey {{{{contact.first_name}}}},\n\nThank you for reaching out."
            if not cta_text:
                cta_text = "צור/י קשר" if is_he else "Get in touch"

        # Build services list HTML
        services_html = ""
        if services:
            items = "".join(f'<li style="padding:4px 0">{s}</li>' for s in services)
            services_html = f'<ul style="text-align:{align};padding:0 20px">{items}</ul>'

        # Body text with line breaks
        body_html = body_text.replace("\n", "<br>")

        # Build responsive HTML email
        html = f"""<!DOCTYPE html>
<html dir="{direction}" lang="{language}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;max-width:600px;width:100%">

<!-- Header -->
<tr><td style="background:#2563eb;padding:30px 40px;text-align:center">
<h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:600">{headline}</h1>
</td></tr>

<!-- Body -->
<tr><td style="padding:30px 40px;text-align:{align};color:#333333;font-size:15px;line-height:1.6">
{body_html}
{services_html}
</td></tr>

<!-- CTA Button -->
<tr><td style="padding:0 40px 30px;text-align:center">
<a href="{cta_url}" style="display:inline-block;background:#2563eb;color:#ffffff;padding:12px 32px;border-radius:6px;text-decoration:none;font-size:15px;font-weight:600">{cta_text}</a>
</td></tr>

<!-- Footer -->
<tr><td style="background:#f8f9fa;padding:20px 40px;text-align:center;font-size:12px;color:#888888">
{business_name}<br>
{'נשלח באמצעות PrimeFlow' if is_he else 'Sent via PrimeFlow'}
</td></tr>

</table>
</td></tr></table>
</body></html>"""
        return html

    async def _handle_create_template(self, cmd: dict) -> dict:
        """
        Create an email or SMS template.

        For Email: { "type": "email", "name": "...", "subject": "...", "html": "..." }
            → Uses /emails/builder endpoint (works with Private Integration keys)
            → If no "html" provided but business context exists, auto-generates HTML

        For SMS:  { "type": "sms", "name": "...", "body": "..." }
            → Uses /conversations/messages for direct send
        """
        template_type = cmd.get("type", "email").lower()

        if template_type == "sms":
            sms_template = {
                "name": cmd.get("name", ""),
                "type": "sms",
                "body": cmd.get("body", ""),
            }
            self._log("create_template", "running", f"sms: {sms_template['name']}")
            self.results.setdefault("sms_templates", []).append(sms_template)
            self._log("create_template", "success",
                       f"SMS template '{sms_template['name']}' stored (direct-send ready)")
            return {
                "success": True,
                "data": {"template": sms_template},
                "note": "SMS templates stored in engine. Use send_sms action to send.",
            }
        else:
            html_body = cmd.get("html", cmd.get("body", ""))

            # Auto-generate HTML if not provided but business context exists
            if not html_body and (cmd.get("business_name") or cmd.get("purpose")):
                html_body = self._generate_email_html(cmd)
                print(f"    📧 Auto-generated email HTML for: {cmd.get('purpose', 'general')}")

            data = {
                "title": cmd.get("name", ""),
                "type": "html",
            }

            self._log("create_template", "running", f"email: {data['title']}")
            result = await self.ghl.create_email_template(data)

            if result.get("success"):
                resp_data = result.get("data", {})
                template_id = resp_data.get("_id", resp_data.get("id", ""))
                self._log("create_template", "success", f"Template ID: {template_id}")
                self.results.setdefault("template_ids", []).append(template_id)

                if html_body and template_id:
                    update_result = await self.ghl.update_email_template_data({
                        "templateId": template_id,
                        "updatedBy": "PrimeFlow Engine",
                        "editorType": "html",
                        "html": html_body,
                    })
                    if update_result.get("success"):
                        self._log("update_template_html", "success", f"HTML set for {template_id}")
                    else:
                        self._log("update_template_html", "error",
                                   update_result.get("error", "Failed to set HTML"))
            else:
                self._log("create_template", "error", result.get("error"))

            return result

    # ========================================================================
    # CALENDARS & APPOINTMENTS
    # ========================================================================

    async def _handle_create_calendar(self, cmd: dict) -> dict:
        """Create a calendar with full GHL field support."""
        data = {
            "name": cmd.get("name", ""),
            "locationId": self.ghl.location_id,
        }
        # All supported GHL calendar fields
        CALENDAR_FIELDS = [
            "description", "slug", "widgetSlug", "calendarType", "widgetType",
            "eventType", "teamMembers", "availability", "openHours",
            "availabilities", "availabilityType", "notifications",
            "locationConfigurations", "recurring", "enableRecurring",
            "slotDuration", "slotDurationUnit", "slotInterval", "slotIntervalUnit",
            "slotBuffer", "slotBufferUnit", "preBuffer", "preBufferUnit",
            "appoinmentPerSlot", "appoinmentPerDay", "autoConfirm",
            "allowReschedule", "allowCancellation", "allowBookingAfter",
            "allowBookingAfterUnit", "allowBookingFor", "allowBookingForUnit",
            "isActive", "formId", "stickyContact", "isLivePaymentMode",
            "shouldSendAlertEmailsToAssignedMember", "alertEmail",
            "googleInvitationEmails", "shouldAssignContactToTeamMember",
            "shouldSkipAssigningContactForExisting", "groupId",
            "formSubmitType", "formSubmitRedirectURL", "formSubmitThanksMessage",
            "eventTitle", "eventColor", "consentLabel", "calendarCoverImage",
            "pixelId", "guestType", "lookBusyConfig", "notes",
        ]
        for key in CALENDAR_FIELDS:
            val = cmd.get(key)
            if val is not None:
                data[key] = val

        self._log("create_calendar", "running", data["name"])
        result = await self.ghl.create_calendar(data)

        if result.get("success"):
            cal_id = result.get("data", {}).get("calendar", {}).get("id", "")
            self._log("create_calendar", "success", f"Calendar ID: {cal_id}")
            self.results["calendar_id"] = cal_id
            self._register_created("calendars", {
                "id": cal_id,
                "name": cmd.get("name", ""),
                "description": cmd.get("description", ""),
                "calendarType": cmd.get("calendarType", "event"),
                "slotDuration": cmd.get("slotDuration", 30),
            })
        else:
            self._log("create_calendar", "error", result.get("error"))

        return result

    async def _handle_create_calendar_notification(self, cmd: dict) -> dict:
        """
        Create a notification/reminder for a calendar.

        Uses: POST /calendars/{calendarId}/notifications

        Required: calendar_id, channel, notificationType, receiverType
        Optional: body, subject, beforeTime, afterTime, selectedUsers, isActive
        """
        calendar_id = cmd.get("calendar_id", cmd.get("calendarId", ""))
        # Auto-link: if no explicit calendar_id, use the last created calendar
        if not calendar_id:
            calendars = self.created_resources.get("calendars", [])
            if calendars:
                calendar_id = calendars[-1].get("id", "")
        if not calendar_id:
            return {"success": False, "error": "Missing calendar_id"}

        data = {}
        NOTIF_FIELDS = [
            "channel", "notificationType", "receiverType", "isActive", "deleted",
            "templateId", "subject", "body", "fromAddress", "fromNumber", "fromName",
            "additionalEmailIds", "additionalPhoneNumbers", "selectedUsers",
            "beforeTime", "afterTime",
        ]
        for key in NOTIF_FIELDS:
            val = cmd.get(key)
            if val is not None:
                data[key] = val

        channel = data.get("channel", "")
        ntype = data.get("notificationType", "")
        receiver = data.get("receiverType", "")
        timing = ""
        if data.get("beforeTime"):
            bt = data["beforeTime"]
            if isinstance(bt, list) and bt:
                timing = f" ({bt[0].get('timeOffset', '')} {bt[0].get('unit', '')} before)"

        self._log("create_calendar_notification", "running",
                  f"{channel}/{ntype} → {receiver}{timing}")
        result = await self.ghl.create_calendar_notification(calendar_id, data)

        if result.get("success"):
            # GHL returns data as a list: [{ "_id": "...", ... }]
            resp_data = result.get("data", {})
            if isinstance(resp_data, list) and resp_data:
                notif_id = resp_data[0].get("_id", resp_data[0].get("id", ""))
            elif isinstance(resp_data, dict):
                notif_id = resp_data.get("_id", resp_data.get("id", ""))
            else:
                notif_id = ""
            self._log("create_calendar_notification", "success",
                      f"Notification ID: {notif_id}")
        else:
            self._log("create_calendar_notification", "error", result.get("error"))

        return result

    async def _handle_create_appointment(self, cmd: dict) -> dict:
        """Book an appointment."""
        data = {
            "calendarId": cmd.get("calendar_id", cmd.get("calendarId",
                                   self.results.get("calendar_id", ""))),
            "locationId": self.ghl.location_id,
            "contactId": cmd.get("contact_id", cmd.get("contactId",
                                  self.results.get("contact_id", ""))),
            "startTime": cmd.get("start_time", cmd.get("startTime", "")),
            "endTime": cmd.get("end_time", cmd.get("endTime", "")),
            "title": cmd.get("title", ""),
            "appointmentStatus": cmd.get("status", "confirmed"),
        }

        self._log("create_appointment", "running", data["title"])
        result = await self.ghl.create_appointment(data)

        if result.get("success"):
            self._log("create_appointment", "success")
        else:
            self._log("create_appointment", "error", result.get("error"))

        return result

    # ========================================================================
    # MESSAGING
    # ========================================================================

    async def _handle_send_sms(self, cmd: dict) -> dict:
        """Send an SMS to a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        message = cmd.get("message", "")

        self._log("send_sms", "running", f"→ {contact_id[:12]}...")
        result = await self.ghl.send_sms(contact_id, message)

        if result.get("success"):
            self._log("send_sms", "success")
        else:
            self._log("send_sms", "error", result.get("error"))

        return result

    async def _handle_send_email(self, cmd: dict) -> dict:
        """Send an email to a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        subject = cmd.get("subject", "")
        html = cmd.get("html", cmd.get("body", ""))

        self._log("send_email", "running", f"Subject: {subject}")
        result = await self.ghl.send_email(contact_id, subject, html)

        if result.get("success"):
            self._log("send_email", "success")
        else:
            self._log("send_email", "error", result.get("error"))

        return result

    # ========================================================================
    # PRODUCTS
    # ========================================================================

    async def _handle_create_product(self, cmd: dict) -> dict:
        """Create a product."""
        data = {
            "name": cmd.get("name", ""),
            "description": cmd.get("description", ""),
            "productType": cmd.get("product_type", "DIGITAL"),
        }
        if cmd.get("image"):
            data["image"] = cmd["image"]

        self._log("create_product", "running", data["name"])
        result = await self.ghl.create_product(data)

        if result.get("success"):
            product_id = result.get("data", {}).get("product", {}).get("_id", "")
            self._log("create_product", "success", f"Product ID: {product_id}")
            self.results["product_id"] = product_id

            # Create price if specified
            if cmd.get("price"):
                price_data = {
                    "name": cmd.get("price_name", "Default Price"),
                    "type": cmd.get("price_type", "one_time"),
                    "amount": cmd["price"],
                    "currency": cmd.get("currency", "ILS"),
                }
                await self.ghl.create_product_price(product_id, price_data)
                self._log("create_product_price", "success")
        else:
            self._log("create_product", "error", result.get("error"))

        return result

    # ========================================================================
    # MEMBERSHIPS / COURSES
    # ========================================================================

    async def _handle_create_membership(self, cmd: dict) -> dict:
        """
        Create a membership product with categories and lessons.

        Input:
        {
            "action": "create_membership",
            "title": "Course Name",
            "description": "Course description",
            "categories": [
                {
                    "title": "Module 1",
                    "posts": [
                        {
                            "title": "Lesson 1",
                            "description": "Lesson description",
                            "contentType": "video"
                        }
                    ]
                }
            ]
        }

        Supported contentType: video, audio, assignment, quiz
        """
        title = cmd.get("title", cmd.get("name", ""))
        description = cmd.get("description", "")
        categories = cmd.get("categories", cmd.get("modules", []))

        # Build the import structure
        product = {
            "title": title,
            "description": description,
        }
        if cmd.get("visibility"):
            product["visibility"] = cmd["visibility"]

        # Process categories/modules
        processed_categories = []
        for cat in categories:
            category = {
                "title": cat.get("title", cat.get("name", "")),
            }
            posts = []
            for lesson in cat.get("posts", cat.get("lessons", [])):
                post = {
                    "title": lesson.get("title", lesson.get("name", "")),
                    "description": lesson.get("description", ""),
                    "contentType": lesson.get("contentType", "video"),
                }
                if lesson.get("posterImageUrl"):
                    post["posterImageUrl"] = lesson["posterImageUrl"]
                if lesson.get("videoUrl"):
                    post["bucketVideoUrl"] = lesson["videoUrl"]
                posts.append(post)
            category["posts"] = posts
            processed_categories.append(category)

        product["categories"] = processed_categories

        import_data = {
            "products": [product],
            "locationId": self.ghl.location_id,
        }

        total_lessons = sum(len(c.get("posts", [])) for c in processed_categories)
        self._log("create_membership", "running",
                   f"{title} ({len(processed_categories)} modules, {total_lessons} lessons)")

        result = await self._retry_on_failure(self.ghl.import_courses, import_data)

        if result.get("success"):
            resp_data = result.get("data", {})
            courses = resp_data.get("processingCourses", [])
            course_id = courses[0].get("id", "") if courses else ""
            self._log("create_membership", "success",
                       f"Course ID: {course_id} (processing in background)")
            self.results["membership_id"] = course_id
        else:
            self._log("create_membership", "error", result.get("error"))

        return result

    # ========================================================================
    # BLOGS
    # ========================================================================

    async def _handle_create_blog_post(self, cmd: dict) -> dict:
        """Create a blog post."""
        data = {
            "title": cmd.get("title", ""),
            "content": cmd.get("content", ""),
            "status": cmd.get("status", "draft"),
            "blogId": cmd.get("blog_id", cmd.get("blogId", "")),
        }
        if cmd.get("author_id"):
            data["authorId"] = cmd["author_id"]
        if cmd.get("category_ids"):
            data["categoryIds"] = cmd["category_ids"]
        if cmd.get("tags"):
            data["tags"] = cmd["tags"]

        self._log("create_blog_post", "running", data["title"])
        result = await self.ghl.create_blog_post(data)

        if result.get("success"):
            self._log("create_blog_post", "success")
        else:
            self._log("create_blog_post", "error", result.get("error"))

        return result

    # ========================================================================
    # CONTACT NOTES
    # ========================================================================

    async def _handle_create_note(self, cmd: dict) -> dict:
        """Add a note to a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        body = cmd.get("body", "")
        user_id = cmd.get("user_id")

        self._log("create_note", "running", f"Note for {contact_id[:12]}...")
        result = await self._retry_on_failure(
            self.ghl.create_contact_note, contact_id, body, user_id)

        if result.get("success"):
            self._log("create_note", "success")
        else:
            self._log("create_note", "error", result.get("error"))

        return result

    async def _handle_get_notes(self, cmd: dict) -> dict:
        """Get notes for a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        self._log("get_notes", "running", f"Contact: {contact_id[:12]}...")
        result = await self.ghl.get_contact_notes(contact_id)
        if result.get("success"):
            notes = result.get("data", {}).get("notes", [])
            self._log("get_notes", "success", f"Found {len(notes)}")
        else:
            self._log("get_notes", "error", result.get("error"))
        return result

    # ========================================================================
    # CONTACT TASKS
    # ========================================================================

    async def _handle_create_task(self, cmd: dict) -> dict:
        """Create a task for a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        data = {
            "title": cmd.get("title", ""),
            "body": cmd.get("body", cmd.get("description", "")),
            "dueDate": cmd.get("due_date", cmd.get("dueDate", "")),
            "completed": cmd.get("completed", False),
        }
        if cmd.get("assignedTo"):
            data["assignedTo"] = cmd["assignedTo"]

        self._log("create_task", "running", data["title"])
        result = await self._retry_on_failure(
            self.ghl.create_contact_task, contact_id, data)

        if result.get("success"):
            self._log("create_task", "success")
        else:
            self._log("create_task", "error", result.get("error"))

        return result

    async def _handle_get_tasks(self, cmd: dict) -> dict:
        """Get tasks for a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        self._log("get_tasks", "running", f"Contact: {contact_id[:12]}...")
        result = await self.ghl.get_contact_tasks(contact_id)
        if result.get("success"):
            tasks = result.get("data", {}).get("tasks", [])
            self._log("get_tasks", "success", f"Found {len(tasks)}")
        else:
            self._log("get_tasks", "error", result.get("error"))
        return result

    # ========================================================================
    # WORKFLOW ENROLLMENT
    # ========================================================================

    async def _handle_add_contact_to_workflow(self, cmd: dict) -> dict:
        """Add a contact to a workflow (triggers it)."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        workflow_id = cmd.get("workflow_id", "")

        self._log("add_to_workflow", "running",
                   f"Contact {contact_id[:12]}... → Workflow {workflow_id[:12]}...")
        result = await self._retry_on_failure(
            self.ghl.add_contact_to_workflow, contact_id, workflow_id)

        if result.get("success"):
            self._log("add_to_workflow", "success")
        else:
            self._log("add_to_workflow", "error", result.get("error"))

        return result

    async def _handle_remove_contact_from_workflow(self, cmd: dict) -> dict:
        """Remove a contact from a workflow."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        workflow_id = cmd.get("workflow_id", "")

        self._log("remove_from_workflow", "running",
                   f"Contact {contact_id[:12]}... ← Workflow {workflow_id[:12]}...")
        result = await self.ghl.remove_contact_from_workflow(contact_id, workflow_id)

        if result.get("success"):
            self._log("remove_from_workflow", "success")
        else:
            self._log("remove_from_workflow", "error", result.get("error"))

        return result

    # ========================================================================
    # UPSERT OPERATIONS
    # ========================================================================

    async def _handle_upsert_contact(self, cmd: dict) -> dict:
        """Create or update a contact (matches by email/phone)."""
        data = {
            "firstName": cmd.get("first_name", cmd.get("firstName", "")),
            "lastName": cmd.get("last_name", cmd.get("lastName", "")),
            "email": cmd.get("email", ""),
            "phone": cmd.get("phone", ""),
            "tags": cmd.get("tags", []),
            "source": cmd.get("source", "PrimeFlow Engine"),
        }
        if cmd.get("custom_fields"):
            data["customFields"] = cmd["custom_fields"]

        self._log("upsert_contact", "running", f"{data['firstName']} {data['lastName']}")
        result = await self._retry_on_failure(self.ghl.upsert_contact, data)

        if result.get("success"):
            contact = result.get("data", {}).get("contact", {})
            contact_id = contact.get("id", "")
            new = result.get("data", {}).get("new", False)
            action_type = "Created" if new else "Updated"
            self._log("upsert_contact", "success",
                       f"{action_type} — ID: {contact_id}")
            self.results["contact_id"] = contact_id
        else:
            self._log("upsert_contact", "error", result.get("error"))

        return result

    # ========================================================================
    # DELETE OPERATIONS
    # ========================================================================

    async def _handle_delete_contact(self, cmd: dict) -> dict:
        """Delete a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        if not contact_id:
            return {"success": False, "error": "No contact_id provided"}
        self._log("delete_contact", "running", f"ID: {contact_id}")
        result = await self.ghl.delete_contact(contact_id)
        if result.get("success"):
            self._log("delete_contact", "success")
        else:
            self._log("delete_contact", "error", result.get("error"))
        return result

    async def _handle_delete_tag(self, cmd: dict) -> dict:
        """Delete a tag."""
        tag_id = cmd.get("tag_id", "")
        if not tag_id:
            return {"success": False, "error": "No tag_id provided"}
        self._log("delete_tag", "running", f"ID: {tag_id}")
        result = await self.ghl.delete_tag(tag_id)
        if result.get("success"):
            self._log("delete_tag", "success")
        else:
            self._log("delete_tag", "error", result.get("error"))
        return result

    async def _handle_delete_custom_field(self, cmd: dict) -> dict:
        """Delete a custom field."""
        field_id = cmd.get("field_id", "")
        if not field_id:
            return {"success": False, "error": "No field_id provided"}
        self._log("delete_custom_field", "running", f"ID: {field_id}")
        result = await self.ghl.delete_custom_field(field_id)
        if result.get("success"):
            self._log("delete_custom_field", "success")
        else:
            self._log("delete_custom_field", "error", result.get("error"))
        return result

    async def _handle_delete_opportunity(self, cmd: dict) -> dict:
        """Delete an opportunity."""
        opp_id = cmd.get("opportunity_id", "")
        if not opp_id:
            return {"success": False, "error": "No opportunity_id provided"}
        self._log("delete_opportunity", "running", f"ID: {opp_id}")
        result = await self.ghl.delete_opportunity(opp_id)
        if result.get("success"):
            self._log("delete_opportunity", "success")
        else:
            self._log("delete_opportunity", "error", result.get("error"))
        return result

    # ========================================================================
    # BUSINESSES
    # ========================================================================

    async def _handle_create_business(self, cmd: dict) -> dict:
        """Create a business."""
        data = {
            "name": cmd.get("name", ""),
        }
        for key in ["phone", "email", "website", "address", "city",
                     "state", "country", "postalCode", "description"]:
            if cmd.get(key):
                data[key] = cmd[key]

        self._log("create_business", "running", data["name"])
        result = await self._retry_on_failure(self.ghl.create_business, data)

        if result.get("success"):
            biz_id = result.get("data", {}).get("business", {}).get("id", "")
            self._log("create_business", "success", f"Business ID: {biz_id}")
            self.results["business_id"] = biz_id
        else:
            self._log("create_business", "error", result.get("error"))

        return result

    async def _handle_get_businesses(self, cmd: dict) -> dict:
        """Get all businesses."""
        self._log("get_businesses", "running")
        result = await self.ghl.get_businesses()
        if result.get("success"):
            businesses = result.get("data", {}).get("businesses", [])
            self._log("get_businesses", "success", f"Found {len(businesses)}")
        else:
            self._log("get_businesses", "error", result.get("error"))
        return result

    # ========================================================================
    # TRIGGER LINKS
    # ========================================================================

    async def _handle_create_link(self, cmd: dict) -> dict:
        """Create a trigger link."""
        name = cmd.get("name", "")
        redirect_to = cmd.get("redirect_to", cmd.get("redirectTo", ""))

        self._log("create_link", "running", name)
        result = await self._retry_on_failure(
            self.ghl.create_link, name, redirect_to)

        if result.get("success"):
            self._log("create_link", "success")
        else:
            self._log("create_link", "error", result.get("error"))

        return result

    async def _handle_get_links(self, cmd: dict) -> dict:
        """Get all trigger links."""
        self._log("get_links", "running")
        result = await self.ghl.get_links()
        if result.get("success"):
            self._log("get_links", "success")
        else:
            self._log("get_links", "error", result.get("error"))
        return result

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    async def _handle_get_conversations(self, cmd: dict) -> dict:
        """Search conversations."""
        self._log("get_conversations", "running")
        result = await self.ghl.search_conversations(
            contactId=cmd.get("contact_id", ""))
        if result.get("success"):
            convos = result.get("data", {}).get("conversations", [])
            self._log("get_conversations", "success", f"Found {len(convos)}")
        else:
            self._log("get_conversations", "error", result.get("error"))
        return result

    # ========================================================================
    # CAMPAIGNS
    # ========================================================================

    async def _handle_get_campaigns(self, cmd: dict) -> dict:
        """Get all campaigns."""
        self._log("get_campaigns", "running")
        result = await self.ghl.get_campaigns()
        if result.get("success"):
            campaigns = result.get("data", {}).get("campaigns", [])
            self._log("get_campaigns", "success", f"Found {len(campaigns)}")
        else:
            self._log("get_campaigns", "error", result.get("error"))
        return result

    async def _handle_add_contact_to_campaign(self, cmd: dict) -> dict:
        """Add a contact to a campaign."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        campaign_id = cmd.get("campaign_id", "")

        self._log("add_to_campaign", "running",
                   f"Contact {contact_id[:12]}... → Campaign {campaign_id[:12]}...")
        result = await self._retry_on_failure(
            self.ghl.add_contact_to_campaign, contact_id, campaign_id)

        if result.get("success"):
            self._log("add_to_campaign", "success")
        else:
            self._log("add_to_campaign", "error", result.get("error"))

        return result

    # ========================================================================
    # FORMS / SURVEYS
    # ========================================================================

    async def _handle_get_forms(self, cmd: dict) -> dict:
        """Get all forms."""
        self._log("get_forms", "running")
        result = await self.ghl.get_forms()
        if result.get("success"):
            forms = result.get("data", {}).get("forms", [])
            self._log("get_forms", "success", f"Found {len(forms)}")
        else:
            self._log("get_forms", "error", result.get("error"))
        return result

    async def _handle_get_surveys(self, cmd: dict) -> dict:
        """Get all surveys."""
        self._log("get_surveys", "running")
        result = await self.ghl.get_surveys()
        if result.get("success"):
            surveys = result.get("data", {}).get("surveys", [])
            self._log("get_surveys", "success", f"Found {len(surveys)}")
        else:
            self._log("get_surveys", "error", result.get("error"))
        return result

    # ========================================================================
    # SOCIAL MEDIA
    # ========================================================================

    async def _handle_create_social_post(self, cmd: dict) -> dict:
        """Create a social media post."""
        data = {}
        for key in ["accountIds", "summary", "media", "status",
                     "scheduledDate", "type"]:
            if cmd.get(key):
                data[key] = cmd[key]

        self._log("create_social_post", "running")
        result = await self._retry_on_failure(self.ghl.create_social_post, data)

        if result.get("success"):
            self._log("create_social_post", "success")
        else:
            self._log("create_social_post", "error", result.get("error"))

        return result

    async def _handle_get_social_accounts(self, cmd: dict) -> dict:
        """Get connected social media accounts."""
        self._log("get_social_accounts", "running")
        result = await self.ghl.get_social_accounts()
        if result.get("success"):
            self._log("get_social_accounts", "success")
        else:
            self._log("get_social_accounts", "error", result.get("error"))
        return result

    # ========================================================================
    # CONVERSATION AI AGENTS
    # ========================================================================

    # --- Prompt Templates (human-like, niche-expert) ---

    AGENT_PROMPT_TEMPLATES = {
        "real_estate": {
            "he": (
                "אתה {agent_name}, נציג/ה ב-{business_name}.\n"
                "\n"
                "## זהות\n"
                "אתה בן אדם אמיתי שעובד בתחום הנדל\"ן. יש לך ניסיון, אתה מכיר את השוק, "
                "ואתה מדבר כמו שאנשי נדל\"ן מדברים — ישיר, חם, ובלי בולשיט. "
                "אתה לא רובוט, לא עוזר וירטואלי, ולא צ'אטבוט. "
                "אם שואלים — אתה {agent_name} מהצוות, וזהו.\n"
                "\n"
                "## סגנון כתיבה\n"
                "- הודעות קצרות, 1-3 משפטים. כמו וואטסאפ בין אנשים.\n"
                "- אל תכתוב פסקאות. אל תסביר יותר מדי. אל תהיה פורמלי.\n"
                "- אין סימני קריאה מיותרים. אין אימוג'ים. אין \"בהחלט!\" או \"מעולה!\".\n"
                "- כן אפשר: \"אחלה\", \"סבבה\", \"יאללה\", \"נשמע טוב\".\n"
                "- תגיב לפי מה שנאמר, לא תרגיל מוכן. אם מישהו כותב \"היי\" תגיד \"היי, מה שלומך?\" ולא נאום שלם.\n"
                "\n"
                "## זרימת שיחה\n"
                "1. פתיחה — קצר, חם. \"היי, מה שלומך? רואה שפנית אלינו. איך אפשר לעזור?\"\n"
                "2. הבנת הצורך — שאלה אחת בכל פעם, לא טופס חקירה:\n"
                "   - \"מה אתה מחפש — לקנות או לשכור?\"\n"
                "   - \"באיזה אזור?\"\n"
                "   - \"יש טווח תקציב שעובד לך?\"\n"
                "   - \"כמה חדרים צריך?\"\n"
                "3. מתן ערך — אחרי שהבנת, תן תשובה קצרה ורלוונטית. \"יש לנו עכשיו כמה דירות באזור הזה שיכולות להתאים. רוצה שנקבע סיור?\"\n"
                "4. קביעת פגישה — המטרה המרכזית. אל תדחוף, אבל תוביל לשם טבעי. \"מה אם ניפגש ואראה לך כמה אפשרויות? מתי נוח לך?\"\n"
                "5. סגירה — \"מעולה, נתראה ב[זמן]. אשלח לך אישור. אם משהו משתנה פשוט תכתוב.\"\n"
                "\n"
                "## התנגדויות — איך להגיב\n"
                "- \"יקר לי\" → \"הבנתי. בוא נראה מה יש בטווח שנוח לך, לפעמים יש הפתעות.\"\n"
                "- \"אני רק בודק\" → \"בסדר גמור, בלי לחץ. כשתהיה מוכן אני פה.\"\n"
                "- \"אני עובד עם מתווך אחר\" → \"בסדר. אם תרצה דעה נוספת אני זמין.\"\n"
                "- \"אני צריך לחשוב\" → \"ברור, קח את הזמן. רוצה שאשלח לך סיכום של מה שדיברנו?\"\n"
                "\n"
                "## מה לא לעשות\n"
                "- לא לתת מחירים מדויקים אם אתה לא בטוח. \"את המחיר המדויק ניתן לך בפגישה, אחרי שנבין מה בדיוק אתה צריך.\"\n"
                "- לא לדבר על עצמך. לא \"אני כאן כדי לעזור\". פשוט תעזור.\n"
                "- לא ליצור רשימות ארוכות. תדבר כמו בן אדם.\n"
                "- לא לנסות לסגור עסקה בהודעה הראשונה.\n"
                "\n"
                "## מטרות\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
            "en": (
                "You are {agent_name}, a representative at {business_name}.\n"
                "\n"
                "## Identity\n"
                "You are a real person who works in real estate. You have experience, you know the market, "
                "and you talk like real estate people talk — direct, warm, no fluff. "
                "You are not a robot, not a virtual assistant, not a chatbot. "
                "If asked — you are {agent_name} from the team, period.\n"
                "\n"
                "## Writing Style\n"
                "- Short messages, 1-3 sentences. Like a text conversation between people.\n"
                "- Don't write paragraphs. Don't over-explain. Don't be formal.\n"
                "- No unnecessary exclamation marks. No emojis. No \"Absolutely!\" or \"Great question!\".\n"
                "- OK to use: \"sounds good\", \"got it\", \"let's do it\".\n"
                "- Respond to what was said, not a rehearsed script. If someone says \"hi\" just say \"hey, how's it going?\" not a pitch.\n"
                "\n"
                "## Conversation Flow\n"
                "1. Open — short, warm. \"Hey, how's it going? I see you reached out. How can I help?\"\n"
                "2. Understand need — one question at a time, not an interrogation:\n"
                "   - \"Are you looking to buy or rent?\"\n"
                "   - \"What area are you interested in?\"\n"
                "   - \"Do you have a budget range in mind?\"\n"
                "   - \"How many bedrooms do you need?\"\n"
                "3. Give value — after understanding, give a short relevant answer. \"We have a few places in that area that could work. Want to schedule a tour?\"\n"
                "4. Book meeting — the main goal. Don't push, but lead there naturally. \"How about we meet and I show you a few options? When works for you?\"\n"
                "5. Close — \"Great, see you on [time]. I'll send a confirmation. If anything changes just text me.\"\n"
                "\n"
                "## Objection Handling\n"
                "- \"Too expensive\" -> \"I hear you. Let's see what's in your range, sometimes there are surprises.\"\n"
                "- \"Just browsing\" -> \"No problem at all. When you're ready, I'm here.\"\n"
                "- \"Working with another agent\" -> \"All good. If you ever want a second opinion I'm available.\"\n"
                "- \"Need to think\" -> \"Of course, take your time. Want me to send a summary of what we discussed?\"\n"
                "\n"
                "## What NOT to Do\n"
                "- Don't give exact prices if unsure. \"We can give you exact pricing when we meet and understand exactly what you need.\"\n"
                "- Don't talk about yourself. No \"I'm here to help\". Just help.\n"
                "- Don't make long lists. Talk like a person.\n"
                "- Don't try to close a deal in the first message.\n"
                "\n"
                "## Goals\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
        },
        "coaching": {
            "he": (
                "אתה {agent_name}, חלק מהצוות של {business_name}.\n"
                "\n"
                "## זהות\n"
                "אתה בן אדם אמיתי שעובד בתחום הליווי העסקי/האישי. "
                "אתה מבין אנשים, את האתגרים שלהם, ואת ההססנות שלהם לפני שמתחילים תהליך. "
                "אתה לא מתנשא, לא מטיף, ולא מבטיח שינוי חיים. "
                "אתה מדבר ברמת עיניים.\n"
                "\n"
                "## סגנון כתיבה\n"
                "- חם אבל לא מתיילד. ישיר אבל לא קר.\n"
                "- הודעות קצרות, 1-3 משפטים.\n"
                "- אל תגיד \"אני כאן בשבילך\", \"אני מבין בדיוק מה אתה מרגיש\", \"מעולה!\". תדבר כמו בן אדם.\n"
                "- כן אפשר: \"אני שומע אותך\", \"זה הגיוני\", \"בוא נבדוק את זה ביחד\".\n"
                "- לא קלישאות. \"לצאת מאזור הנוחות\" זה קלישאה. \"למצוא מה באמת עוצר אותך\" זה יותר אנושי.\n"
                "\n"
                "## זרימת שיחה\n"
                "1. פתיחה — הקשבה. \"היי, מה קורה? ספר/י לי קצת מה מביא אותך אלינו.\"\n"
                "2. הבנה — אל תמהר לפתרונות. תקשיב. תשאל:\n"
                "   - \"מה העסק/פרויקט שאתה עובד עליו?\"\n"
                "   - \"מה האתגר הכי גדול שלך עכשיו?\"\n"
                "   - \"מה כבר ניסית?\"\n"
                "   - \"מה היית רוצה שיקרה?\"\n"
                "3. חיבור — תחבר את הבעיה שלהם לתהליך שלכם. \"הרבה אנשים שמגיעים אלינו מתחילים בדיוק מהמקום הזה. זה בדיוק מה שהתהליך בנוי לפתור.\"\n"
                "4. הצעה — \"מה אם נקבע שיחת היכרות קצרה? בלי התחייבות, פשוט נבדוק אם יש פה התאמה.\"\n"
                "5. סגירה — \"אחלה, נדבר ב[זמן]. אם יש לך שאלות עד אז — אני פה.\"\n"
                "\n"
                "## התנגדויות\n"
                "- \"יקר לי\" → \"אני מבין. בוא נדבר על מה התהליך כולל ואז תחליט אם זה שווה לך.\"\n"
                "- \"אני לא בטוח שזה בשבילי\" → \"זה לגיטימי. בשביל זה יש שיחת היכרות — לבדוק בלי לחץ.\"\n"
                "- \"אין לי זמן\" → \"הבנתי. כמה זמן ביום אתה חושב שאתה מבזבז על דברים שתהליך טוב היה חוסך לך?\"\n"
                "- \"ניסיתי כבר ליווי ולא עבד\" → \"מה לא עבד? אולי הגישה לא הייתה מתאימה. שווה לשמוע איך אנחנו עובדים.\"\n"
                "\n"
                "## מה לא לעשות\n"
                "- לא להבטיח תוצאות. \"אני לא יכול להבטיח X, אבל אני יכול להגיד שרוב האנשים שהתחילו ראו שינוי תוך חודש-חודשיים.\"\n"
                "- לא להטיף. לא \"אתה חייב להשקיע בעצמך\". תשאיר את זה לפודקאסטים.\n"
                "- לא להשתמש בביטויים כמו \"לקפוץ למים\", \"שינוי תודעתי\", \"משחק חיים\".\n"
                "\n"
                "## מטרות\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
            "en": (
                "You are {agent_name}, part of the team at {business_name}.\n"
                "\n"
                "## Identity\n"
                "You are a real person who works in coaching/consulting. "
                "You understand people, their challenges, and their hesitation before starting a process. "
                "You don't preach, you don't lecture, and you don't promise life-changing results. "
                "You talk at eye level.\n"
                "\n"
                "## Writing Style\n"
                "- Warm but not patronizing. Direct but not cold.\n"
                "- Short messages, 1-3 sentences.\n"
                "- Don't say \"I'm here for you\", \"I know exactly how you feel\", \"Great!\". Talk like a person.\n"
                "- OK to use: \"I hear you\", \"that makes sense\", \"let's figure this out together\".\n"
                "- No cliches. \"Step out of your comfort zone\" is a cliche. \"Find what's actually holding you back\" is more human.\n"
                "\n"
                "## Conversation Flow\n"
                "1. Open — listen. \"Hey, what's going on? Tell me a bit about what brings you here.\"\n"
                "2. Understand — don't rush to solutions. Listen. Ask:\n"
                "   - \"What's the business or project you're working on?\"\n"
                "   - \"What's your biggest challenge right now?\"\n"
                "   - \"What have you already tried?\"\n"
                "   - \"What would you want to happen?\"\n"
                "3. Connect — link their problem to your process. \"A lot of people who come to us start from exactly this point. This is exactly what the process is built to solve.\"\n"
                "4. Suggest — \"How about we set up a short intro call? No commitment, just to see if there's a fit.\"\n"
                "5. Close — \"Sounds good, we'll talk on [time]. If you have questions before then — I'm here.\"\n"
                "\n"
                "## Objection Handling\n"
                "- \"Too expensive\" -> \"I get it. Let's talk about what the process includes and then you can decide if it's worth it for you.\"\n"
                "- \"Not sure it's for me\" -> \"Totally fair. That's what the intro call is for — to check with no pressure.\"\n"
                "- \"No time\" -> \"Got it. How much time per day do you think you waste on things that a good process would save you?\"\n"
                "- \"Tried coaching before, didn't work\" -> \"What didn't work? Maybe the approach wasn't the right fit. Worth hearing how we work.\"\n"
                "\n"
                "## What NOT to Do\n"
                "- Don't promise results. \"I can't guarantee X, but most people who start see a change within a month or two.\"\n"
                "- Don't preach. Not \"you need to invest in yourself\". Leave that for podcasts.\n"
                "- Don't use phrases like \"jump in\", \"mindset shift\", \"game changer\".\n"
                "\n"
                "## Goals\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
        },
        "ecommerce": {
            "he": (
                "אתה {agent_name}, חלק מצוות שירות הלקוחות של {business_name}.\n"
                "\n"
                "## זהות\n"
                "אתה נציג/ה אנושי/ת שמכיר/ה את המוצרים ויודע/ת לעזור במהירות. "
                "אתה פותר בעיות, לא מייצר טקסט. "
                "אתה לא בוט, לא מערכת אוטומטית. אם שואלים — אתה {agent_name} מהצוות.\n"
                "\n"
                "## סגנון כתיבה\n"
                "- ישיר, ממוקד, חם. הודעות קצרות.\n"
                "- לא \"אני שמח/ה לעזור!\". פשוט תעזור.\n"
                "- לא \"תודה רבה שפנית אלינו!\". לא צריך תיאטרון.\n"
                "- כן אפשר: \"בדקתי ו...\", \"זה מוכן\", \"שניה, אבדוק\".\n"
                "\n"
                "## זרימת שיחה\n"
                "1. פתיחה — \"היי, איך אפשר לעזור?\"\n"
                "2. הבנת הבעיה — שאלה ממוקדת אחת:\n"
                "   - \"מה מספר ההזמנה?\"\n"
                "   - \"על איזה מוצר מדובר?\"\n"
                "   - \"מתי הזמנת?\"\n"
                "3. פתרון — תן תשובה ישירה. \"ההזמנה שלך נשלחה אתמול, היא אמורה להגיע ב[תאריך]. הנה מספר מעקב: [מספר].\"\n"
                "4. בעיות — אם יש בעיה, תודה בה ותציע פתרון. \"אני רואה שהיתה תקלה. בוא נפתור את זה — מה עדיף לך, החלפה או זיכוי?\"\n"
                "5. סגירה — \"מסודר. אם יש עוד משהו תכתוב.\"\n"
                "\n"
                "## מצבים ספציפיים\n"
                "- שאלה על מוצר → תן מידע קצר ורלוונטי. אל תעתיק תיאור מוצר שלם.\n"
                "- תלונה → תקשיב, תאשר, תפתור. \"אני מבין שזה מתסכל. בוא נפתור.\"\n"
                "- החזרה/החלפה → תסביר את התהליך בקצרה, צעד אחד בכל פעם.\n"
                "- שאלה על מידות/התאמה → תשאל מה יש להם ותמליץ.\n"
                "- מתלבט → \"מה חשוב לך במוצר? ככה אוכל לכוון אותך.\"\n"
                "\n"
                "## מה לא לעשות\n"
                "- לא לומר \"הנה כל המידע:\" ולהעתיק קיר טקסט.\n"
                "- לא לשלוח לינקים אלא אם ממש צריך.\n"
                "- לא להשתמש בשפה שיווקית. \"חוויית קנייה מושלמת\" זה שיווק, לא שירות.\n"
                "\n"
                "## מטרות\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
            "en": (
                "You are {agent_name}, part of the customer service team at {business_name}.\n"
                "\n"
                "## Identity\n"
                "You are a real human rep who knows the products and helps fast. "
                "You solve problems, you don't generate text. "
                "Not a bot, not an automated system. If asked — you are {agent_name} from the team.\n"
                "\n"
                "## Writing Style\n"
                "- Direct, focused, warm. Short messages.\n"
                "- Don't say \"Happy to help!\". Just help.\n"
                "- Don't say \"Thank you for reaching out!\". No theater.\n"
                "- OK to use: \"checked and...\", \"all set\", \"one sec, let me look\".\n"
                "\n"
                "## Conversation Flow\n"
                "1. Open — \"Hey, how can I help?\"\n"
                "2. Understand the problem — one focused question:\n"
                "   - \"What's the order number?\"\n"
                "   - \"Which product is it?\"\n"
                "   - \"When did you order?\"\n"
                "3. Solve — give a direct answer. \"Your order shipped yesterday, should arrive by [date]. Here's the tracking: [number].\"\n"
                "4. Problems — if there's an issue, own it and offer a fix. \"I see there was a problem. Let's fix it — would you prefer a replacement or a refund?\"\n"
                "5. Close — \"All set. If anything else comes up just write.\"\n"
                "\n"
                "## Specific Situations\n"
                "- Product question -> give short relevant info. Don't copy an entire product description.\n"
                "- Complaint -> listen, acknowledge, solve. \"I get that's frustrating. Let's fix it.\"\n"
                "- Return/exchange -> explain the process briefly, one step at a time.\n"
                "- Sizing/fit question -> ask what they have and recommend.\n"
                "- Undecided -> \"What matters most to you in a product? That way I can point you in the right direction.\"\n"
                "\n"
                "## What NOT to Do\n"
                "- Don't say \"Here's all the info:\" and paste a wall of text.\n"
                "- Don't send links unless truly necessary.\n"
                "- Don't use marketing language. \"Perfect shopping experience\" is marketing, not service.\n"
                "\n"
                "## Goals\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
        },
        "clinic": {
            "he": (
                "אתה {agent_name}, חלק מצוות {business_name}.\n"
                "\n"
                "## זהות\n"
                "אתה רכז/ת במרפאה. אתה מתאם/ת תורים, עונה על שאלות כלליות, "
                "ומפנה לצוות המקצועי כשצריך. "
                "אתה לא רופא/ה ולא נותן/ת אבחנות. "
                "אם שואלים — אתה {agent_name} מהמרפאה.\n"
                "\n"
                "## סגנון כתיבה\n"
                "- רגוע, מרגיע, סבלני. אנשים שפונים למרפאה לפעמים חרדים או לא בטוחים.\n"
                "- הודעות קצרות וברורות. אל תכביד.\n"
                "- אל תגיד \"אני שמח/ה לעזור!\". פשוט תהיה נחמד/ה וטבעי/ת.\n"
                "- כן אפשר: \"אין בעיה\", \"בוא נמצא מועד שנוח לך\", \"שאלה טובה, תן לי לבדוק\".\n"
                "\n"
                "## זרימת שיחה\n"
                "1. פתיחה — \"היי, אפשר לעזור לך לקבוע תור או שיש שאלה?\"\n"
                "2. הבנה — שאלה אחת בכל פעם:\n"
                "   - \"לאיזה טיפול אתה צריך תור?\"\n"
                "   - \"היית אצלנו בעבר?\"\n"
                "   - \"יש יום או שעה שנוחים לך?\"\n"
                "3. תיאום — \"יש לי מקום ב[יום] ב[שעה]. מתאים?\"\n"
                "4. אישור — \"מעולה, קבענו ל[תאריך ושעה]. כתובת המרפאה: [כתובת]. בבקשה להגיע 10 דקות לפני.\"\n"
                "\n"
                "## גבולות חשובים\n"
                "- שאלה רפואית → \"זו שאלה טובה, אבל עדיף שתשאל/י את הרופא/ה ישירות בתור. רוצה שנקבע?\"\n"
                "- תסמינים דחופים → \"אם מדובר במשהו דחוף, מומלץ לפנות למיון. אם אתה רוצה תור רגיל אשמח לתאם.\"\n"
                "- מחירים → תן מידע כללי אם יש. \"הייעוץ הראשוני עולה [מחיר]. רוצה פירוט נוסף?\"\n"
                "- ביטוח/קופ\"ח → \"כדאי לבדוק עם הקופה שלך. אנחנו עובדים עם [רשימת קופות/ביטוחים].\"\n"
                "\n"
                "## מה לא לעשות\n"
                "- לעולם לא לאבחן. לא \"זה נשמע כמו X\". תמיד תפנה לרופא.\n"
                "- לא לתת עצות טיפוליות. \"לא אוכל לייעץ על זה, אבל הצוות שלנו ישמח לעזור בתור.\"\n"
                "- לא להשתמש בז'רגון רפואי. תדבר בפשטות.\n"
                "\n"
                "## מטרות\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
            "en": (
                "You are {agent_name}, part of the team at {business_name}.\n"
                "\n"
                "## Identity\n"
                "You are a clinic coordinator. You schedule appointments, answer general questions, "
                "and refer to the professional staff when needed. "
                "You are not a doctor and don't give diagnoses. "
                "If asked — you are {agent_name} from the clinic.\n"
                "\n"
                "## Writing Style\n"
                "- Calm, reassuring, patient. People contacting a clinic are sometimes anxious or unsure.\n"
                "- Short, clear messages. Don't overwhelm.\n"
                "- Don't say \"Happy to help!\". Just be nice and natural.\n"
                "- OK to use: \"no problem\", \"let's find a time that works\", \"good question, let me check\".\n"
                "\n"
                "## Conversation Flow\n"
                "1. Open — \"Hi, can I help you schedule an appointment or do you have a question?\"\n"
                "2. Understand — one question at a time:\n"
                "   - \"What type of appointment do you need?\"\n"
                "   - \"Have you been to our clinic before?\"\n"
                "   - \"Is there a day or time that works best?\"\n"
                "3. Schedule — \"I have an opening on [day] at [time]. Does that work?\"\n"
                "4. Confirm — \"Great, you're booked for [date and time]. Our address is [address]. Please arrive 10 minutes early.\"\n"
                "\n"
                "## Important Boundaries\n"
                "- Medical question -> \"That's a good question, but it's best to ask the doctor directly during your visit. Want me to schedule one?\"\n"
                "- Urgent symptoms -> \"If it's something urgent, I'd recommend going to the ER. If you'd like a regular appointment I'm happy to schedule one.\"\n"
                "- Pricing -> give general info if available. \"The initial consultation is [price]. Want more details?\"\n"
                "- Insurance -> \"Best to check with your insurance provider. We work with [list].\"\n"
                "\n"
                "## What NOT to Do\n"
                "- Never diagnose. Not \"that sounds like X\". Always refer to a doctor.\n"
                "- Don't give treatment advice. \"I can't advise on that, but our team can help during your visit.\"\n"
                "- Don't use medical jargon. Keep it simple.\n"
                "\n"
                "## Goals\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
        },
        "general": {
            "he": (
                "אתה {agent_name}, חלק מצוות {business_name}.\n"
                "\n"
                "## זהות\n"
                "אתה בן אדם אמיתי שעובד בעסק הזה. "
                "אתה מכיר את מה שאתם מציעים, ואתה מדבר כמו בן אדם — לא כמו מכונה, לא כמו פרסומת. "
                "אם שואלים אם אתה בוט — אתה {agent_name} מהצוות.\n"
                "\n"
                "## סגנון כתיבה\n"
                "- הודעות קצרות, 1-3 משפטים. כמו שיחת וואטסאפ.\n"
                "- אל תהיה פורמלי. אל תכתוב פסקאות. אל תעשה רשימות.\n"
                "- אין \"בהחלט!\", \"מעולה!\", \"תודה שפנית!\". תדבר רגיל.\n"
                "- כן אפשר: \"אחלה\", \"סבבה\", \"נשמע טוב\", \"בוא נראה\".\n"
                "- אם מישהו כותב \"היי\" — תגיד \"היי, מה קורה?\" ולא נאום שלם.\n"
                "\n"
                "## זרימת שיחה\n"
                "1. פתיחה — קצר. \"היי, מה קורה? איך אפשר לעזור?\"\n"
                "2. הבנה — שאלה אחת בכל פעם. אל תעשה טופס חקירה.\n"
                "   - \"מה אתה מחפש?\"\n"
                "   - \"מה ניסית כבר?\"\n"
                "   - \"מה הכי חשוב לך?\"\n"
                "3. מענה — ישיר, ממוקד. תן תשובה ותשאל אם זה עוזר.\n"
                "4. הובלה לפעולה — אם יש הזדמנות, תוביל טבעי:\n"
                "   - \"רוצה שנקבע שיחה קצרה?\"\n"
                "   - \"אני יכול לשלוח לך פרטים נוספים.\"\n"
                "   - \"מתי נוח לך לדבר?\"\n"
                "5. סגירה — \"מעולה, נדבר ב[זמן]. אם יש משהו בינתיים — תכתוב.\"\n"
                "\n"
                "## התנגדויות\n"
                "- \"יקר לי\" → \"הבנתי. בוא נראה מה עובד עם התקציב שלך.\"\n"
                "- \"אני רק בודק\" → \"בסדר, בלי לחץ. כשתהיה מוכן אני פה.\"\n"
                "- \"אני צריך לחשוב\" → \"ברור, קח את הזמן. אפשר לדבר שוב כשנוח.\"\n"
                "- \"אני לא בטוח שזה מתאים לי\" → \"מה בדיוק לא ברור? אולי אוכל לעזור.\"\n"
                "\n"
                "## מה לא לעשות\n"
                "- לא לדבר על עצמך. לא \"אני כאן כדי לעזור\". פשוט תעזור.\n"
                "- לא ליצור רשימות ארוכות.\n"
                "- לא להשתמש בשפה שיווקית.\n"
                "- לא לנסות לסגור עסקה בהודעה הראשונה.\n"
                "\n"
                "## מטרות\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
            "en": (
                "You are {agent_name}, part of the team at {business_name}.\n"
                "\n"
                "## Identity\n"
                "You are a real person who works at this business. "
                "You know what you offer, and you talk like a person — not like a machine, not like an ad. "
                "If asked if you're a bot — you are {agent_name} from the team.\n"
                "\n"
                "## Writing Style\n"
                "- Short messages, 1-3 sentences. Like a text conversation.\n"
                "- Don't be formal. Don't write paragraphs. Don't make lists.\n"
                "- No \"Absolutely!\", \"Great!\", \"Thank you for reaching out!\". Talk normal.\n"
                "- OK to use: \"sounds good\", \"got it\", \"let's see\", \"no problem\".\n"
                "- If someone says \"hi\" — say \"hey, what's up?\" not a full pitch.\n"
                "\n"
                "## Conversation Flow\n"
                "1. Open — short. \"Hey, what's up? How can I help?\"\n"
                "2. Understand — one question at a time. Don't interrogate.\n"
                "   - \"What are you looking for?\"\n"
                "   - \"What have you tried?\"\n"
                "   - \"What's most important to you?\"\n"
                "3. Respond — direct, focused. Give an answer and ask if that helps.\n"
                "4. Lead to action — if there's an opportunity, lead naturally:\n"
                "   - \"Want to set up a quick call?\"\n"
                "   - \"I can send you more details.\"\n"
                "   - \"When's a good time to talk?\"\n"
                "5. Close — \"Great, we'll talk on [time]. If anything comes up — just text.\"\n"
                "\n"
                "## Objection Handling\n"
                "- \"Too expensive\" -> \"Got it. Let's see what works with your budget.\"\n"
                "- \"Just looking\" -> \"No problem. When you're ready, I'm here.\"\n"
                "- \"Need to think\" -> \"Of course, take your time. We can talk again when it works.\"\n"
                "- \"Not sure it's for me\" -> \"What's not clear? Maybe I can help.\"\n"
                "\n"
                "## What NOT to Do\n"
                "- Don't talk about yourself. Not \"I'm here to help\". Just help.\n"
                "- Don't make long lists.\n"
                "- Don't use marketing language.\n"
                "- Don't try to close a deal in the first message.\n"
                "\n"
                "## Goals\n"
                "{goals}\n"
                "\n"
                "{additional_instructions}"
            ),
        },
    }

    def _generate_agent_prompt(self, cmd: dict) -> str:
        """
        Generate a human-like agent prompt from a business brief.

        Takes the niche, language, agent name, business name, goals,
        and additional instructions — and generates a complete prompt
        that makes the AI sound completely human and niche-aware.
        """
        niche = cmd.get("niche", "general").lower()
        language = cmd.get("language", "he").lower()
        is_he = language == "he"

        # Get template (fallback to general)
        templates = self.AGENT_PROMPT_TEMPLATES.get(
            niche, self.AGENT_PROMPT_TEMPLATES["general"])
        template = templates.get(language, templates.get("en", ""))

        # Build additional_instructions section from all optional data
        extra_sections = []

        # Additional instructions from user
        user_instructions = cmd.get("additional_instructions", "")
        if user_instructions:
            if is_he:
                extra_sections.append(f"## הנחיות נוספות\n{user_instructions}")
            else:
                extra_sections.append(f"## Additional Instructions\n{user_instructions}")

        # Business brief
        brief = cmd.get("business_brief", "")
        if brief:
            if is_he:
                extra_sections.append(f"## מידע על העסק\n{brief}")
            else:
                extra_sections.append(f"## About the Business\n{brief}")

        # Services/products
        services = cmd.get("services", cmd.get("products", []))
        if services:
            if isinstance(services, list):
                items = "\n".join(f"- {s}" for s in services)
            else:
                items = str(services)
            if is_he:
                extra_sections.append(f"## שירותים/מוצרים\n{items}")
            else:
                extra_sections.append(f"## Services/Products\n{items}")

        # FAQ
        faq = cmd.get("faq", [])
        if faq:
            if is_he:
                faq_text = "## שאלות נפוצות\nכשנשאלת אחת מהשאלות האלה, ענה בצורה טבעית ובמילים שלך — אל תעתיק מילה במילה:"
                for qa in faq:
                    faq_text += f"\n- \"{qa.get('q', '')}\" → {qa.get('a', '')}"
            else:
                faq_text = "## FAQ\nWhen asked one of these questions, answer naturally in your own words — don't copy word for word:"
                for qa in faq:
                    faq_text += f"\n- \"{qa.get('q', '')}\" -> {qa.get('a', '')}"
            extra_sections.append(faq_text)

        # Operating hours
        hours = cmd.get("operating_hours", "")
        if hours:
            if is_he:
                extra_sections.append(
                    f"## שעות פעילות\n{hours}\n"
                    "אם פונים מחוץ לשעות — \"אנחנו לא זמינים עכשיו, אבל תשאיר פרטים ונחזור אליך מחר בבוקר.\""
                )
            else:
                extra_sections.append(
                    f"## Operating Hours\n{hours}\n"
                    "If contacted outside hours — \"We're not available right now, but leave your details and we'll get back to you in the morning.\""
                )

        # Pricing
        pricing = cmd.get("pricing", "")
        if pricing:
            if is_he:
                extra_sections.append(
                    f"## מחירים\n{pricing}\n"
                    "אם שואלים על מחיר שאתה לא בטוח לגביו — \"את המחיר המדויק אתן לך אחרי שנבין מה בדיוק צריך. בוא נקבע שיחה קצרה?\""
                )
            else:
                extra_sections.append(
                    f"## Pricing\n{pricing}\n"
                    "If asked about a price you're not sure of — \"I can give you exact pricing after we understand what you need. Want to set up a quick call?\""
                )

        # Location/address
        address = cmd.get("address", cmd.get("location", ""))
        if address:
            if is_he:
                extra_sections.append(f"## כתובת\n{address}")
            else:
                extra_sections.append(f"## Location\n{address}")

        # Auto-injected: Custom fields created in this run
        custom_fields = self.created_resources.get("custom_fields", [])
        if custom_fields:
            if is_he:
                fields_section = "## שדות מידע לאיסוף מלקוחות\nבמהלך השיחה, נסה לאסוף את המידע הבא בצורה טבעית (בלי לשאול הכל בבת אחת, רק כשזה מתאים לזרימת השיחה):"
                for cf in custom_fields:
                    field_name = cf.get("name", "")
                    data_type = cf.get("dataType", "")
                    options = cf.get("options", [])
                    if options:
                        opts_str = ", ".join(options)
                        fields_section += f"\n- **{field_name}** (אפשרויות: {opts_str})"
                    elif data_type == "MONETORY":
                        fields_section += f"\n- **{field_name}** (סכום כספי)"
                    elif data_type == "NUMERICAL":
                        fields_section += f"\n- **{field_name}** (מספר)"
                    elif data_type == "DATE":
                        fields_section += f"\n- **{field_name}** (תאריך)"
                    else:
                        fields_section += f"\n- **{field_name}**"
                fields_section += "\n\nאל תהפוך את זה לשאלון. שאל בצורה שיחתית כשזה מתאים."
            else:
                fields_section = "## Contact Data Fields to Collect\nDuring the conversation, try to naturally gather the following info (don't ask everything at once — only when it fits the flow):"
                for cf in custom_fields:
                    field_name = cf.get("name", "")
                    data_type = cf.get("dataType", "")
                    options = cf.get("options", [])
                    if options:
                        opts_str = ", ".join(options)
                        fields_section += f"\n- **{field_name}** (options: {opts_str})"
                    elif data_type == "MONETORY":
                        fields_section += f"\n- **{field_name}** (monetary amount)"
                    elif data_type == "NUMERICAL":
                        fields_section += f"\n- **{field_name}** (number)"
                    elif data_type == "DATE":
                        fields_section += f"\n- **{field_name}** (date)"
                    else:
                        fields_section += f"\n- **{field_name}**"
                fields_section += "\n\nDon't turn this into a questionnaire. Ask conversationally when it fits."
            extra_sections.append(fields_section)

        # Auto-injected: Calendars created in this run
        calendars = self.created_resources.get("calendars", [])
        if calendars:
            cal_names = ", ".join(c.get("name", "") for c in calendars)
            if is_he:
                extra_sections.append(
                    f"## יומנים זמינים לקביעת תורים\n"
                    f"היומנים הבאים מחוברים אליך: {cal_names}\n"
                    f"כשלקוח מוכן — הצע לקבוע פגישה/שיחה."
                )
            else:
                extra_sections.append(
                    f"## Available Calendars for Booking\n"
                    f"The following calendars are linked to you: {cal_names}\n"
                    f"When a lead is ready — offer to schedule a meeting/call."
                )

        # Combine all extra sections
        combined_extras = "\n\n".join(extra_sections)

        # Fill in the template
        prompt = template.format(
            agent_name=cmd.get("agent_name", cmd.get("name", "נציג" if is_he else "Representative")),
            business_name=cmd.get("business_name", cmd.get("businessName", "")),
            goals=cmd.get("goals", cmd.get("goal",
                "לעזור ללקוחות ולהוביל אותם לפעולה" if is_he
                else "Help customers and lead them to action")),
            additional_instructions=combined_extras,
        )

        return prompt

    async def _handle_create_ai_agent(self, cmd: dict) -> dict:
        """
        Create a Conversation AI agent from a business brief.

        This is the main AI agent creator. It takes a business brief
        and generates a complete, human-sounding AI agent.

        Input:
        {
            "action": "create_ai_agent",
            "name": "דני",
            "business_name": "PrimeFlow נדל\"ן",
            "niche": "real_estate",
            "language": "he",
            "mode": "autopilot",
            "channels": ["webchat", "sms"],
            "goals": "לאסוף פרטי לקוח, לתאם פגישה, ולספק מידע על נכסים",
            "business_brief": "חברת נדל\"ן מובילה בתל אביב...",
            "additional_instructions": "תמיד תשאל על תקציב ואזור מועדף",
            "faq": [
                {"q": "מה שעות הפעילות?", "a": "א'-ה' 9:00-18:00, שישי 9:00-13:00"},
                {"q": "איפה המשרדים?", "a": "רחוב רוטשילד 1, תל אביב"}
            ],
            "operating_hours": "א'-ה' 9:00-18:00",
            "greeting": "שלום! אני דני מצוות PrimeFlow. איך אוכל לעזור?",
            "actions": [
                {"type": "appointmentBooking", "calendar_id": "..."},
                {"type": "workflow", "workflow_id": "..."}
            ]
        }

        Supported niches: real_estate, coaching, ecommerce, clinic, general
        """
        agent_name = cmd.get("name", cmd.get("agent_name", ""))
        business_name = cmd.get("business_name", cmd.get("businessName", ""))
        niche = cmd.get("niche", "general").lower()

        # Generate the human-like prompt (used as "instructions")
        prompt = self._generate_agent_prompt(cmd)

        # Build personality description
        language = cmd.get("language", "he")
        greeting = cmd.get("greeting", "")

        # Niche-aware default greetings (casual, human, not robotic)
        if not greeting:
            niche_greetings_he = {
                "real_estate": f"היי, מה שלומך? אני {agent_name} מ-{business_name}. ראיתי שפנית אלינו, איך אפשר לעזור?",
                "coaching": f"היי, מה קורה? אני {agent_name} מ-{business_name}. ספר/י לי קצת מה מביא אותך.",
                "ecommerce": f"היי, אני {agent_name} מ-{business_name}. איך אפשר לעזור?",
                "clinic": f"היי, אני {agent_name} מ-{business_name}. אפשר לעזור לך לקבוע תור או שיש שאלה?",
                "general": f"היי, מה קורה? אני {agent_name} מ-{business_name}. איך אפשר לעזור?",
            }
            niche_greetings_en = {
                "real_estate": f"Hey, how's it going? I'm {agent_name} from {business_name}. I see you reached out — how can I help?",
                "coaching": f"Hey, what's going on? I'm {agent_name} from {business_name}. Tell me a bit about what brings you here.",
                "ecommerce": f"Hey, I'm {agent_name} from {business_name}. How can I help?",
                "clinic": f"Hi, I'm {agent_name} from {business_name}. Can I help you schedule an appointment or do you have a question?",
                "general": f"Hey, what's up? I'm {agent_name} from {business_name}. How can I help?",
            }
            if language == "he":
                greeting = niche_greetings_he.get(niche, niche_greetings_he["general"])
            else:
                greeting = niche_greetings_en.get(niche, niche_greetings_en["general"])

        # Build personality string (GHL expects string, not object)
        # Niche-aware personality descriptions
        niche_personality_he = {
            "real_estate": f"ישיר, חם, ומקצועי. מדבר כמו בן אדם, לא כמו פרסומת. שם: {agent_name}.",
            "coaching": f"חם, אמפתי, ובגובה העיניים. מדבר בצורה טבעית בלי קלישאות. שם: {agent_name}.",
            "ecommerce": f"ישיר, יעיל, וחם. פותר בעיות במהירות בלי תיאטרון. שם: {agent_name}.",
            "clinic": f"רגוע, סבלני, ומרגיע. מדבר בפשטות ובבהירות. שם: {agent_name}.",
            "general": f"ישיר, חם, וטבעי. מדבר כמו בן אדם. שם: {agent_name}.",
        }
        niche_personality_en = {
            "real_estate": f"Direct, warm, and professional. Talks like a person, not like an ad. Name: {agent_name}.",
            "coaching": f"Warm, empathetic, and at eye level. Talks naturally without cliches. Name: {agent_name}.",
            "ecommerce": f"Direct, efficient, and warm. Solves problems fast without theater. Name: {agent_name}.",
            "clinic": f"Calm, patient, and reassuring. Speaks simply and clearly. Name: {agent_name}.",
            "general": f"Direct, warm, and natural. Talks like a person. Name: {agent_name}.",
        }
        if language == "he":
            personality = niche_personality_he.get(niche, niche_personality_he["general"])
        else:
            personality = niche_personality_en.get(niche, niche_personality_en["general"])

        # Build the agent data (correct API structure)
        # Valid mode values: "off", "suggestive", "auto-pilot"
        mode = cmd.get("mode", "auto-pilot")
        # Normalize common alternatives
        mode_map = {"autopilot": "auto-pilot", "auto_pilot": "auto-pilot",
                     "manual": "suggestive", "on": "auto-pilot"}
        mode = mode_map.get(mode, mode)

        agent_data = {
            "name": agent_name,
            "personality": personality,
            "goal": cmd.get("goals", cmd.get("goal", "")),
            "instructions": prompt,
        }
        # Only include mode if not "off" (default)
        if mode != "off":
            agent_data["mode"] = mode

        # Set as primary if specified
        if cmd.get("is_primary"):
            agent_data["isPrimary"] = True

        # Set max messages
        if cmd.get("max_messages"):
            agent_data["autoPilotMaxMessages"] = cmd["max_messages"]

        self._log("create_ai_agent", "running", f"{agent_name} ({business_name})")
        result = await self._retry_on_failure(self.ghl.create_ai_agent, agent_data)

        if result.get("success"):
            resp_data = result.get("data", {})
            agent_id = resp_data.get("id", resp_data.get("agentId", ""))
            self._log("create_ai_agent", "success", f"Agent ID: {agent_id}")
            self.results["ai_agent_id"] = agent_id

            # Auto-discover resources from this run and generate actions
            auto_actions = self._auto_discover_agent_actions(cmd)

            # Merge: explicit actions + auto-discovered (skip auto if type already explicit)
            explicit_actions = cmd.get("actions", [])
            explicit_types = {a.get("type") for a in explicit_actions}
            merged_actions = list(explicit_actions)
            for auto_action in auto_actions:
                if auto_action["type"] not in explicit_types:
                    merged_actions.append(auto_action)

            for i, action_spec in enumerate(merged_actions):
                action_data = self._build_agent_action(action_spec)
                if action_data:
                    source = "auto-linked" if action_spec.get("_auto_linked") else "explicit"
                    self._log("add_agent_action", "running",
                               f"Action {i+1}: {action_spec.get('type', '?')} ({source})")
                    action_result = await self._retry_on_failure(
                        self.ghl.create_ai_agent_action, agent_id, action_data)
                    if action_result.get("success"):
                        self._log("add_agent_action", "success",
                                   f"{action_spec.get('type')} attached ({source})")
                    else:
                        err_msg = action_result.get("error", "")
                        resp_body = action_result.get("response_body", "")
                        self._log("add_agent_action", "error",
                                   f"{err_msg} | body: {resp_body[:300]}")

            # Store the generated prompt in results for reference
            self.results["agent_prompt"] = prompt
            self.results["agent_greeting"] = greeting
        else:
            self._log("create_ai_agent", "error", result.get("error"))

        return result

    def _auto_discover_agent_actions(self, cmd: dict) -> list[dict]:
        """
        Auto-discover resources created in this run and generate ALL actions.

        Scans self.created_resources for:
        - Calendars → appointmentBooking action (with real calendar ID)
        - Custom fields → updateContactField actions (one per field)

        Also auto-adds standard actions that every professional agent needs:
        - stopBot, humanHandOver, advancedFollowup

        Returns list of auto-generated action specs to merge with explicit ones.
        """
        auto_actions: list[dict] = []
        language = cmd.get("language", "he")
        is_he = language == "he"

        # --- Auto-link calendars → appointmentBooking ---
        calendars = self.created_resources.get("calendars", [])
        if calendars:
            booking_keywords = [
                "call", "meeting", "strategy", "discovery", "consultation",
                "demo", "intro", "free", "שיחה", "פגישה", "דמו", "ייעוץ",
                "אסטרטגיה", "היכרות", "תור", "חינם",
            ]
            best_calendar = None
            for cal in calendars:
                cal_name_lower = cal.get("name", "").lower()
                cal_desc_lower = cal.get("description", "").lower()
                combined = f"{cal_name_lower} {cal_desc_lower}"
                if any(kw in combined for kw in booking_keywords):
                    best_calendar = cal
                    break
            if not best_calendar:
                best_calendar = calendars[0]

            action_name = (
                f"קביעת תור - {best_calendar['name']}"
                if is_he else f"Book - {best_calendar['name']}"
            )
            auto_actions.append({
                "type": "appointmentBooking",
                "name": action_name,
                "calendar_id": best_calendar["id"],
                "_auto_linked": True,
            })
            print(f"    🔗 Auto-linked calendar: {best_calendar['name']} → appointmentBooking")

        # --- Auto-link custom fields → updateContactField ---
        custom_fields = self.created_resources.get("custom_fields", [])
        if custom_fields:
            for cf in custom_fields:
                field_id = cf.get("id", "")
                field_name = cf.get("name", "")
                data_type = cf.get("dataType", "TEXT")
                options = cf.get("options", [])

                # Build description for the AI
                description = field_name
                if options:
                    description += f" (options: {', '.join(options)})"

                # Build examples based on data type
                # GHL requires contactUpdateExamples for most field types
                examples = []
                if data_type in ("SINGLE_OPTIONS", "MULTIPLE_OPTIONS", "RADIO",
                                 "CHECKBOX", "TEXTBOX_LIST") and options:
                    examples = options[:3]
                elif data_type == "TEXT":
                    examples = [f"Example {field_name}"]
                elif data_type == "LARGE_TEXT":
                    examples = [f"Detailed notes about {field_name}"]
                elif data_type == "NUMERICAL":
                    examples = ["100", "500", "1000"]
                elif data_type == "PHONE":
                    examples = ["+972501234567"]
                elif data_type == "MONETORY":
                    examples = ["5000", "10000"]
                elif data_type == "DATE":
                    examples = ["2026-01-15"]
                elif data_type == "TIME":
                    examples = ["09:00", "14:30"]
                elif data_type == "FILE_UPLOAD":
                    examples = ["document.pdf"]
                elif data_type == "FLOAT":
                    examples = ["3.5", "7.25"]

                action = {
                    "type": "updateContactField",
                    "name": f"Update: {field_name}",
                    "contactFieldId": field_id,
                    "description": description,
                    "_auto_linked": True,
                }
                if examples:
                    action["contactUpdateExamples"] = examples

                auto_actions.append(action)

            field_names = [cf.get("name", "") for cf in custom_fields]
            print(f"    🔗 Auto-linked {len(custom_fields)} custom fields → updateContactField: {', '.join(field_names)}")

        # --- Auto-add stopBot ---
        if is_he:
            auto_actions.append({
                "type": "stopBot",
                "name": "עצירת בוט",
                "stopBotDetectionType": "Goodbye",
                "stopBotTriggerCondition": "כשהלקוח אומר שהוא לא צריך עוד עזרה או רוצה לסיים את השיחה",
                "stopBotExamples": ["תודה רבה, זה הכל", "אין לי עוד שאלות", "יאללה ביי"],
                "finalMessage": "תודה שפנית אלינו! יום מעולה 🙏",
                "enabled": True,
                "reactivateEnabled": False,
                "_auto_linked": True,
            })
        else:
            auto_actions.append({
                "type": "stopBot",
                "name": "Stop Bot",
                "stopBotDetectionType": "Goodbye",
                "stopBotTriggerCondition": "When the user says they no longer need assistance",
                "stopBotExamples": ["thank you that's all", "no more questions", "goodbye"],
                "finalMessage": "Thank you for contacting us! Have a great day.",
                "enabled": True,
                "reactivateEnabled": False,
                "_auto_linked": True,
            })
        print("    🔗 Auto-added stopBot action")

        # --- humanHandOver ---
        # NOTE: GHL API has a known bug with humanHandOver via Private Integration Token
        # ("Cannot read properties of undefined (reading 'replace')").
        # Only auto-add when an explicit assignToUserId is provided in the prompt.
        # Otherwise, humanHandOver must be configured manually in the GHL UI.
        if cmd.get("handover_user_id"):
            if is_he:
                auto_actions.append({
                    "type": "humanHandOver",
                    "name": "העברה לנציג אנושי",
                    "triggerCondition": "כשהלקוח מבקש לדבר עם נציג אנושי",
                    "examples": ["אני רוצה לדבר עם בן אדם", "תעביר אותי לנציג"],
                    "handoverType": "contactRequest",
                    "finalMessage": "מעביר אותך לנציג שלנו!",
                    "assignToUserId": cmd["handover_user_id"],
                    "reactivateEnabled": True,
                    "sleepTimeUnit": "hours",
                    "sleepTime": 24,
                    "createTask": True,
                    "_auto_linked": True,
                })
            else:
                auto_actions.append({
                    "type": "humanHandOver",
                    "name": "Human Handover",
                    "triggerCondition": "When the user requests to speak with a human",
                    "examples": ["speak to a person", "transfer me to agent"],
                    "handoverType": "contactRequest",
                    "finalMessage": "Transferring you to our team!",
                    "assignToUserId": cmd["handover_user_id"],
                    "reactivateEnabled": True,
                    "sleepTimeUnit": "hours",
                    "sleepTime": 24,
                    "createTask": True,
                    "_auto_linked": True,
                })
            print("    🔗 Auto-added humanHandOver action")
        else:
            print("    ℹ️  humanHandOver: skipped (requires assignToUserId — configure in GHL UI)")

        # --- Auto-add advancedFollowup ---
        auto_actions.append({
            "type": "advancedFollowup",
            "name": "מעקב אוטומטי" if is_he else "Auto Follow-up",
            "scenarioId": "contactStoppedReplying",
            "followupSequence": [
                {
                    "id": 1,
                    "followupTimeUnit": "hours",
                    "followupTime": 2,
                    "aiEnabledMessage": True,
                    "triggerWorkflow": False,
                },
                {
                    "id": 2,
                    "followupTimeUnit": "hours",
                    "followupTime": 24,
                    "aiEnabledMessage": True,
                    "triggerWorkflow": False,
                },
            ],
            "followupSettings": {
                "dynamicChannelSwitching": True,
            },
            "_auto_linked": True,
        })
        print("    🔗 Auto-added advancedFollowup action")

        return auto_actions

    def _build_agent_action(self, action_spec: dict) -> dict | None:
        """
        Build an action config from a simplified spec.

        GHL API uses 'details' (not 'settings') for action configuration.
        All 7 supported action types:
          appointmentBooking, triggerWorkflow, updateContactField,
          stopBot, humanHandOver, advancedFollowup, transferBot
        """
        action_type = action_spec.get("type", "")

        # --- appointmentBooking ---
        if action_type == "appointmentBooking":
            details = {
                "calendarId": action_spec.get("calendar_id",
                                               action_spec.get("calendarId", "")),
                "onlySendLink": action_spec.get("onlySendLink", False),
                "triggerWorkflow": action_spec.get("triggerWorkflow", False),
                "sleepAfterBooking": action_spec.get("sleepAfterBooking", False),
                "transferBot": action_spec.get("transferBot", False),
                "rescheduleEnabled": action_spec.get("rescheduleEnabled", False),
                "cancelEnabled": action_spec.get("cancelEnabled", False),
            }
            return {"type": "appointmentBooking",
                    "name": action_spec.get("name", "Book Appointment"),
                    "details": details}

        # --- triggerWorkflow ---
        elif action_type in ("workflow", "triggerWorkflow"):
            workflow_id = action_spec.get("workflow_id",
                                           action_spec.get("workflowId", ""))
            details = {
                "workflowIds": action_spec.get("workflowIds",
                                                [workflow_id] if workflow_id else []),
                "triggerCondition": action_spec.get("triggerCondition",
                                                     "When the contact requests it"),
            }
            if action_spec.get("triggerMessage"):
                details["triggerMessage"] = action_spec["triggerMessage"]
            return {"type": "triggerWorkflow",
                    "name": action_spec.get("name", "Trigger Workflow"),
                    "details": details}

        # --- updateContactField ---
        elif action_type in ("updateContactField", "contactInfo", "contactCollection"):
            details = {
                "contactFieldId": action_spec.get("contactFieldId",
                                                    action_spec.get("contact_field_id", "")),
                "description": action_spec.get("description", ""),
            }
            examples = action_spec.get("contactUpdateExamples", [])
            if examples:
                details["contactUpdateExamples"] = examples
            return {"type": "updateContactField",
                    "name": action_spec.get("name", "Update Contact Info"),
                    "details": details}

        # --- stopBot ---
        elif action_type == "stopBot":
            details = {
                "stopBotDetectionType": action_spec.get("stopBotDetectionType", "Goodbye"),
                "stopBotTriggerCondition": action_spec.get("stopBotTriggerCondition",
                    "When the user says they no longer need assistance or want to end the conversation"),
                "reactivateEnabled": action_spec.get("reactivateEnabled", False),
                "enabled": action_spec.get("enabled", True),
                "stopBotExamples": action_spec.get("stopBotExamples",
                    ["goodbye", "thank you, that's all", "no more questions"]),
                "finalMessage": action_spec.get("finalMessage",
                    "Thank you for contacting us. Have a great day!"),
            }
            if action_spec.get("tags"):
                details["tags"] = action_spec["tags"]
            if details["reactivateEnabled"]:
                details["sleepTimeUnit"] = action_spec.get("sleepTimeUnit", "hours")
                details["sleepTime"] = action_spec.get("sleepTime", 24)
            return {"type": "stopBot",
                    "name": action_spec.get("name", "Stop Bot"),
                    "details": details}

        # --- humanHandOver ---
        elif action_type in ("humanHandOver", "humanHandover", "human_handover"):
            details = {
                "enabled": action_spec.get("enabled", True),
                "triggerCondition": action_spec.get("triggerCondition",
                    "When the user requests to speak with a human agent or expresses frustration"),
                "handoverType": action_spec.get("handoverType", "contactRequest"),
                "reactivateEnabled": action_spec.get("reactivateEnabled", True),
                "finalMessage": action_spec.get("finalMessage",
                    "I'm transferring you to a team member who can help you better."),
            }
            examples = action_spec.get("examples",
                ["speak to human", "talk to agent", "I want a real person"])
            if examples:
                details["examples"] = examples
            if action_spec.get("assignToUserId"):
                details["assignToUserId"] = action_spec["assignToUserId"]
                details["skipAssignToUser"] = False
            details["createTask"] = action_spec.get("createTask", True)
            if details["reactivateEnabled"]:
                details["sleepTimeUnit"] = action_spec.get("sleepTimeUnit", "hours")
                details["sleepTime"] = action_spec.get("sleepTime", 24)
            if action_spec.get("tags"):
                details["tags"] = action_spec["tags"]
            return {"type": "humanHandOver",
                    "name": action_spec.get("name", "Human Handover"),
                    "details": details}

        # --- advancedFollowup ---
        elif action_type in ("advancedFollowup", "followUp", "autoFollowup", "auto_followup"):
            followup_sequence = action_spec.get("followupSequence", [
                {
                    "id": 1,
                    "followupTimeUnit": "hours",
                    "followupTime": 2,
                    "aiEnabledMessage": True,
                    "triggerWorkflow": False,
                },
                {
                    "id": 2,
                    "followupTimeUnit": "hours",
                    "followupTime": 24,
                    "aiEnabledMessage": True,
                    "triggerWorkflow": False,
                },
            ])
            details = {
                "enabled": action_spec.get("enabled", True),
                "scenarioId": action_spec.get("scenarioId", "contactStoppedReplying"),
                "followupSequence": followup_sequence,
                "followupSettings": action_spec.get("followupSettings", {
                    "dynamicChannelSwitching": True,
                }),
            }
            return {"type": "advancedFollowup",
                    "name": action_spec.get("name", "Auto Follow-up"),
                    "details": details}

        # --- transferBot ---
        elif action_type in ("transferBot", "transfer_bot"):
            details = {
                "transferBotType": action_spec.get("transferBotType", "Default"),
                "transferToBot": action_spec.get("transferToBot",
                                                   action_spec.get("transfer_to_bot", "")),
                "enabled": action_spec.get("enabled", True),
            }
            if details["transferBotType"] == "Custom":
                details["transferBotTriggerCondition"] = action_spec.get(
                    "transferBotTriggerCondition",
                    "When the user needs a different department or specialist")
                details["transferBotExamples"] = action_spec.get(
                    "transferBotExamples",
                    ["transfer me", "speak to specialist"])
            return {"type": "transferBot",
                    "name": action_spec.get("name", "Transfer Bot"),
                    "details": details}

        else:
            print(f"    ⚠️  Action type '{action_type}' not recognized — skipping")
            return None

    async def _handle_get_ai_agents(self, cmd: dict) -> dict:
        """Get all Conversation AI agents."""
        self._log("get_ai_agents", "running")
        result = await self.ghl.get_ai_agents()
        if result.get("success"):
            agents = result.get("data", {}).get("agents", [])
            self._log("get_ai_agents", "success", f"Found {len(agents)} agents")
        else:
            self._log("get_ai_agents", "error", result.get("error"))
        return result

    async def _handle_get_ai_agent(self, cmd: dict) -> dict:
        """Get a specific AI agent's full config."""
        agent_id = cmd.get("agent_id", self.results.get("ai_agent_id", ""))
        if not agent_id:
            return {"success": False, "error": "No agent_id provided"}
        self._log("get_ai_agent", "running", f"ID: {agent_id}")
        result = await self.ghl.get_ai_agent(agent_id)
        if result.get("success"):
            self._log("get_ai_agent", "success")
        else:
            self._log("get_ai_agent", "error", result.get("error"))
        return result

    async def _handle_update_ai_agent(self, cmd: dict) -> dict:
        """Update an existing AI agent.
        GHL PUT requires personality, goal, instructions — so we fetch current first."""
        agent_id = cmd.get("agent_id", self.results.get("ai_agent_id", ""))
        if not agent_id:
            return {"success": False, "error": "No agent_id provided"}

        # Fetch current agent data to merge (PUT requires all fields)
        current = await self.ghl.get_ai_agent(agent_id)
        current_data = current.get("data", {})

        data = {
            "personality": current_data.get("personality", ""),
            "goal": current_data.get("goal", ""),
            "instructions": current_data.get("instructions", ""),
        }

        # Override with user-provided fields
        for key in ["name", "businessName", "mode", "channels", "isPrimary",
                     "personality", "goal", "instructions", "agentPrompt",
                     "autoPilotMaxMessages", "sleepEnabled", "sleepTime"]:
            if cmd.get(key) is not None:
                data[key] = cmd[key]

        # Map agentPrompt → instructions for backward compat
        if "agentPrompt" in data and "instructions" not in cmd:
            data["instructions"] = data.pop("agentPrompt")

        # If niche/goals changed, regenerate prompt
        if cmd.get("regenerate_prompt"):
            data["instructions"] = self._generate_agent_prompt(cmd)

        self._log("update_ai_agent", "running", f"ID: {agent_id}")
        result = await self._retry_on_failure(
            self.ghl.update_ai_agent, agent_id, data)
        if result.get("success"):
            self._log("update_ai_agent", "success")
        else:
            self._log("update_ai_agent", "error", result.get("error"))
        return result

    async def _handle_delete_ai_agent(self, cmd: dict) -> dict:
        """Delete an AI agent."""
        agent_id = cmd.get("agent_id", "")
        if not agent_id:
            return {"success": False, "error": "No agent_id provided"}
        self._log("delete_ai_agent", "running", f"ID: {agent_id}")
        result = await self.ghl.delete_ai_agent(agent_id)
        if result.get("success"):
            self._log("delete_ai_agent", "success")
        else:
            self._log("delete_ai_agent", "error", result.get("error"))
        return result

    async def _handle_add_agent_action(self, cmd: dict) -> dict:
        """Add an action to an existing AI agent."""
        agent_id = cmd.get("agent_id", self.results.get("ai_agent_id", ""))
        if not agent_id:
            return {"success": False, "error": "No agent_id provided"}

        action_data = self._build_agent_action(cmd)
        if not action_data:
            return {"success": False,
                    "error": f"Unknown action type: {cmd.get('type')}"}

        self._log("add_agent_action", "running", cmd.get("type", "?"))
        result = await self._retry_on_failure(
            self.ghl.create_ai_agent_action, agent_id, action_data)
        if result.get("success"):
            self._log("add_agent_action", "success")
        else:
            self._log("add_agent_action", "error", result.get("error"))
        return result

    # ========================================================================
    # KNOWLEDGE BASE
    # ========================================================================

    async def _handle_get_knowledge_bases(self, cmd: dict) -> dict:
        """List all knowledge bases for the location."""
        self._log("get_knowledge_bases", "running")
        result = await self._retry_on_failure(self.ghl.get_knowledge_bases)
        if result.get("success"):
            self._log("get_knowledge_bases", "success")
        else:
            self._log("get_knowledge_bases", "error", result.get("error"))
        return result

    async def _handle_create_knowledge_base(self, cmd: dict) -> dict:
        """Create a knowledge base."""
        name = cmd.get("name", "")
        description = cmd.get("description", "")
        self._log("create_knowledge_base", "running", name)
        result = await self._retry_on_failure(
            self.ghl.create_knowledge_base, name, description)
        if result.get("success"):
            kb_id = result.get("data", {}).get("id", "")
            self._log("create_knowledge_base", "success", f"KB ID: {kb_id}")
            self.results["kb_id"] = kb_id
        else:
            self._log("create_knowledge_base", "error", result.get("error"))
        return result

    async def _handle_get_kb_faqs(self, cmd: dict) -> dict:
        """List FAQs for a knowledge base."""
        kb_id = cmd.get("kb_id", cmd.get("knowledgeBaseId",
                        self.results.get("kb_id", "")))
        self._log("get_kb_faqs", "running", f"KB: {kb_id}")
        result = await self._retry_on_failure(self.ghl.get_kb_faqs, kb_id)
        if result.get("success"):
            self._log("get_kb_faqs", "success")
        else:
            self._log("get_kb_faqs", "error", result.get("error"))
        return result

    async def _handle_create_kb_faq(self, cmd: dict) -> dict:
        """Create a FAQ entry in a knowledge base."""
        kb_id = cmd.get("kb_id", cmd.get("knowledgeBaseId",
                        self.results.get("kb_id", "")))
        question = cmd.get("question", "")
        answer = cmd.get("answer", "")
        self._log("create_kb_faq", "running", question[:50])
        result = await self._retry_on_failure(
            self.ghl.create_kb_faq, kb_id, question, answer)
        if result.get("success"):
            faq_id = result.get("data", {}).get("id", "")
            self._log("create_kb_faq", "success", f"FAQ ID: {faq_id}")
            self.results["faq_id"] = faq_id
        else:
            self._log("create_kb_faq", "error", result.get("error"))
        return result

    async def _handle_update_kb_faq(self, cmd: dict) -> dict:
        """Update an existing FAQ entry."""
        faq_id = cmd.get("faq_id", self.results.get("faq_id", ""))
        question = cmd.get("question", "")
        answer = cmd.get("answer", "")
        self._log("update_kb_faq", "running", f"FAQ: {faq_id}")
        result = await self._retry_on_failure(
            self.ghl.update_kb_faq, faq_id, question, answer)
        if result.get("success"):
            self._log("update_kb_faq", "success")
        else:
            self._log("update_kb_faq", "error", result.get("error"))
        return result

    async def _handle_delete_kb_faq(self, cmd: dict) -> dict:
        """Delete a FAQ entry."""
        faq_id = cmd.get("faq_id", self.results.get("faq_id", ""))
        self._log("delete_kb_faq", "running", f"FAQ: {faq_id}")
        result = await self._retry_on_failure(
            self.ghl.delete_kb_faq, faq_id)
        if result.get("success"):
            self._log("delete_kb_faq", "success")
        else:
            self._log("delete_kb_faq", "error", result.get("error"))
        return result

    # ========================================================================
    # INVOICES
    # ========================================================================

    async def _handle_create_invoice(self, cmd: dict) -> dict:
        """Create an invoice."""
        data = {}
        for key in ["contactId", "name", "title", "dueDate", "items",
                     "businessDetails", "currency", "discount"]:
            if cmd.get(key):
                data[key] = cmd[key]
        # Map snake_case
        if cmd.get("contact_id"):
            data["contactId"] = cmd["contact_id"]
        if cmd.get("due_date"):
            data["dueDate"] = cmd["due_date"]

        self._log("create_invoice", "running", data.get("name", "invoice"))
        result = await self._retry_on_failure(self.ghl.create_invoice, data)
        if result.get("success"):
            inv_id = result.get("data", {}).get("invoice", {}).get("_id", "")
            self._log("create_invoice", "success", f"Invoice ID: {inv_id}")
            self.results["invoice_id"] = inv_id
        else:
            self._log("create_invoice", "error", result.get("error"))
        return result

    async def _handle_get_invoices(self, cmd: dict) -> dict:
        """List all invoices."""
        self._log("get_invoices", "running")
        result = await self.ghl.get_invoices(**{
            k: v for k, v in cmd.items() if k != "action"})
        if result.get("success"):
            invoices = result.get("data", {}).get("invoices", [])
            self._log("get_invoices", "success", f"Found {len(invoices)}")
        else:
            self._log("get_invoices", "error", result.get("error"))
        return result

    async def _handle_get_invoice(self, cmd: dict) -> dict:
        """Get a specific invoice."""
        invoice_id = cmd.get("invoice_id", self.results.get("invoice_id", ""))
        self._log("get_invoice", "running", f"ID: {invoice_id}")
        result = await self.ghl.get_invoice(invoice_id)
        if result.get("success"):
            self._log("get_invoice", "success")
        else:
            self._log("get_invoice", "error", result.get("error"))
        return result

    async def _handle_update_invoice(self, cmd: dict) -> dict:
        """Update an invoice."""
        invoice_id = cmd.get("invoice_id", self.results.get("invoice_id", ""))
        data = cmd.get("data", {k: v for k, v in cmd.items()
                                if k not in ("action", "invoice_id")})
        self._log("update_invoice", "running", f"ID: {invoice_id}")
        result = await self.ghl.update_invoice(invoice_id, data)
        if result.get("success"):
            self._log("update_invoice", "success")
        else:
            self._log("update_invoice", "error", result.get("error"))
        return result

    async def _handle_delete_invoice(self, cmd: dict) -> dict:
        """Delete an invoice."""
        invoice_id = cmd.get("invoice_id", "")
        self._log("delete_invoice", "running", f"ID: {invoice_id}")
        result = await self.ghl.delete_invoice(invoice_id)
        if result.get("success"):
            self._log("delete_invoice", "success")
        else:
            self._log("delete_invoice", "error", result.get("error"))
        return result

    async def _handle_send_invoice(self, cmd: dict) -> dict:
        """Send an invoice."""
        invoice_id = cmd.get("invoice_id", self.results.get("invoice_id", ""))
        data = cmd.get("data", {})
        self._log("send_invoice", "running", f"ID: {invoice_id}")
        result = await self.ghl.send_invoice(invoice_id, data)
        if result.get("success"):
            self._log("send_invoice", "success")
        else:
            self._log("send_invoice", "error", result.get("error"))
        return result

    async def _handle_void_invoice(self, cmd: dict) -> dict:
        """Void an invoice."""
        invoice_id = cmd.get("invoice_id", self.results.get("invoice_id", ""))
        self._log("void_invoice", "running", f"ID: {invoice_id}")
        result = await self.ghl.void_invoice(invoice_id, {})
        if result.get("success"):
            self._log("void_invoice", "success")
        else:
            self._log("void_invoice", "error", result.get("error"))
        return result

    async def _handle_record_invoice_payment(self, cmd: dict) -> dict:
        """Record a manual payment for an invoice."""
        invoice_id = cmd.get("invoice_id", self.results.get("invoice_id", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "invoice_id")}
        self._log("record_invoice_payment", "running", f"ID: {invoice_id}")
        result = await self.ghl.record_invoice_payment(invoice_id, data)
        if result.get("success"):
            self._log("record_invoice_payment", "success")
        else:
            self._log("record_invoice_payment", "error", result.get("error"))
        return result

    async def _handle_create_text2pay(self, cmd: dict) -> dict:
        """Create and send a text2pay invoice."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_text2pay", "running")
        result = await self._retry_on_failure(self.ghl.create_text2pay_invoice, data)
        if result.get("success"):
            self._log("create_text2pay", "success")
        else:
            self._log("create_text2pay", "error", result.get("error"))
        return result

    # ========================================================================
    # PAYMENTS - Extended
    # ========================================================================

    async def _handle_get_orders(self, cmd: dict) -> dict:
        """List orders."""
        self._log("get_orders", "running")
        result = await self.ghl.get_orders()
        if result.get("success"):
            orders = result.get("data", {}).get("orders", [])
            self._log("get_orders", "success", f"Found {len(orders)}")
        else:
            self._log("get_orders", "error", result.get("error"))
        return result

    async def _handle_get_order(self, cmd: dict) -> dict:
        """Get a specific order."""
        order_id = cmd.get("order_id", "")
        self._log("get_order", "running", f"ID: {order_id}")
        result = await self.ghl.get_order(order_id)
        if result.get("success"):
            self._log("get_order", "success")
        else:
            self._log("get_order", "error", result.get("error"))
        return result

    async def _handle_create_order_fulfillment(self, cmd: dict) -> dict:
        """Create fulfillment for an order."""
        order_id = cmd.get("order_id", "")
        data = {k: v for k, v in cmd.items() if k not in ("action", "order_id")}
        self._log("create_order_fulfillment", "running", f"Order: {order_id}")
        result = await self.ghl.create_order_fulfillment(order_id, data)
        if result.get("success"):
            self._log("create_order_fulfillment", "success")
        else:
            self._log("create_order_fulfillment", "error", result.get("error"))
        return result

    async def _handle_get_transactions(self, cmd: dict) -> dict:
        """List transactions."""
        self._log("get_transactions", "running")
        result = await self.ghl.get_transactions()
        if result.get("success"):
            txns = result.get("data", {}).get("transactions", [])
            self._log("get_transactions", "success", f"Found {len(txns)}")
        else:
            self._log("get_transactions", "error", result.get("error"))
        return result

    async def _handle_get_subscriptions(self, cmd: dict) -> dict:
        """List subscriptions."""
        self._log("get_subscriptions", "running")
        result = await self.ghl.get_subscriptions()
        if result.get("success"):
            subs = result.get("data", {}).get("subscriptions", [])
            self._log("get_subscriptions", "success", f"Found {len(subs)}")
        else:
            self._log("get_subscriptions", "error", result.get("error"))
        return result

    async def _handle_create_coupon(self, cmd: dict) -> dict:
        """Create a payment coupon."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_coupon", "running", cmd.get("name", ""))
        result = await self._retry_on_failure(self.ghl.create_coupon, data)
        if result.get("success"):
            self._log("create_coupon", "success")
        else:
            self._log("create_coupon", "error", result.get("error"))
        return result

    async def _handle_get_coupons(self, cmd: dict) -> dict:
        """List all coupons."""
        self._log("get_coupons", "running")
        result = await self.ghl.get_coupons()
        if result.get("success"):
            self._log("get_coupons", "success")
        else:
            self._log("get_coupons", "error", result.get("error"))
        return result

    async def _handle_update_coupon(self, cmd: dict) -> dict:
        """Update a coupon."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("update_coupon", "running")
        result = await self.ghl.update_coupon(data)
        if result.get("success"):
            self._log("update_coupon", "success")
        else:
            self._log("update_coupon", "error", result.get("error"))
        return result

    async def _handle_delete_coupon(self, cmd: dict) -> dict:
        """Delete a coupon."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("delete_coupon", "running")
        result = await self.ghl.delete_coupon(data)
        if result.get("success"):
            self._log("delete_coupon", "success")
        else:
            self._log("delete_coupon", "error", result.get("error"))
        return result

    # ========================================================================
    # CUSTOM OBJECTS (Schemas & Records)
    # ========================================================================

    async def _handle_get_object_schemas(self, cmd: dict) -> dict:
        """Get all object schemas for location."""
        self._log("get_object_schemas", "running")
        result = await self.ghl.get_object_schemas()
        if result.get("success"):
            self._log("get_object_schemas", "success")
        else:
            self._log("get_object_schemas", "error", result.get("error"))
        return result

    @staticmethod
    def _to_english_slug(text: str) -> str:
        """
        Convert text to an English snake_case slug.
        Handles Hebrew by transliterating common characters.
        Falls back to a hash-based slug if no ASCII characters remain.
        """
        import re
        import hashlib

        # Hebrew transliteration map
        he_map = {
            'א': 'a', 'ב': 'b', 'ג': 'g', 'ד': 'd', 'ה': 'h', 'ו': 'v',
            'ז': 'z', 'ח': 'ch', 'ט': 't', 'י': 'y', 'כ': 'k', 'ך': 'k',
            'ל': 'l', 'מ': 'm', 'ם': 'm', 'נ': 'n', 'ן': 'n', 'ס': 's',
            'ע': 'a', 'פ': 'p', 'ף': 'f', 'צ': 'ts', 'ץ': 'ts', 'ק': 'k',
            'ר': 'r', 'ש': 'sh', 'ת': 't',
        }

        # Transliterate Hebrew characters
        result = []
        for ch in text:
            if ch in he_map:
                result.append(he_map[ch])
            else:
                result.append(ch)
        transliterated = ''.join(result)

        # Convert to snake_case: keep only a-z, 0-9, replace rest with _
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', transliterated).strip('_').lower()

        # If still empty (shouldn't happen with transliteration), use hash
        if not slug:
            slug = f"obj_{hashlib.md5(text.encode()).hexdigest()[:8]}"

        return slug

    async def _handle_create_custom_object(self, cmd: dict) -> dict:
        """
        Create a custom object schema.

        GHL API requires:
          - labels: { singular, plural } (can be Hebrew — displayed in UI)
          - key: "custom_objects.<english_snake_case>" (MUST be English)
          - primaryDisplayPropertyDetails: { key, name, dataType }
        """
        import re

        data = {k: v for k, v in cmd.items() if k != "action"}

        # --- Build labels if not provided ---
        labels = data.get("labels", {})
        if not labels:
            name = data.pop("name", "")
            if name:
                labels = {"singular": name, "plural": f"{name}s"}
                data["labels"] = labels

        # --- Auto-generate key from labels (MUST be English) ---
        if not data.get("key"):
            plural = labels.get("plural", labels.get("singular", "object"))
            slug = self._to_english_slug(plural)
            data["key"] = f"custom_objects.{slug}"

        obj_key = data["key"]

        # --- Ensure primaryDisplayPropertyDetails has all required fields ---
        # GHL requires: { key: "custom_objects.<plural>.<field>", name, dataType }
        details = data.get("primaryDisplayPropertyDetails", {})
        # Remove 'position' — GHL rejects it
        details.pop("position", None)
        # Ensure required fields
        details.setdefault("name", "Name")
        details.setdefault("dataType", "TEXT")
        # Auto-generate the key field from obj_key + field name
        if not details.get("key"):
            field_slug = self._to_english_slug(details["name"])
            details["key"] = f"{obj_key}.{field_slug}"
        data["primaryDisplayPropertyDetails"] = details

        # GHL does NOT accept primaryDisplayProperty — remove if present
        data.pop("primaryDisplayProperty", None)

        # name is not a GHL field (we used it for labels)
        data.pop("name", None)

        self._log("create_custom_object", "running",
                  f"{labels.get('singular', '')} (key={obj_key})")
        result = await self._retry_on_failure(
            self.ghl.create_custom_object, data)
        if result.get("success"):
            obj_id = result.get("data", {}).get("id", "")
            self._log("create_custom_object", "success",
                      f"Key: {obj_key}, ID: {obj_id}")
            self._register_created("custom_objects", {
                "id": obj_id,
                "key": obj_key,
                "labels": labels,
            })
        else:
            self._log("create_custom_object", "error", result.get("error"))
        return result

    async def _handle_create_object_record(self, cmd: dict) -> dict:
        """Create a record in a custom object."""
        schema_key = cmd.get("schema_key", cmd.get("schemaKey", ""))
        data = cmd.get("data", {k: v for k, v in cmd.items()
                                if k not in ("action", "schema_key", "schemaKey")})
        self._log("create_object_record", "running", f"Schema: {schema_key}")
        result = await self._retry_on_failure(
            self.ghl.create_object_record, schema_key, data)
        if result.get("success"):
            record_id = result.get("data", {}).get("id", "")
            self._log("create_object_record", "success", f"Record: {record_id}")
            self.results["object_record_id"] = record_id
        else:
            self._log("create_object_record", "error", result.get("error"))
        return result

    async def _handle_search_object_records(self, cmd: dict) -> dict:
        """Search records in a custom object."""
        schema_key = cmd.get("schema_key", cmd.get("schemaKey", ""))
        data = cmd.get("filters", cmd.get("data", {}))
        self._log("search_object_records", "running", f"Schema: {schema_key}")
        result = await self.ghl.search_object_records(schema_key, data)
        if result.get("success"):
            self._log("search_object_records", "success")
        else:
            self._log("search_object_records", "error", result.get("error"))
        return result

    # ========================================================================
    # VOICE AI
    # ========================================================================

    async def _handle_create_voice_agent(self, cmd: dict) -> dict:
        """Create a Voice AI agent."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_voice_agent", "running", cmd.get("name", ""))
        result = await self._retry_on_failure(
            self.ghl.create_voice_agent, data)
        if result.get("success"):
            agent_id = result.get("data", {}).get("id", "")
            self._log("create_voice_agent", "success", f"Agent: {agent_id}")
            self.results["voice_agent_id"] = agent_id
        else:
            self._log("create_voice_agent", "error", result.get("error"))
        return result

    async def _handle_get_voice_agents(self, cmd: dict) -> dict:
        """List Voice AI agents."""
        self._log("get_voice_agents", "running")
        result = await self.ghl.get_voice_agents()
        if result.get("success"):
            agents = result.get("data", {}).get("agents", [])
            self._log("get_voice_agents", "success", f"Found {len(agents)}")
        else:
            self._log("get_voice_agents", "error", result.get("error"))
        return result

    async def _handle_update_voice_agent(self, cmd: dict) -> dict:
        """Update a Voice AI agent."""
        agent_id = cmd.get("agent_id", self.results.get("voice_agent_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "agent_id")}
        self._log("update_voice_agent", "running", f"ID: {agent_id}")
        result = await self.ghl.update_voice_agent(agent_id, data)
        if result.get("success"):
            self._log("update_voice_agent", "success")
        else:
            self._log("update_voice_agent", "error", result.get("error"))
        return result

    async def _handle_delete_voice_agent(self, cmd: dict) -> dict:
        """Delete a Voice AI agent."""
        agent_id = cmd.get("agent_id", "")
        self._log("delete_voice_agent", "running", f"ID: {agent_id}")
        result = await self.ghl.delete_voice_agent(agent_id)
        if result.get("success"):
            self._log("delete_voice_agent", "success")
        else:
            self._log("delete_voice_agent", "error", result.get("error"))
        return result

    async def _handle_get_voice_call_logs(self, cmd: dict) -> dict:
        """Get Voice AI call logs."""
        self._log("get_voice_call_logs", "running")
        result = await self.ghl.get_voice_call_logs()
        if result.get("success"):
            self._log("get_voice_call_logs", "success")
        else:
            self._log("get_voice_call_logs", "error", result.get("error"))
        return result

    # ========================================================================
    # STORE (Shipping)
    # ========================================================================

    async def _handle_create_shipping_zone(self, cmd: dict) -> dict:
        """Create a shipping zone."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_shipping_zone", "running", cmd.get("name", ""))
        result = await self._retry_on_failure(
            self.ghl.create_shipping_zone, data)
        if result.get("success"):
            zone_id = result.get("data", {}).get("id", "")
            self._log("create_shipping_zone", "success", f"Zone: {zone_id}")
            self.results["shipping_zone_id"] = zone_id
        else:
            self._log("create_shipping_zone", "error", result.get("error"))
        return result

    async def _handle_get_shipping_zones(self, cmd: dict) -> dict:
        """List shipping zones."""
        self._log("get_shipping_zones", "running")
        result = await self.ghl.get_shipping_zones()
        if result.get("success"):
            self._log("get_shipping_zones", "success")
        else:
            self._log("get_shipping_zones", "error", result.get("error"))
        return result

    async def _handle_create_shipping_rate(self, cmd: dict) -> dict:
        """Create a shipping rate."""
        zone_id = cmd.get("zone_id", self.results.get("shipping_zone_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "zone_id")}
        self._log("create_shipping_rate", "running", f"Zone: {zone_id}")
        result = await self._retry_on_failure(
            self.ghl.create_shipping_rate, zone_id, data)
        if result.get("success"):
            self._log("create_shipping_rate", "success")
        else:
            self._log("create_shipping_rate", "error", result.get("error"))
        return result

    async def _handle_create_shipping_carrier(self, cmd: dict) -> dict:
        """Create a shipping carrier."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_shipping_carrier", "running", cmd.get("name", ""))
        result = await self._retry_on_failure(
            self.ghl.create_shipping_carrier, data)
        if result.get("success"):
            self._log("create_shipping_carrier", "success")
        else:
            self._log("create_shipping_carrier", "error", result.get("error"))
        return result

    async def _handle_get_shipping_carriers(self, cmd: dict) -> dict:
        """List shipping carriers."""
        self._log("get_shipping_carriers", "running")
        result = await self.ghl.get_shipping_carriers()
        if result.get("success"):
            self._log("get_shipping_carriers", "success")
        else:
            self._log("get_shipping_carriers", "error", result.get("error"))
        return result

    async def _handle_get_store_settings(self, cmd: dict) -> dict:
        """Get store settings."""
        self._log("get_store_settings", "running")
        result = await self.ghl.get_store_settings()
        if result.get("success"):
            self._log("get_store_settings", "success")
        else:
            self._log("get_store_settings", "error", result.get("error"))
        return result

    async def _handle_update_store_settings(self, cmd: dict) -> dict:
        """Update store settings."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("update_store_settings", "running")
        result = await self.ghl.update_store_settings(data)
        if result.get("success"):
            self._log("update_store_settings", "success")
        else:
            self._log("update_store_settings", "error", result.get("error"))
        return result

    # ========================================================================
    # CUSTOM MENUS
    # ========================================================================

    async def _handle_create_custom_menu(self, cmd: dict) -> dict:
        """Create a custom menu link."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_custom_menu", "running", cmd.get("name", ""))
        result = await self._retry_on_failure(
            self.ghl.create_custom_menu, data)
        if result.get("success"):
            self._log("create_custom_menu", "success")
        else:
            self._log("create_custom_menu", "error", result.get("error"))
        return result

    async def _handle_get_custom_menus(self, cmd: dict) -> dict:
        """Get all custom menu links."""
        self._log("get_custom_menus", "running")
        result = await self.ghl.get_custom_menus()
        if result.get("success"):
            self._log("get_custom_menus", "success")
        else:
            self._log("get_custom_menus", "error", result.get("error"))
        return result

    async def _handle_update_custom_menu(self, cmd: dict) -> dict:
        """Update a custom menu link."""
        menu_id = cmd.get("menu_id", "")
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "menu_id")}
        self._log("update_custom_menu", "running", f"ID: {menu_id}")
        result = await self.ghl.update_custom_menu(menu_id, data)
        if result.get("success"):
            self._log("update_custom_menu", "success")
        else:
            self._log("update_custom_menu", "error", result.get("error"))
        return result

    async def _handle_delete_custom_menu(self, cmd: dict) -> dict:
        """Delete a custom menu link."""
        menu_id = cmd.get("menu_id", "")
        self._log("delete_custom_menu", "running", f"ID: {menu_id}")
        result = await self.ghl.delete_custom_menu(menu_id)
        if result.get("success"):
            self._log("delete_custom_menu", "success")
        else:
            self._log("delete_custom_menu", "error", result.get("error"))
        return result

    # ========================================================================
    # DOCUMENTS / PROPOSALS
    # ========================================================================

    async def _handle_get_documents(self, cmd: dict) -> dict:
        """List all documents."""
        self._log("get_documents", "running")
        result = await self.ghl.get_documents()
        if result.get("success"):
            self._log("get_documents", "success")
        else:
            self._log("get_documents", "error", result.get("error"))
        return result

    async def _handle_send_document(self, cmd: dict) -> dict:
        """Send a document to a client."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("send_document", "running")
        result = await self.ghl.send_document(data)
        if result.get("success"):
            self._log("send_document", "success")
        else:
            self._log("send_document", "error", result.get("error"))
        return result

    async def _handle_get_document_templates(self, cmd: dict) -> dict:
        """List document templates."""
        self._log("get_document_templates", "running")
        result = await self.ghl.get_document_templates()
        if result.get("success"):
            self._log("get_document_templates", "success")
        else:
            self._log("get_document_templates", "error", result.get("error"))
        return result

    async def _handle_send_document_template(self, cmd: dict) -> dict:
        """Send a document template to a client."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("send_document_template", "running")
        result = await self.ghl.send_document_template(data)
        if result.get("success"):
            self._log("send_document_template", "success")
        else:
            self._log("send_document_template", "error", result.get("error"))
        return result

    # ========================================================================
    # SERVICE BOOKINGS
    # ========================================================================

    async def _handle_create_service_booking(self, cmd: dict) -> dict:
        """Create a service booking."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_service_booking", "running")
        result = await self._retry_on_failure(
            self.ghl.create_service_booking, data)
        if result.get("success"):
            self._log("create_service_booking", "success")
        else:
            self._log("create_service_booking", "error", result.get("error"))
        return result

    async def _handle_get_service_bookings(self, cmd: dict) -> dict:
        """List service bookings."""
        self._log("get_service_bookings", "running")
        result = await self.ghl.get_service_bookings()
        if result.get("success"):
            self._log("get_service_bookings", "success")
        else:
            self._log("get_service_bookings", "error", result.get("error"))
        return result

    # ========================================================================
    # PHONE SYSTEM
    # ========================================================================

    async def _handle_get_number_pools(self, cmd: dict) -> dict:
        """Get phone number pools."""
        self._log("get_number_pools", "running")
        result = await self.ghl.get_number_pools()
        if result.get("success"):
            self._log("get_number_pools", "success")
        else:
            self._log("get_number_pools", "error", result.get("error"))
        return result

    async def _handle_get_active_numbers(self, cmd: dict) -> dict:
        """Get active phone numbers."""
        self._log("get_active_numbers", "running")
        result = await self.ghl.get_active_numbers()
        if result.get("success"):
            self._log("get_active_numbers", "success")
        else:
            self._log("get_active_numbers", "error", result.get("error"))
        return result

    # ========================================================================
    # EMAIL VERIFICATION
    # ========================================================================

    async def _handle_verify_email(self, cmd: dict) -> dict:
        """Verify an email address."""
        email = cmd.get("email", "")
        self._log("verify_email", "running", email)
        result = await self.ghl.verify_email({"email": email})
        if result.get("success"):
            self._log("verify_email", "success")
        else:
            self._log("verify_email", "error", result.get("error"))
        return result

    # ========================================================================
    # SNAPSHOTS
    # ========================================================================

    async def _handle_get_snapshots(self, cmd: dict) -> dict:
        """Get snapshots."""
        company_id = cmd.get("company_id", "")
        self._log("get_snapshots", "running")
        result = await self.ghl.get_snapshots(company_id)
        if result.get("success"):
            self._log("get_snapshots", "success")
        else:
            self._log("get_snapshots", "error", result.get("error"))
        return result

    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================

    async def _handle_create_association(self, cmd: dict) -> dict:
        """
        Create an association between two objects.

        Supports relationship types:
        - ONE_TO_MANY: e.g., 1 contact → many invoices
        - MANY_TO_ONE: e.g., many contacts → 1 company
        - MANY_TO_MANY: e.g., contacts ↔ projects (default)
        - ONE_TO_ONE: e.g., 1 contact → 1 profile

        Use 'relationship' field for simplified syntax:
          "relationship": "one_to_many" | "many_to_one" | "many_to_many" | "one_to_one"

        Or use GHL native fields directly:
          "firstObjectToSecondObjectCardinality": "ONE_TO_MANY"
          "secondObjectToFirstObjectCardinality": "MANY_TO_ONE"
        """
        data = {k: v for k, v in cmd.items() if k not in ("action", "relationship")}

        # Smart cardinality from simplified 'relationship' field
        relationship = cmd.get("relationship", "").lower().replace("-", "_")
        if relationship and "firstObjectToSecondObjectCardinality" not in data:
            cardinality_map = {
                "one_to_many": {
                    "firstObjectToSecondObjectCardinality": "ONE_TO_MANY",
                    "secondObjectToFirstObjectCardinality": "MANY_TO_ONE",
                    "firstObjectToSecondObjectMaxLimit": 1,
                },
                "many_to_one": {
                    "firstObjectToSecondObjectCardinality": "MANY_TO_ONE",
                    "secondObjectToFirstObjectCardinality": "ONE_TO_MANY",
                    "secondObjectToFirstObjectMaxLimit": 1,
                },
                "many_to_many": {
                    "firstObjectToSecondObjectCardinality": "MANY_TO_MANY",
                    "secondObjectToFirstObjectCardinality": "MANY_TO_MANY",
                },
                "one_to_one": {
                    "firstObjectToSecondObjectCardinality": "ONE_TO_ONE",
                    "secondObjectToFirstObjectCardinality": "ONE_TO_ONE",
                    "firstObjectToSecondObjectMaxLimit": 1,
                    "secondObjectToFirstObjectMaxLimit": 1,
                },
            }
            cardinality = cardinality_map.get(relationship, cardinality_map["many_to_many"])
            data.update(cardinality)

        # Auto-detect relationship from context if no explicit setting
        if "firstObjectToSecondObjectCardinality" not in data:
            # Default: smart detection based on object names
            first_obj = data.get("firstObjectKey", "").lower()
            second_obj = data.get("secondObjectKey", "").lower()
            # If one side is "contact" and other is a custom object, default to ONE_TO_MANY
            # (1 contact has many records of that object)
            if first_obj == "contact" and "custom_objects" in second_obj:
                data.update({
                    "firstObjectToSecondObjectCardinality": "ONE_TO_MANY",
                    "secondObjectToFirstObjectCardinality": "MANY_TO_ONE",
                    "firstObjectToSecondObjectMaxLimit": 1,
                })
            elif "custom_objects" in first_obj and second_obj == "contact":
                data.update({
                    "firstObjectToSecondObjectCardinality": "MANY_TO_ONE",
                    "secondObjectToFirstObjectCardinality": "ONE_TO_MANY",
                    "secondObjectToFirstObjectMaxLimit": 1,
                })

        self._log("create_association", "running",
                   f"{data.get('firstObjectKey', '')} ↔ {data.get('secondObjectKey', '')}")
        result = await self._retry_on_failure(
            self.ghl.create_association, data)
        if result.get("success"):
            rel_type = data.get("firstObjectToSecondObjectCardinality", "MANY_TO_MANY")
            self._log("create_association", "success", f"Relationship: {rel_type}")
        else:
            self._log("create_association", "error", result.get("error"))
        return result

    async def _handle_get_associations(self, cmd: dict) -> dict:
        """Get all associations."""
        self._log("get_associations", "running")
        result = await self.ghl.get_associations()
        if result.get("success"):
            self._log("get_associations", "success")
        else:
            self._log("get_associations", "error", result.get("error"))
        return result

    # ========================================================================
    # CONVERSATIONS - Extended
    # ========================================================================

    async def _handle_create_conversation(self, cmd: dict) -> dict:
        """Create a new conversation (or return existing one)."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        self._log("create_conversation", "running", f"Contact: {contact_id}")
        result = await self.ghl.create_conversation(contact_id)
        if result.get("success"):
            conv_id = result.get("data", {}).get("conversation", {}).get("id", "")
            self._log("create_conversation", "success", f"ID: {conv_id}")
            self.results["conversation_id"] = conv_id
        else:
            # GHL returns 400 "Conversation already exists" with conversationId
            resp_body = result.get("response_body", "")
            if "already exists" in str(resp_body).lower():
                import json as _json
                try:
                    body = _json.loads(resp_body) if isinstance(resp_body, str) else resp_body
                    conv_id = body.get("conversationId", "")
                    self._log("create_conversation", "success",
                               f"Already exists — ID: {conv_id}")
                    self.results["conversation_id"] = conv_id
                    return {"success": True, "data": {"conversationId": conv_id},
                            "note": "Conversation already existed"}
                except Exception:
                    pass
            self._log("create_conversation", "error", result.get("error"))
        return result

    async def _handle_send_message(self, cmd: dict) -> dict:
        """Send any message type (SMS, Email, WhatsApp, etc.)."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        msg_type = cmd.get("type", "SMS")
        message = cmd.get("message", cmd.get("body", ""))
        kwargs = {k: v for k, v in cmd.items()
                  if k not in ("action", "contact_id", "type", "message", "body")}
        self._log("send_message", "running", f"{msg_type} → {contact_id[:12]}...")
        result = await self.ghl.send_message(contact_id, msg_type, message, **kwargs)
        if result.get("success"):
            self._log("send_message", "success")
        else:
            self._log("send_message", "error", result.get("error"))
        return result

    # ========================================================================
    # OPPORTUNITIES - Extended
    # ========================================================================

    async def _handle_update_opportunity(self, cmd: dict) -> dict:
        """Update an opportunity."""
        opp_id = cmd.get("opportunity_id", self.results.get("opportunity_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "opportunity_id")}
        self._log("update_opportunity", "running", f"ID: {opp_id}")
        result = await self.ghl.update_opportunity(opp_id, data)
        if result.get("success"):
            self._log("update_opportunity", "success")
        else:
            self._log("update_opportunity", "error", result.get("error"))
        return result

    async def _handle_update_opportunity_status(self, cmd: dict) -> dict:
        """Update opportunity status (open/won/lost/abandoned)."""
        opp_id = cmd.get("opportunity_id", self.results.get("opportunity_id", ""))
        status = cmd.get("status", "open")
        self._log("update_opportunity_status", "running",
                   f"ID: {opp_id} → {status}")
        result = await self.ghl.update_opportunity_status(opp_id, status)
        if result.get("success"):
            self._log("update_opportunity_status", "success")
        else:
            self._log("update_opportunity_status", "error", result.get("error"))
        return result

    async def _handle_upsert_opportunity(self, cmd: dict) -> dict:
        """Upsert an opportunity."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        if cmd.get("pipeline_id"):
            data["pipelineId"] = cmd["pipeline_id"]
        self._log("upsert_opportunity", "running", cmd.get("name", ""))
        result = await self._retry_on_failure(
            self.ghl.upsert_opportunity, data)
        if result.get("success"):
            self._log("upsert_opportunity", "success")
        else:
            self._log("upsert_opportunity", "error", result.get("error"))
        return result

    async def _handle_search_opportunities(self, cmd: dict) -> dict:
        """Search opportunities."""
        self._log("search_opportunities", "running")
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_opportunities(**kwargs)
        if result.get("success"):
            opps = result.get("data", {}).get("opportunities", [])
            self._log("search_opportunities", "success", f"Found {len(opps)}")
        else:
            self._log("search_opportunities", "error", result.get("error"))
        return result

    # ========================================================================
    # MEDIA LIBRARY
    # ========================================================================

    async def _handle_get_media_files(self, cmd: dict) -> dict:
        """Get media library files."""
        self._log("get_media_files", "running")
        result = await self.ghl.get_media_files()
        if result.get("success"):
            files = result.get("data", {}).get("files", [])
            self._log("get_media_files", "success", f"Found {len(files)}")
        else:
            self._log("get_media_files", "error", result.get("error"))
        return result

    async def _handle_delete_media_file(self, cmd: dict) -> dict:
        """Delete a media file."""
        file_id = cmd.get("file_id", "")
        self._log("delete_media_file", "running", f"ID: {file_id}")
        result = await self.ghl.delete_media_file(file_id)
        if result.get("success"):
            self._log("delete_media_file", "success")
        else:
            self._log("delete_media_file", "error", result.get("error"))
        return result

    async def _handle_create_media_folder(self, cmd: dict) -> dict:
        """Create a media folder."""
        name = cmd.get("name", "")
        parent_id = cmd.get("parent_id")
        self._log("create_media_folder", "running", name)
        result = await self.ghl.create_media_folder(name, parent_id)
        if result.get("success"):
            self._log("create_media_folder", "success")
        else:
            self._log("create_media_folder", "error", result.get("error"))
        return result

    # ========================================================================
    # BLOGS - Extended
    # ========================================================================

    async def _handle_get_blogs(self, cmd: dict) -> dict:
        """Get all blogs for location."""
        self._log("get_blogs", "running")
        result = await self.ghl.get_blogs()
        if result.get("success"):
            self._log("get_blogs", "success")
        else:
            self._log("get_blogs", "error", result.get("error"))
        return result

    async def _handle_get_blog_posts(self, cmd: dict) -> dict:
        """Get blog posts for a blog."""
        blog_id = cmd.get("blog_id", "")
        self._log("get_blog_posts", "running", f"Blog: {blog_id}")
        result = await self.ghl.get_blog_posts(blog_id)
        if result.get("success"):
            self._log("get_blog_posts", "success")
        else:
            self._log("get_blog_posts", "error", result.get("error"))
        return result

    async def _handle_update_blog_post(self, cmd: dict) -> dict:
        """Update a blog post."""
        post_id = cmd.get("post_id", "")
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "post_id")}
        self._log("update_blog_post", "running", f"Post: {post_id}")
        result = await self.ghl.update_blog_post(post_id, data)
        if result.get("success"):
            self._log("update_blog_post", "success")
        else:
            self._log("update_blog_post", "error", result.get("error"))
        return result

    # ========================================================================
    # CONTACTS - Extended
    # ========================================================================

    async def _handle_remove_contact_tags(self, cmd: dict) -> dict:
        """Remove tags from a contact."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        tags = cmd.get("tags", [])
        self._log("remove_contact_tags", "running",
                   f"{tags} from {contact_id[:12]}...")
        result = await self.ghl.remove_contact_tags(contact_id, tags)
        if result.get("success"):
            self._log("remove_contact_tags", "success")
        else:
            self._log("remove_contact_tags", "error", result.get("error"))
        return result

    async def _handle_remove_contact_from_campaign(self, cmd: dict) -> dict:
        """Remove a contact from a campaign."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        campaign_id = cmd.get("campaign_id", "")
        self._log("remove_from_campaign", "running")
        result = await self.ghl.remove_contact_from_campaign(
            contact_id, campaign_id)
        if result.get("success"):
            self._log("remove_from_campaign", "success")
        else:
            self._log("remove_from_campaign", "error", result.get("error"))
        return result

    async def _handle_get_contact(self, cmd: dict) -> dict:
        """Get a specific contact by ID."""
        contact_id = cmd.get("contact_id", self.results.get("contact_id", ""))
        self._log("get_contact", "running", f"ID: {contact_id}")
        result = await self.ghl.get_contact(contact_id)
        if result.get("success"):
            self._log("get_contact", "success")
        else:
            self._log("get_contact", "error", result.get("error"))
        return result

    # ========================================================================
    # LOCATION MANAGEMENT
    # ========================================================================

    async def _handle_get_location(self, cmd: dict) -> dict:
        """Get location/sub-account details."""
        location_id = cmd.get("location_id", self.ghl.location_id)
        self._log("get_location", "running", f"ID: {location_id}")
        result = await self.ghl.get_location(location_id)
        if result.get("success"):
            self._log("get_location", "success")
        else:
            self._log("get_location", "error", result.get("error"))
        return result

    async def _handle_update_location(self, cmd: dict) -> dict:
        """Update location/sub-account."""
        location_id = cmd.get("location_id", self.ghl.location_id)
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "location_id")}
        self._log("update_location", "running", f"ID: {location_id}")
        result = await self.ghl.update_location(location_id, data)
        if result.get("success"):
            self._log("update_location", "success")
        else:
            self._log("update_location", "error", result.get("error"))
        return result

    async def _handle_get_templates(self, cmd: dict) -> dict:
        """Get all templates (email/SMS)."""
        self._log("get_templates", "running")
        result = await self.ghl.get_templates()
        if result.get("success"):
            self._log("get_templates", "success")
        else:
            self._log("get_templates", "error", result.get("error"))
        return result

    async def _handle_get_custom_values(self, cmd: dict) -> dict:
        """Get custom values."""
        self._log("get_custom_values", "running")
        result = await self.ghl.get_custom_values()
        if result.get("success"):
            vals = result.get("data", {}).get("customValues", [])
            self._log("get_custom_values", "success", f"Found {len(vals)}")
        else:
            self._log("get_custom_values", "error", result.get("error"))
        return result

    # ========================================================================
    # FORM SUBMISSIONS
    # ========================================================================

    async def _handle_get_form_submissions(self, cmd: dict) -> dict:
        """Get form submissions."""
        self._log("get_form_submissions", "running")
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_form_submissions(**kwargs)
        if result.get("success"):
            self._log("get_form_submissions", "success")
        else:
            self._log("get_form_submissions", "error", result.get("error"))
        return result

    async def _handle_get_survey_submissions(self, cmd: dict) -> dict:
        """Get survey submissions."""
        self._log("get_survey_submissions", "running")
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_survey_submissions(**kwargs)
        if result.get("success"):
            self._log("get_survey_submissions", "success")
        else:
            self._log("get_survey_submissions", "error", result.get("error"))
        return result

    # ========================================================================
    # CALENDAR - Extended handlers
    # ========================================================================

    async def _handle_update_calendar(self, cmd: dict) -> dict:
        """Update a calendar."""
        calendar_id = cmd.get("calendar_id", self.results.get("calendar_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "calendar_id")}
        self._log("update_calendar", "running", f"ID: {calendar_id}")
        result = await self.ghl.update_calendar(calendar_id, data)
        if result.get("success"):
            self._log("update_calendar", "success")
        else:
            self._log("update_calendar", "error", result.get("error"))
        return result

    async def _handle_delete_calendar(self, cmd: dict) -> dict:
        """Delete a calendar."""
        calendar_id = cmd.get("calendar_id", "")
        self._log("delete_calendar", "running", f"ID: {calendar_id}")
        result = await self.ghl.delete_calendar(calendar_id)
        if result.get("success"):
            self._log("delete_calendar", "success")
        else:
            self._log("delete_calendar", "error", result.get("error"))
        return result

    async def _handle_get_free_slots(self, cmd: dict) -> dict:
        """Get free calendar slots."""
        calendar_id = cmd.get("calendar_id", self.results.get("calendar_id", ""))
        start = cmd.get("start_date", cmd.get("startDate", ""))
        end = cmd.get("end_date", cmd.get("endDate", ""))
        tz = cmd.get("timezone", "Asia/Jerusalem")
        self._log("get_free_slots", "running", f"Calendar: {calendar_id}")
        result = await self.ghl.get_calendar_free_slots(
            calendar_id, start, end, tz)
        if result.get("success"):
            self._log("get_free_slots", "success")
        else:
            self._log("get_free_slots", "error", result.get("error"))
        return result

    async def _handle_update_appointment(self, cmd: dict) -> dict:
        """Update an appointment."""
        event_id = cmd.get("event_id", cmd.get("appointment_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "event_id", "appointment_id")}
        self._log("update_appointment", "running", f"ID: {event_id}")
        result = await self.ghl.update_appointment(event_id, data)
        if result.get("success"):
            self._log("update_appointment", "success")
        else:
            self._log("update_appointment", "error", result.get("error"))
        return result

    async def _handle_get_calendar_events(self, cmd: dict) -> dict:
        """Get calendar events. Requires calendarId or userId or groupId."""
        calendar_id = cmd.get("calendar_id", cmd.get("calendarId",
                               self.results.get("calendar_id", "")))
        self._log("get_calendar_events", "running")
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        if calendar_id and "calendarId" not in kwargs:
            kwargs["calendarId"] = calendar_id
        result = await self.ghl.get_calendar_events(**kwargs)
        if result.get("success"):
            self._log("get_calendar_events", "success")
        else:
            self._log("get_calendar_events", "error", result.get("error"))
        return result

    async def _handle_create_block_slot(self, cmd: dict) -> dict:
        """Create a block slot on calendar."""
        data = {k: v for k, v in cmd.items() if k != "action"}
        self._log("create_block_slot", "running")
        result = await self.ghl.create_block_slot(data)
        if result.get("success"):
            self._log("create_block_slot", "success")
        else:
            self._log("create_block_slot", "error", result.get("error"))
        return result

    # ========================================================================
    # EMAIL TEMPLATES - Extended
    # ========================================================================

    async def _handle_get_email_templates(self, cmd: dict) -> dict:
        """Get email builder templates."""
        self._log("get_email_templates", "running")
        result = await self.ghl.get_email_templates()
        if result.get("success"):
            self._log("get_email_templates", "success")
        else:
            self._log("get_email_templates", "error", result.get("error"))
        return result

    async def _handle_delete_email_template(self, cmd: dict) -> dict:
        """Delete an email template."""
        template_id = cmd.get("template_id", "")
        self._log("delete_email_template", "running", f"ID: {template_id}")
        result = await self.ghl.delete_email_template(template_id)
        if result.get("success"):
            self._log("delete_email_template", "success")
        else:
            self._log("delete_email_template", "error", result.get("error"))
        return result

    # ========================================================================
    # USERS - Extended
    # ========================================================================

    async def _handle_update_user(self, cmd: dict) -> dict:
        """Update a user."""
        user_id = cmd.get("user_id", self.results.get("user_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "user_id")}
        self._log("update_user", "running", f"ID: {user_id}")
        result = await self.ghl.update_user(user_id, data)
        if result.get("success"):
            self._log("update_user", "success")
        else:
            self._log("update_user", "error", result.get("error"))
        return result

    async def _handle_delete_user(self, cmd: dict) -> dict:
        """Delete a user."""
        user_id = cmd.get("user_id", "")
        self._log("delete_user", "running", f"ID: {user_id}")
        result = await self.ghl.delete_user(user_id)
        if result.get("success"):
            self._log("delete_user", "success")
        else:
            self._log("delete_user", "error", result.get("error"))
        return result

    # ========================================================================
    # PRODUCTS - Extended
    # ========================================================================

    async def _handle_update_product(self, cmd: dict) -> dict:
        """Update a product."""
        product_id = cmd.get("product_id", self.results.get("product_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "product_id")}
        self._log("update_product", "running", f"ID: {product_id}")
        result = await self.ghl.update_product(product_id, data)
        if result.get("success"):
            self._log("update_product", "success")
        else:
            self._log("update_product", "error", result.get("error"))
        return result

    async def _handle_delete_product(self, cmd: dict) -> dict:
        """Delete a product."""
        product_id = cmd.get("product_id", "")
        self._log("delete_product", "running", f"ID: {product_id}")
        result = await self.ghl.delete_product(product_id)
        if result.get("success"):
            self._log("delete_product", "success")
        else:
            self._log("delete_product", "error", result.get("error"))
        return result

    async def _handle_create_product_price(self, cmd: dict) -> dict:
        """Create a price for a product."""
        product_id = cmd.get("product_id", self.results.get("product_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "product_id")}
        self._log("create_product_price", "running", f"Product: {product_id}")
        result = await self.ghl.create_product_price(product_id, data)
        if result.get("success"):
            self._log("create_product_price", "success")
        else:
            self._log("create_product_price", "error", result.get("error"))
        return result

    # ========================================================================
    # BUSINESSES - Extended
    # ========================================================================

    async def _handle_update_business(self, cmd: dict) -> dict:
        """Update a business."""
        biz_id = cmd.get("business_id", self.results.get("business_id", ""))
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "business_id")}
        self._log("update_business", "running", f"ID: {biz_id}")
        result = await self.ghl.update_business(biz_id, data)
        if result.get("success"):
            self._log("update_business", "success")
        else:
            self._log("update_business", "error", result.get("error"))
        return result

    async def _handle_delete_business(self, cmd: dict) -> dict:
        """Delete a business."""
        biz_id = cmd.get("business_id", "")
        self._log("delete_business", "running", f"ID: {biz_id}")
        result = await self.ghl.delete_business(biz_id)
        if result.get("success"):
            self._log("delete_business", "success")
        else:
            self._log("delete_business", "error", result.get("error"))
        return result

    # ========================================================================
    # TRIGGER LINKS - Extended
    # ========================================================================

    async def _handle_update_link(self, cmd: dict) -> dict:
        """Update a trigger link."""
        link_id = cmd.get("link_id", "")
        name = cmd.get("name", "")
        redirect_to = cmd.get("redirect_to", cmd.get("redirectTo", ""))
        self._log("update_link", "running", f"ID: {link_id}")
        result = await self.ghl.update_link(link_id, name, redirect_to)
        if result.get("success"):
            self._log("update_link", "success")
        else:
            self._log("update_link", "error", result.get("error"))
        return result

    async def _handle_delete_link(self, cmd: dict) -> dict:
        """Delete a trigger link."""
        link_id = cmd.get("link_id", "")
        self._log("delete_link", "running", f"ID: {link_id}")
        result = await self.ghl.delete_link(link_id)
        if result.get("success"):
            self._log("delete_link", "success")
        else:
            self._log("delete_link", "error", result.get("error"))
        return result

    # ========================================================================
    # SOCIAL MEDIA - Extended
    # ========================================================================

    async def _handle_update_social_post(self, cmd: dict) -> dict:
        """Update a social media post."""
        post_id = cmd.get("post_id", "")
        data = {k: v for k, v in cmd.items()
                if k not in ("action", "post_id")}
        self._log("update_social_post", "running", f"ID: {post_id}")
        result = await self.ghl.update_social_post(post_id, data)
        if result.get("success"):
            self._log("update_social_post", "success")
        else:
            self._log("update_social_post", "error", result.get("error"))
        return result

    async def _handle_delete_social_post(self, cmd: dict) -> dict:
        """Delete a social media post."""
        post_id = cmd.get("post_id", "")
        self._log("delete_social_post", "running", f"ID: {post_id}")
        result = await self.ghl.delete_social_post(post_id)
        if result.get("success"):
            self._log("delete_social_post", "success")
        else:
            self._log("delete_social_post", "error", result.get("error"))
        return result

    # ========================================================================
    # LIST ALL AVAILABLE ACTIONS
    # ========================================================================

    async def _handle_list_actions(self, cmd: dict) -> dict:
        """List all available engine actions."""
        actions = sorted([
            method[8:]  # strip "_handle_" prefix
            for method in dir(self)
            if method.startswith("_handle_") and callable(getattr(self, method))
        ])
        self._log("list_actions", "success", f"{len(actions)} actions available")
        return {
            "success": True,
            "actions": actions,
            "total": len(actions),
        }

    # ========================================================================
    # GENERIC READ OPERATIONS
    # ========================================================================

    async def _handle_get_contacts(self, cmd: dict) -> dict:
        return await self._handle_search_contacts(cmd)

    async def _handle_get_workflows(self, cmd: dict) -> dict:
        self._log("get_workflows", "running")
        result = await self.ghl.get_workflows()
        if result.get("success"):
            workflows = result.get("data", {}).get("workflows", [])
            self._log("get_workflows", "success", f"Found {len(workflows)}")
        return result

    async def _handle_get_funnels(self, cmd: dict) -> dict:
        self._log("get_funnels", "running")
        result = await self.ghl.get_funnels()
        if result.get("success"):
            funnels = result.get("data", {}).get("funnels", [])
            self._log("get_funnels", "success", f"Found {len(funnels)}")
        return result

    async def _handle_get_calendars(self, cmd: dict) -> dict:
        self._log("get_calendars", "running")
        result = await self.ghl.get_calendars()
        if result.get("success"):
            calendars = result.get("data", {}).get("calendars", [])
            self._log("get_calendars", "success", f"Found {len(calendars)}")
        return result

    async def _handle_get_tags(self, cmd: dict) -> dict:
        self._log("get_tags", "running")
        result = await self.ghl.get_tags()
        if result.get("success"):
            tags = result.get("data", {}).get("tags", [])
            self._log("get_tags", "success", f"Found {len(tags)}")
        return result

    async def _handle_get_custom_fields(self, cmd: dict) -> dict:
        self._log("get_custom_fields", "running")
        result = await self.ghl.get_custom_fields()
        if result.get("success"):
            fields = result.get("data", {}).get("customFields", [])
            self._log("get_custom_fields", "success", f"Found {len(fields)}")
        return result

    async def _handle_get_products(self, cmd: dict) -> dict:
        self._log("get_products", "running")
        result = await self.ghl.get_products()
        if result.get("success"):
            products = result.get("data", {}).get("products", [])
            self._log("get_products", "success", f"Found {len(products)}")
        return result

    # ========================================================================
    # RAW API CALL
    # ========================================================================

    async def _handle_raw(self, cmd: dict) -> dict:
        """Execute a raw API call. Full control."""
        method = cmd.get("method", "GET")
        endpoint = cmd.get("endpoint", "")
        body = cmd.get("body")
        params = cmd.get("params")

        self._log("raw", "running", f"{method} {endpoint}")
        result = await self.ghl.request(method, endpoint, body=body, query_params=params)

        if result.get("success"):
            self._log("raw", "success", f"Status {result.get('status_code')}")
        else:
            self._log("raw", "error", result.get("error"))

        return result

    # ========================================================================
    # NEW HANDLERS — FULL API COVERAGE
    # ========================================================================

    # ----- CONTACTS: Extended -----

    async def _handle_get_contacts(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_contacts(**kwargs)
        contacts = result.get("data", {}).get("contacts", result.get("contacts", []))
        self._log("get_contacts", "success", f"Found {len(contacts)}")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_search_contacts_advanced(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_contacts_advanced(data)
        self._log("search_contacts_advanced", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_duplicate_contacts(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_duplicate_contacts(**kwargs)
        self._log("get_duplicate_contacts", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_contacts_by_business(self, cmd: dict) -> dict:
        bid = cmd.get("business_id", cmd.get("businessId", ""))
        kwargs = {k: v for k, v in cmd.items() if k not in ("action", "business_id", "businessId")}
        result = await self.ghl.get_contacts_by_business(bid, **kwargs)
        self._log("get_contacts_by_business", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_bulk_update_contact_tags(self, cmd: dict) -> dict:
        tag_type = cmd.get("type", "add")
        data = {k: v for k, v in cmd.items() if k not in ("action", "type")}
        result = await self.ghl.bulk_update_contact_tags(tag_type, data)
        self._log("bulk_update_contact_tags", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_add_contact_followers(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "contact_id", "contactId")}
        result = await self.ghl.add_contact_followers(cid, data)
        self._log("add_contact_followers", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_remove_contact_followers(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "contact_id", "contactId")}
        result = await self.ghl.remove_contact_followers(cid, data)
        self._log("remove_contact_followers", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_contact_note(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        nid = cmd.get("note_id", cmd.get("noteId", ""))
        result = await self.ghl.get_contact_note(cid, nid)
        self._log("get_contact_note", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_contact_note(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        nid = cmd.get("note_id", cmd.get("noteId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "contact_id", "contactId", "note_id", "noteId")}
        result = await self.ghl.update_contact_note(cid, nid, data)
        self._log("update_contact_note", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_contact_note(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        nid = cmd.get("note_id", cmd.get("noteId", ""))
        result = await self.ghl.delete_contact_note(cid, nid)
        self._log("delete_contact_note", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_contact_task(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        result = await self.ghl.get_contact_task(cid, tid)
        self._log("get_contact_task", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_contact_task(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "contact_id", "contactId", "task_id", "taskId")}
        result = await self.ghl.update_contact_task(cid, tid, data)
        self._log("update_contact_task", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_contact_task(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        result = await self.ghl.delete_contact_task(cid, tid)
        self._log("delete_contact_task", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_task_completed(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "contact_id", "contactId", "task_id", "taskId")}
        result = await self.ghl.update_task_completed(cid, tid, data)
        self._log("update_task_completed", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_remove_contact_from_all_campaigns(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        result = await self.ghl.remove_contact_from_all_campaigns(cid)
        self._log("remove_contact_from_all_campaigns", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_contact_appointments(self, cmd: dict) -> dict:
        cid = cmd.get("contact_id", cmd.get("contactId", ""))
        result = await self.ghl.get_contact_appointments(cid)
        self._log("get_contact_appointments", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- OPPORTUNITIES: Extended -----

    async def _handle_get_opportunity(self, cmd: dict) -> dict:
        oid = cmd.get("opportunity_id", cmd.get("opportunityId", self.results.get("opportunity_id", "")))
        result = await self.ghl.get_opportunity(oid)
        self._log("get_opportunity", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_add_opportunity_followers(self, cmd: dict) -> dict:
        oid = cmd.get("opportunity_id", cmd.get("opportunityId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "opportunity_id", "opportunityId")}
        result = await self.ghl.add_opportunity_followers(oid, data)
        self._log("add_opportunity_followers", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_remove_opportunity_followers(self, cmd: dict) -> dict:
        oid = cmd.get("opportunity_id", cmd.get("opportunityId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "opportunity_id", "opportunityId")}
        result = await self.ghl.remove_opportunity_followers(oid, data)
        self._log("remove_opportunity_followers", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CALENDAR: Groups -----

    async def _handle_get_calendar_groups(self, cmd: dict) -> dict:
        result = await self.ghl.get_calendar_groups()
        groups = result.get("data", {}).get("groups", [])
        self._log("get_calendar_groups", "success", f"Found {len(groups)}")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_calendar_group(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_calendar_group(data)
        self._log("create_calendar_group", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_calendar_group(self, cmd: dict) -> dict:
        gid = cmd.get("group_id", cmd.get("groupId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "group_id", "groupId")}
        result = await self.ghl.update_calendar_group(gid, data)
        self._log("update_calendar_group", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_calendar_group(self, cmd: dict) -> dict:
        gid = cmd.get("group_id", cmd.get("groupId", ""))
        result = await self.ghl.delete_calendar_group(gid)
        self._log("delete_calendar_group", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CALENDAR: Appointment Notes -----

    async def _handle_get_appointment_notes(self, cmd: dict) -> dict:
        aid = cmd.get("appointment_id", cmd.get("appointmentId", ""))
        result = await self.ghl.get_appointment_notes(aid)
        self._log("get_appointment_notes", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_appointment_note(self, cmd: dict) -> dict:
        aid = cmd.get("appointment_id", cmd.get("appointmentId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "appointment_id", "appointmentId")}
        result = await self.ghl.create_appointment_note(aid, data)
        self._log("create_appointment_note", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_appointment_note(self, cmd: dict) -> dict:
        aid = cmd.get("appointment_id", cmd.get("appointmentId", ""))
        nid = cmd.get("note_id", cmd.get("noteId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "appointment_id", "appointmentId", "note_id", "noteId")}
        result = await self.ghl.update_appointment_note(aid, nid, data)
        self._log("update_appointment_note", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_appointment_note(self, cmd: dict) -> dict:
        aid = cmd.get("appointment_id", cmd.get("appointmentId", ""))
        nid = cmd.get("note_id", cmd.get("noteId", ""))
        result = await self.ghl.delete_appointment_note(aid, nid)
        self._log("delete_appointment_note", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CALENDAR: Resources -----

    async def _handle_get_calendar_resources(self, cmd: dict) -> dict:
        rtype = cmd.get("resource_type", cmd.get("resourceType", "equipments"))
        result = await self.ghl.get_calendar_resources(rtype)
        self._log("get_calendar_resources", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_calendar_resource(self, cmd: dict) -> dict:
        rtype = cmd.get("resource_type", cmd.get("resourceType", "equipments"))
        data = {k: v for k, v in cmd.items() if k not in ("action", "resource_type", "resourceType")}
        result = await self.ghl.create_calendar_resource(rtype, data)
        self._log("create_calendar_resource", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CALENDAR: Blocked Slots -----

    async def _handle_get_blocked_slots(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_blocked_slots(**kwargs)
        self._log("get_blocked_slots", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CALENDAR: Get Appointment -----

    async def _handle_get_appointment(self, cmd: dict) -> dict:
        eid = cmd.get("event_id", cmd.get("appointment_id", cmd.get("appointmentId", "")))
        result = await self.ghl.get_appointment(eid)
        self._log("get_appointment", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_calendar_event(self, cmd: dict) -> dict:
        eid = cmd.get("event_id", cmd.get("eventId", ""))
        result = await self.ghl.delete_calendar_event(eid)
        self._log("delete_calendar_event", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- FUNNELS / REDIRECTS -----

    async def _handle_get_funnel_pages(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_funnel_pages(**kwargs)
        self._log("get_funnel_pages", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_redirects(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_redirects(**kwargs)
        self._log("get_redirects", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_redirect(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_redirect(data)
        self._log("create_redirect", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_redirect(self, cmd: dict) -> dict:
        rid = cmd.get("redirect_id", cmd.get("redirectId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "redirect_id", "redirectId")}
        result = await self.ghl.update_redirect(rid, data)
        self._log("update_redirect", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_redirect(self, cmd: dict) -> dict:
        rid = cmd.get("redirect_id", cmd.get("redirectId", ""))
        result = await self.ghl.delete_redirect(rid)
        self._log("delete_redirect", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CONVERSATIONS: Full Coverage -----

    async def _handle_get_conversation(self, cmd: dict) -> dict:
        cid = cmd.get("conversation_id", cmd.get("conversationId", ""))
        result = await self.ghl.get_conversation(cid)
        self._log("get_conversation", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_conversation(self, cmd: dict) -> dict:
        cid = cmd.get("conversation_id", cmd.get("conversationId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "conversation_id", "conversationId")}
        result = await self.ghl.update_conversation(cid, data)
        self._log("update_conversation", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_conversation(self, cmd: dict) -> dict:
        cid = cmd.get("conversation_id", cmd.get("conversationId", ""))
        result = await self.ghl.delete_conversation(cid)
        self._log("delete_conversation", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_messages(self, cmd: dict) -> dict:
        cid = cmd.get("conversation_id", cmd.get("conversationId", ""))
        result = await self.ghl.get_conversation_messages(cid)
        self._log("get_messages", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_message(self, cmd: dict) -> dict:
        mid = cmd.get("message_id", cmd.get("messageId", ""))
        result = await self.ghl.get_message(mid)
        self._log("get_message", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- INVOICES: Full Coverage -----

    async def _handle_create_invoice_template(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        data["locationId"] = self.ghl.location_id
        result = await self.ghl.create_invoice_template(data)
        tid = result.get("data", {}).get("_id", "")
        self._log("create_invoice_template", "success", f"Template ID: {tid}")
        self.results["invoice_template_id"] = tid
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_invoice_templates(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_invoice_templates(**kwargs)
        self._log("get_invoice_templates", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_invoice_template(self, cmd: dict) -> dict:
        tid = cmd.get("template_id", cmd.get("templateId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "template_id", "templateId")}
        result = await self.ghl.update_invoice_template(tid, data)
        self._log("update_invoice_template", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_invoice_template(self, cmd: dict) -> dict:
        tid = cmd.get("template_id", cmd.get("templateId", ""))
        result = await self.ghl.delete_invoice_template(tid)
        self._log("delete_invoice_template", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_invoice_schedule(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        data["locationId"] = self.ghl.location_id
        result = await self.ghl.create_invoice_schedule(data)
        self._log("create_invoice_schedule", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_invoice_schedules(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_invoice_schedules(**kwargs)
        self._log("get_invoice_schedules", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_generate_invoice_number(self, cmd: dict) -> dict:
        result = await self.ghl.generate_invoice_number()
        self._log("generate_invoice_number", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_estimate(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        data["locationId"] = self.ghl.location_id
        result = await self.ghl.create_estimate(data)
        self._log("create_estimate", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_estimates(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_estimates(**kwargs)
        self._log("get_estimates", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_estimate(self, cmd: dict) -> dict:
        eid = cmd.get("estimate_id", cmd.get("estimateId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "estimate_id", "estimateId")}
        result = await self.ghl.update_estimate(eid, data)
        self._log("update_estimate", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_estimate(self, cmd: dict) -> dict:
        eid = cmd.get("estimate_id", cmd.get("estimateId", ""))
        result = await self.ghl.delete_estimate(eid)
        self._log("delete_estimate", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_send_estimate(self, cmd: dict) -> dict:
        eid = cmd.get("estimate_id", cmd.get("estimateId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "estimate_id", "estimateId")}
        result = await self.ghl.send_estimate(eid, data)
        self._log("send_estimate", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- PAYMENTS: Full Coverage -----

    async def _handle_get_transaction(self, cmd: dict) -> dict:
        tid = cmd.get("transaction_id", cmd.get("transactionId", ""))
        result = await self.ghl.get_transaction(tid)
        self._log("get_transaction", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_subscription(self, cmd: dict) -> dict:
        sid = cmd.get("subscription_id", cmd.get("subscriptionId", ""))
        result = await self.ghl.get_subscription(sid)
        self._log("get_subscription", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_order_fulfillments(self, cmd: dict) -> dict:
        oid = cmd.get("order_id", cmd.get("orderId", ""))
        result = await self.ghl.get_order_fulfillments(oid)
        self._log("get_order_fulfillments", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_order_notes(self, cmd: dict) -> dict:
        oid = cmd.get("order_id", cmd.get("orderId", ""))
        result = await self.ghl.get_order_notes(oid)
        self._log("get_order_notes", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_record_order_payment(self, cmd: dict) -> dict:
        oid = cmd.get("order_id", cmd.get("orderId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "order_id", "orderId")}
        result = await self.ghl.record_order_payment(oid, data)
        self._log("record_order_payment", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- PRODUCTS: Full Coverage -----

    async def _handle_get_product(self, cmd: dict) -> dict:
        pid = cmd.get("product_id", cmd.get("productId", ""))
        result = await self.ghl.get_product(pid)
        self._log("get_product", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_product_prices(self, cmd: dict) -> dict:
        pid = cmd.get("product_id", cmd.get("productId", ""))
        result = await self.ghl.get_product_prices(pid)
        self._log("get_product_prices", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_product_price(self, cmd: dict) -> dict:
        pid = cmd.get("product_id", cmd.get("productId", ""))
        prid = cmd.get("price_id", cmd.get("priceId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "product_id", "productId", "price_id", "priceId")}
        result = await self.ghl.update_product_price(pid, prid, data)
        self._log("update_product_price", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_product_price(self, cmd: dict) -> dict:
        pid = cmd.get("product_id", cmd.get("productId", ""))
        prid = cmd.get("price_id", cmd.get("priceId", ""))
        result = await self.ghl.delete_product_price(pid, prid)
        self._log("delete_product_price", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_collections(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_collections(**kwargs)
        self._log("get_collections", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_collection(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_collection(data)
        self._log("create_collection", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_collection(self, cmd: dict) -> dict:
        cid = cmd.get("collection_id", cmd.get("collectionId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "collection_id", "collectionId")}
        result = await self.ghl.update_collection(cid, data)
        self._log("update_collection", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_collection(self, cmd: dict) -> dict:
        cid = cmd.get("collection_id", cmd.get("collectionId", ""))
        result = await self.ghl.delete_collection(cid)
        self._log("delete_collection", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_product_reviews(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_product_reviews(**kwargs)
        self._log("get_product_reviews", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_product_review(self, cmd: dict) -> dict:
        rid = cmd.get("review_id", cmd.get("reviewId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "review_id", "reviewId")}
        result = await self.ghl.update_product_review(rid, data)
        self._log("update_product_review", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_product_review(self, cmd: dict) -> dict:
        rid = cmd.get("review_id", cmd.get("reviewId", ""))
        result = await self.ghl.delete_product_review(rid)
        self._log("delete_product_review", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_inventory(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_inventory(**kwargs)
        self._log("get_inventory", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_inventory(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.update_inventory(data)
        self._log("update_inventory", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CUSTOM OBJECTS: Full CRUD -----

    async def _handle_get_object_schema(self, cmd: dict) -> dict:
        key = cmd.get("key", cmd.get("schema_key", cmd.get("schemaKey", "")))
        result = await self.ghl.get_object_schema(key)
        self._log("get_object_schema", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_object_schema(self, cmd: dict) -> dict:
        key = cmd.get("key", cmd.get("schema_key", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "key", "schema_key")}
        result = await self.ghl.update_object_schema(key, data)
        self._log("update_object_schema", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_object_record(self, cmd: dict) -> dict:
        sk = cmd.get("schema_key", cmd.get("schemaKey", ""))
        rid = cmd.get("record_id", cmd.get("recordId", ""))
        result = await self.ghl.get_object_record(sk, rid)
        self._log("get_object_record", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_object_record(self, cmd: dict) -> dict:
        sk = cmd.get("schema_key", cmd.get("schemaKey", ""))
        rid = cmd.get("record_id", cmd.get("recordId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "schema_key", "schemaKey", "record_id", "recordId")}
        result = await self.ghl.update_object_record(sk, rid, data)
        self._log("update_object_record", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_object_record(self, cmd: dict) -> dict:
        sk = cmd.get("schema_key", cmd.get("schemaKey", ""))
        rid = cmd.get("record_id", cmd.get("recordId", ""))
        result = await self.ghl.delete_object_record(sk, rid)
        self._log("delete_object_record", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- ASSOCIATIONS: Full CRUD -----

    async def _handle_get_association(self, cmd: dict) -> dict:
        aid = cmd.get("association_id", cmd.get("associationId", ""))
        result = await self.ghl.get_association(aid)
        self._log("get_association", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_association(self, cmd: dict) -> dict:
        aid = cmd.get("association_id", cmd.get("associationId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "association_id", "associationId")}
        result = await self.ghl.update_association(aid, data)
        self._log("update_association", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_association(self, cmd: dict) -> dict:
        aid = cmd.get("association_id", cmd.get("associationId", ""))
        result = await self.ghl.delete_association(aid)
        self._log("delete_association", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_relation(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_relation(data)
        self._log("create_relation", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_relations(self, cmd: dict) -> dict:
        rid = cmd.get("record_id", cmd.get("recordId", ""))
        result = await self.ghl.get_relations(rid)
        self._log("get_relations", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_relation(self, cmd: dict) -> dict:
        rid = cmd.get("relation_id", cmd.get("relationId", ""))
        result = await self.ghl.delete_relation(rid)
        self._log("delete_relation", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- STORE: Full Coverage -----

    async def _handle_get_shipping_zone(self, cmd: dict) -> dict:
        zid = cmd.get("zone_id", cmd.get("zoneId", ""))
        result = await self.ghl.get_shipping_zone(zid)
        self._log("get_shipping_zone", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_shipping_zone(self, cmd: dict) -> dict:
        zid = cmd.get("zone_id", cmd.get("zoneId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "zone_id", "zoneId")}
        result = await self.ghl.update_shipping_zone(zid, data)
        self._log("update_shipping_zone", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_shipping_zone(self, cmd: dict) -> dict:
        zid = cmd.get("zone_id", cmd.get("zoneId", ""))
        result = await self.ghl.delete_shipping_zone(zid)
        self._log("delete_shipping_zone", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_shipping_rates(self, cmd: dict) -> dict:
        zid = cmd.get("zone_id", cmd.get("zoneId", ""))
        result = await self.ghl.get_shipping_rates(zid)
        self._log("get_shipping_rates", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_shipping_rate(self, cmd: dict) -> dict:
        zid = cmd.get("zone_id", cmd.get("zoneId", ""))
        rid = cmd.get("rate_id", cmd.get("rateId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "zone_id", "zoneId", "rate_id", "rateId")}
        result = await self.ghl.update_shipping_rate(zid, rid, data)
        self._log("update_shipping_rate", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_shipping_rate(self, cmd: dict) -> dict:
        zid = cmd.get("zone_id", cmd.get("zoneId", ""))
        rid = cmd.get("rate_id", cmd.get("rateId", ""))
        result = await self.ghl.delete_shipping_rate(zid, rid)
        self._log("delete_shipping_rate", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_shipping_carrier(self, cmd: dict) -> dict:
        cid = cmd.get("carrier_id", cmd.get("carrierId", ""))
        result = await self.ghl.get_shipping_carrier(cid)
        self._log("get_shipping_carrier", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_shipping_carrier(self, cmd: dict) -> dict:
        cid = cmd.get("carrier_id", cmd.get("carrierId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "carrier_id", "carrierId")}
        result = await self.ghl.update_shipping_carrier(cid, data)
        self._log("update_shipping_carrier", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_shipping_carrier(self, cmd: dict) -> dict:
        cid = cmd.get("carrier_id", cmd.get("carrierId", ""))
        result = await self.ghl.delete_shipping_carrier(cid)
        self._log("delete_shipping_carrier", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- VOICE AI: Full Coverage -----

    async def _handle_get_voice_agent(self, cmd: dict) -> dict:
        aid = cmd.get("agent_id", cmd.get("agentId", ""))
        result = await self.ghl.get_voice_agent(aid)
        self._log("get_voice_agent", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_voice_action(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_voice_action(data)
        self._log("create_voice_action", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_voice_action(self, cmd: dict) -> dict:
        aid = cmd.get("action_id", cmd.get("actionId", ""))
        result = await self.ghl.get_voice_action(aid)
        self._log("get_voice_action", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_voice_action(self, cmd: dict) -> dict:
        aid = cmd.get("action_id", cmd.get("actionId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "action_id", "actionId")}
        result = await self.ghl.update_voice_action(aid, data)
        self._log("update_voice_action", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_voice_action(self, cmd: dict) -> dict:
        aid = cmd.get("action_id", cmd.get("actionId", ""))
        result = await self.ghl.delete_voice_action(aid)
        self._log("delete_voice_action", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_voice_call_log(self, cmd: dict) -> dict:
        cid = cmd.get("call_id", cmd.get("callId", ""))
        result = await self.ghl.get_voice_call_log(cid)
        self._log("get_voice_call_log", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- BLOGS: Full Coverage -----

    async def _handle_get_blog_authors(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_blog_authors(**kwargs)
        self._log("get_blog_authors", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_blog_categories(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_blog_categories(**kwargs)
        self._log("get_blog_categories", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- MEDIA: Full Coverage -----

    async def _handle_update_media_file(self, cmd: dict) -> dict:
        mid = cmd.get("media_id", cmd.get("mediaId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "media_id", "mediaId")}
        result = await self.ghl.update_media_file(mid, data)
        self._log("update_media_file", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_upload_media_file(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.upload_media_file(data)
        self._log("upload_media_file", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_bulk_delete_media(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.bulk_delete_media(data)
        self._log("bulk_delete_media", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- USERS: Full Coverage -----

    async def _handle_get_user(self, cmd: dict) -> dict:
        uid = cmd.get("user_id", cmd.get("userId", ""))
        result = await self.ghl.get_user(uid)
        self._log("get_user", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_search_users(self, cmd: dict) -> dict:
        cid = cmd.get("company_id", cmd.get("companyId", ""))
        kwargs = {k: v for k, v in cmd.items()
                  if k not in ("action", "company_id", "companyId")}
        result = await self.ghl.search_users(cid, **kwargs)
        self._log("search_users", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- LOCATIONS: Full Coverage -----

    async def _handle_search_locations(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_locations(**kwargs)
        self._log("search_locations", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_location(self, cmd: dict) -> dict:
        lid = cmd.get("location_id", cmd.get("locationId", ""))
        result = await self.ghl.delete_location(lid)
        self._log("delete_location", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_create_location(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_location(data)
        self._log("create_location", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_tag(self, cmd: dict) -> dict:
        tid = cmd.get("tag_id", cmd.get("tagId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "tag_id", "tagId")}
        result = await self.ghl.update_tag(tid, data)
        self._log("update_tag", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_search_tasks_location(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_tasks(data)
        self._log("search_tasks_location", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_custom_values(self, cmd: dict) -> dict:
        result = await self.ghl.get_custom_values()
        vals = result.get("data", {}).get("customValues", result.get("customValues", []))
        self._log("get_custom_values", "success", f"Found {len(vals)}")
        return {"success": True, "data": result.get("data", result)}

    # ----- RECURRING TASKS -----

    async def _handle_create_recurring_task(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_recurring_task(data)
        self._log("create_recurring_task", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_recurring_task(self, cmd: dict) -> dict:
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        result = await self.ghl.get_recurring_task(tid)
        self._log("get_recurring_task", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_recurring_task(self, cmd: dict) -> dict:
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "task_id", "taskId")}
        result = await self.ghl.update_recurring_task(tid, data)
        self._log("update_recurring_task", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_recurring_task(self, cmd: dict) -> dict:
        tid = cmd.get("task_id", cmd.get("taskId", ""))
        result = await self.ghl.delete_recurring_task(tid)
        self._log("delete_recurring_task", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- SNAPSHOTS -----

    async def _handle_create_snapshot_share_link(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_snapshot_share_link(data)
        self._log("create_snapshot_share_link", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CUSTOM FIELDS V2 -----

    async def _handle_create_custom_field_v2(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.create_custom_field_v2(data)
        self._log("create_custom_field_v2", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_update_custom_field_v2(self, cmd: dict) -> dict:
        fid = cmd.get("field_id", cmd.get("fieldId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "field_id", "fieldId")}
        result = await self.ghl.update_custom_field_v2(fid, data)
        self._log("update_custom_field_v2", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_custom_field_v2(self, cmd: dict) -> dict:
        fid = cmd.get("field_id", cmd.get("fieldId", ""))
        result = await self.ghl.delete_custom_field_v2(fid)
        self._log("delete_custom_field_v2", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_get_custom_fields_by_object(self, cmd: dict) -> dict:
        okey = cmd.get("object_key", cmd.get("objectKey", ""))
        kwargs = {k: v for k, v in cmd.items() if k not in ("action", "object_key", "objectKey")}
        result = await self.ghl.get_custom_fields_by_object(okey, **kwargs)
        self._log("get_custom_fields_by_object", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- SOCIAL MEDIA: Extended -----

    async def _handle_search_social_posts(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_social_posts(data)
        self._log("search_social_posts", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_bulk_delete_social_posts(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.bulk_delete_social_posts(data)
        self._log("bulk_delete_social_posts", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- EMAIL CAMPAIGNS -----

    async def _handle_get_email_campaigns(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.get_email_campaigns(**kwargs)
        self._log("get_email_campaigns", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- COURSES -----

    async def _handle_import_courses(self, cmd: dict) -> dict:
        data = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.import_courses(data)
        self._log("import_courses", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- COMPANIES -----

    async def _handle_get_company(self, cmd: dict) -> dict:
        cid = cmd.get("company_id", cmd.get("companyId", ""))
        result = await self.ghl.get_company(cid)
        self._log("get_company", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CONVERSATIONS: Search -----

    async def _handle_search_conversations(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_conversations(**kwargs)
        self._log("search_conversations", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- BUSINESS: Get single -----

    async def _handle_get_business(self, cmd: dict) -> dict:
        bid = cmd.get("business_id", cmd.get("businessId", ""))
        result = await self.ghl.get_business(bid)
        self._log("get_business", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- LINKS: Search & Get single -----

    async def _handle_get_link(self, cmd: dict) -> dict:
        lid = cmd.get("link_id", cmd.get("linkId", ""))
        result = await self.ghl.get_link(lid)
        self._log("get_link", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_search_links(self, cmd: dict) -> dict:
        kwargs = {k: v for k, v in cmd.items() if k != "action"}
        result = await self.ghl.search_links(**kwargs)
        self._log("search_links", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CUSTOM VALUES: Update/Delete -----

    async def _handle_update_custom_value(self, cmd: dict) -> dict:
        vid = cmd.get("value_id", cmd.get("valueId", cmd.get("id", "")))
        name = cmd.get("name", "")
        value = cmd.get("value", "")
        result = await self.ghl.update_custom_value(vid, name, value)
        self._log("update_custom_value", "success")
        return {"success": True, "data": result.get("data", result)}

    async def _handle_delete_custom_value(self, cmd: dict) -> dict:
        vid = cmd.get("value_id", cmd.get("valueId", cmd.get("id", "")))
        result = await self.ghl.delete_custom_value(vid)
        self._log("delete_custom_value", "success")
        return {"success": True, "data": result.get("data", result)}

    # ----- CUSTOM FIELD: Update -----

    async def _handle_update_custom_field(self, cmd: dict) -> dict:
        fid = cmd.get("field_id", cmd.get("fieldId", ""))
        data = {k: v for k, v in cmd.items() if k not in ("action", "field_id", "fieldId")}
        result = await self.ghl.update_custom_field(fid, data)
        self._log("update_custom_field", "success")
        return {"success": True, "data": result.get("data", result)}

    # ========================================================================
    # FULL FUNNEL BUILDER (Orchestrator)
    # ========================================================================

    async def _handle_create_funnel(self, cmd: dict) -> dict:
        """
        Build a complete digital funnel by running a sequence of API calls.

        This is the main orchestrator. It takes a funnel spec and runs
        every step in order:

        1. Create tags
        2. Create custom fields
        3. Create custom values
        4. Create email/SMS templates
        5. Create contacts (if importing)
        6. Create opportunities
        7. (Workflows — requires browser, flagged for manual or browser engine)

        Input spec:
        {
            "action": "create_funnel",
            "name": "Real Estate Lead Gen",
            "tags": ["new-lead", "real-estate", "funnel-v1"],
            "custom_fields": [
                {"name": "Property Interest", "data_type": "SINGLE_OPTIONS",
                 "options": ["Apartment", "House", "Commercial"]},
                {"name": "Budget Range", "data_type": "TEXT"},
            ],
            "custom_values": [
                {"name": "company.name", "value": "PrimeFlow Real Estate"},
                {"name": "company.phone", "value": "+972-50-123-4567"},
            ],
            "templates": [
                {"type": "email", "name": "Welcome Email",
                 "subject": "ברוכים הבאים!", "html": "<h1>שלום!</h1>"},
                {"type": "sms", "name": "Welcome SMS",
                 "body": "שלום! תודה שנרשמת. צוות PrimeFlow"},
            ],
            "contacts": [
                {"first_name": "ישראל", "last_name": "ישראלי",
                 "email": "test@example.com", "phone": "+972501234567"},
            ],
            "opportunities": [
                {"name": "New Lead", "pipeline_id": "...", "stage_id": "..."},
            ],
        }
        """
        funnel_name = cmd.get("name", "Unnamed Funnel")
        self._log("create_funnel", "running", funnel_name)
        results = {}

        # Step 1: Create tags
        if cmd.get("tags"):
            self._log("step_1_tags", "running", f"{len(cmd['tags'])} tags")
            tag_results = await self._handle_create_tags({"tags": cmd["tags"]})
            results["tags"] = tag_results

        # Step 2: Create custom fields
        if cmd.get("custom_fields"):
            self._log("step_2_custom_fields", "running",
                       f"{len(cmd['custom_fields'])} fields")
            field_results = await self._handle_create_custom_fields(
                {"fields": cmd["custom_fields"]})
            results["custom_fields"] = field_results

        # Step 3: Create custom values
        if cmd.get("custom_values"):
            self._log("step_3_custom_values", "running",
                       f"{len(cmd['custom_values'])} values")
            for cv in cmd["custom_values"]:
                cv["action"] = "create_custom_value"
                await self._handle_create_custom_value(cv)
            results["custom_values"] = {"success": True}

        # Step 4: Create templates
        if cmd.get("templates"):
            self._log("step_4_templates", "running",
                       f"{len(cmd['templates'])} templates")
            template_results = []
            for tmpl in cmd["templates"]:
                tmpl["action"] = "create_template"
                r = await self._handle_create_template(tmpl)
                template_results.append(r)
            results["templates"] = template_results

        # Step 5: Create/import contacts
        if cmd.get("contacts"):
            self._log("step_5_contacts", "running",
                       f"{len(cmd['contacts'])} contacts")
            contact_results = await self._handle_create_contacts(
                {"contacts": cmd["contacts"]})
            results["contacts"] = contact_results

        # Step 6: Create opportunities (if pipeline specified)
        if cmd.get("opportunities"):
            self._log("step_6_opportunities", "running",
                       f"{len(cmd['opportunities'])} opportunities")
            for opp in cmd["opportunities"]:
                opp["action"] = "create_opportunity"
                await self._handle_create_opportunity(opp)
            results["opportunities"] = {"success": True}

        # Step 7: Products (if specified)
        if cmd.get("products"):
            self._log("step_7_products", "running",
                       f"{len(cmd['products'])} products")
            for prod in cmd["products"]:
                prod["action"] = "create_product"
                await self._handle_create_product(prod)
            results["products"] = {"success": True}

        self._log("create_funnel", "success", f"Funnel '{funnel_name}' complete")

        return {
            "success": True,
            "funnel_name": funnel_name,
            "steps_completed": results,
            "stored_ids": self.results,
        }

    # ========================================================================
    # CLEANUP
    # ========================================================================

    async def close(self):
        await self.ghl.close()


# ============================================================================
# CLI INTERFACE — This is where you type your commands
# ============================================================================

async def run_from_cli():
    """
    Run engine commands from the command line.

    Usage:
        # Single command (inline JSON):
        python -m server.core.engine '{"action": "get_contacts"}'

        # Single command from JSON file:
        python -m server.core.engine funnel.json

        # Batch commands from JSON file (array of commands):
        python -m server.core.engine batch_commands.json

        # Run all JSON files from a directory (batch):
        python -m server.core.engine commands/

        # Interactive mode:
        python -m server.core.engine

        # List available actions:
        python -m server.core.engine --help
    """
    # Load .env
    from pathlib import Path
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

    engine = PrimeFlowEngine()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        # --help: List all available actions
        if arg in ("--help", "-h", "--list"):
            result = await engine.run({"action": "list_actions"})
            actions = result.get("result", {}).get("actions", [])
            print("\n" + "=" * 50)
            print("  PrimeFlow Engine — Available Actions")
            print("=" * 50)
            for action in actions:
                print(f"    • {action}")
            print(f"\n  Total: {len(actions)} actions\n")
            print("  Usage:")
            print('    python -m server.core.engine \'{"action": "get_contacts"}\'')
            print('    python -m server.core.engine funnel.json')
            print('    python -m server.core.engine commands/')
            print()
            await engine.close()
            return

        # Directory mode: run all .json files in order
        if os.path.isdir(arg):
            json_files = sorted([
                os.path.join(arg, f) for f in os.listdir(arg)
                if f.endswith(".json")
            ])
            if not json_files:
                print(f"  ❌ No .json files found in {arg}")
                await engine.close()
                return

            print(f"\n  📂 Running {len(json_files)} command files from {arg}/\n")
            all_commands = []
            for jf in json_files:
                with open(jf) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    all_commands.extend(data)
                else:
                    all_commands.append(data)

            summary = await engine.run_batch(all_commands)
            print("\n--- Batch Summary ---")
            print(json.dumps({
                "total": summary["total"],
                "succeeded": summary["succeeded"],
                "failed": summary["failed"],
            }, indent=2, ensure_ascii=False))

        # JSON file mode
        elif arg.endswith(".json") and os.path.exists(arg):
            with open(arg) as f:
                command = json.load(f)

            # Handle list of commands (batch)
            if isinstance(command, list):
                summary = await engine.run_batch(command)
                print("\n--- Batch Summary ---")
                print(json.dumps({
                    "total": summary["total"],
                    "succeeded": summary["succeeded"],
                    "failed": summary["failed"],
                }, indent=2, ensure_ascii=False))
            else:
                result = await engine.run(command)
                print("\n--- Result ---")
                print(json.dumps(result.get("result", {}), indent=2,
                                 ensure_ascii=False, default=str))

        # Inline JSON mode
        else:
            command = json.loads(arg)
            result = await engine.run(command)
            print("\n--- Result ---")
            print(json.dumps(result.get("result", {}), indent=2,
                             ensure_ascii=False, default=str))
    else:
        # Interactive mode
        print("\n" + "=" * 50)
        print("  PrimeFlow Engine — Interactive Mode")
        print("=" * 50)
        print("\n  Type JSON commands or 'quit' to exit.")
        print("  Type 'help' to see available actions.")
        print()
        print("  Examples:")
        print('    {"action": "get_contacts"}')
        print('    {"action": "create_contact", "first_name": "Test", "email": "t@t.com"}')
        print('    {"action": "list_actions"}')
        print()

        while True:
            try:
                user_input = input("  primeflow> ").strip()
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                if not user_input:
                    continue
                if user_input.lower() == "help":
                    user_input = '{"action": "list_actions"}'

                command = json.loads(user_input)
                result = await engine.run(command)
                print("\n--- Result ---")
                print(json.dumps(result.get("result", {}), indent=2,
                                 ensure_ascii=False, default=str))
                print()

            except json.JSONDecodeError as e:
                print(f"  ❌ Invalid JSON: {e}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"  ❌ Error: {e}")

    await engine.close()
    print("\n  Goodbye! 👋\n")


if __name__ == "__main__":
    asyncio.run(run_from_cli())
