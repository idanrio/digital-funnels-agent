"""
PrimeFlow Orchestrator — Smart Execution Layer

Sits ON TOP of engine.py. Engine stays untouched for backwards compatibility.

Flow:
    1. PreflightAudit.run()    → GET all existing resources (concurrent)
    2. SmartExecutor.execute() → Compare, deduplicate, create/update/skip
    3. ReportTracker            → Collect all results
    4. ReportGenerator          → Generate HTML + text report
    5. ReportEmailer           → Send to support@primeflow.ai

NO AI. Pure code. Deterministic. Fast.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from server.core.engine import PrimeFlowEngine
from server.integrations.ghl import GHLClient
from server.reports.report import (
    ActionResult, ReportData, ReportGenerator, ReportEmailer,
)
from server.utils.error_handler import (
    ErrorClassifier, SmartRetry, ErrorTracker,
)


# ===========================================================================
# DEDUP MAP — Defines how to match existing resources for each action
# ===========================================================================

DEDUP_MAP: dict[str, dict[str, Any]] = {
    # action_name → {audit_key, match_on, on_match, id_field}
    "create_custom_field": {
        "audit_key": "custom_fields",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_custom_value": {
        "audit_key": "custom_values",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "update",
        "update_action": "update_custom_value",
        "id_field": "id",
    },
    "create_tag": {
        "audit_key": "tags",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_contact": {
        "audit_key": "contacts",
        "match_on": "email",
        "cmd_field": "email",
        "on_match": "update",
        "update_action": "update_contact",
        "id_field": "id",
    },
    "create_opportunity": {
        "audit_key": "opportunities",
        "match_on": "contact_pipeline",
        "cmd_field": "name",
        "on_match": "update",
        "update_action": "update_opportunity",
        "id_field": "id",
    },
    "create_calendar": {
        "audit_key": "calendars",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_template": {
        "audit_key": "templates",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_user": {
        "audit_key": "users",
        "match_on": "email",
        "cmd_field": "email",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_ai_agent": {
        "audit_key": "ai_agents",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_knowledge_base": {
        "audit_key": "knowledge_bases",
        "match_on": "name",
        "cmd_field": "name",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_kb_faq": {
        "audit_key": "kb_faqs",
        "match_on": "question",
        "cmd_field": "question",
        "on_match": "update",
        "update_action": "update_kb_faq",
        "id_field": "id",
    },
    "create_custom_object": {
        "audit_key": "custom_objects",
        "match_on": "key",
        "cmd_field": "key",
        "on_match": "skip",
        "id_field": "id",
    },
    "create_association": {
        "audit_key": "associations",
        "match_on": "key",
        "cmd_field": "key",
        "on_match": "skip",
        "id_field": "id",
    },
}

# Category labels for reporting
ACTION_TO_CATEGORY: dict[str, str] = {
    "create_custom_field": "custom_fields",
    "create_custom_value": "custom_values",
    "create_tag": "tags",
    "create_contact": "contacts",
    "create_opportunity": "opportunities",
    "create_calendar": "calendars",
    "create_template": "templates",
    "create_user": "users",
    "create_ai_agent": "ai_agents",
    "create_knowledge_base": "knowledge_bases",
    "create_kb_faq": "kb_faqs",
    "create_custom_object": "custom_objects",
    "create_association": "associations",
    "create_calendar_notification": "calendar_notifications",
    "update_custom_value": "custom_values",
    "update_contact": "contacts",
    "update_opportunity": "opportunities",
    "update_kb_faq": "kb_faqs",
    "update_tag": "tags",
    "update_calendar": "calendars",
    "update_user": "users",
    "update_ai_agent": "ai_agents",
    "update_opportunity_status": "opportunities",
    "update_product": "products",
    "update_blog_post": "blogs",
    "update_custom_menu": "custom_menus",
    "update_business": "businesses",
    "update_link": "links",
    "update_voice_agent": "voice_agents",
    "send_email": "messaging",
    "send_sms": "messaging",
    "raw": "raw_api",
}


# ===========================================================================
# UPDATE LOOKUP MAP — Smart ID Resolution for update_* commands
# ===========================================================================
# When an update_* command comes in without the required ID but WITH a
# lookup field (name, email, etc.), the orchestrator resolves the ID
# from the preflight snapshot.
#
# Format:
#   update_action → {
#       "audit_key": which snapshot key to search,
#       "lookup_field": field in snapshot to match against,
#       "cmd_field": field in command to match with,
#       "id_field": field in snapshot containing the ID,
#       "cmd_id_field": field name to inject into the command
#   }

UPDATE_LOOKUP_MAP: dict[str, dict[str, str]] = {
    "update_contact": {
        "audit_key": "contacts",
        "lookup_field": "email",
        "cmd_field": "email",
        "id_field": "id",
        "cmd_id_field": "contact_id",
    },
    "update_tag": {
        "audit_key": "tags",
        "lookup_field": "name",
        "cmd_field": "current_name",  # user provides current name for lookup
        "id_field": "id",
        "cmd_id_field": "tag_id",
    },
    "update_calendar": {
        "audit_key": "calendars",
        "lookup_field": "name",
        "cmd_field": "current_name",
        "id_field": "id",
        "cmd_id_field": "calendar_id",
    },
    "update_ai_agent": {
        "audit_key": "ai_agents",
        "lookup_field": "name",
        "cmd_field": "current_name",
        "id_field": "id",
        "cmd_id_field": "agent_id",
    },
    "update_user": {
        "audit_key": "users",
        "lookup_field": "email",
        "cmd_field": "email",
        "id_field": "id",
        "cmd_id_field": "user_id",
    },
    "update_custom_value": {
        "audit_key": "custom_values",
        "lookup_field": "name",
        "cmd_field": "name",
        "id_field": "id",
        "cmd_id_field": "value_id",
    },
    "update_kb_faq": {
        "audit_key": "kb_faqs",
        "lookup_field": "question",
        "cmd_field": "current_question",
        "id_field": "id",
        "cmd_id_field": "faq_id",
    },
    "update_opportunity": {
        "audit_key": "opportunities",
        "lookup_field": "name",
        "cmd_field": "current_name",
        "id_field": "id",
        "cmd_id_field": "opportunity_id",
    },
}


# ===========================================================================
# COMMAND DETAIL EXTRACTOR — Extract rich properties for reporting
# ===========================================================================

# Maps action → list of (cmd_key, display_label) to extract from the command
_DETAIL_KEYS: dict[str, list[tuple[str, str]]] = {
    "create_custom_field": [
        ("data_type", "Type"), ("dataType", "Type"),
        ("placeholder", "Placeholder"),
        ("options", "Options"),
    ],
    "create_custom_value": [
        ("value", "Value"),
    ],
    "create_tag": [],
    "create_contact": [
        ("email", "Email"), ("phone", "Phone"),
        ("first_name", "First Name"), ("firstName", "First Name"),
        ("last_name", "Last Name"), ("lastName", "Last Name"),
        ("companyName", "Company"), ("source", "Source"),
        ("tags", "Tags"),
    ],
    "create_opportunity": [
        ("monetary_value", "Value"), ("monetaryValue", "Value"),
        ("status", "Status"),
        ("pipeline_id", "Pipeline"), ("pipelineId", "Pipeline"),
        ("stage_id", "Stage"), ("stageId", "Stage"),
        ("contact_id", "Contact"), ("contactId", "Contact"),
    ],
    "create_calendar": [
        ("calendarType", "Type"), ("slotDuration", "Slot Duration"),
        ("description", "Description"),
    ],
    "create_template": [
        ("type", "Type"), ("subject", "Subject"),
        ("body", "Body"),
    ],
    "create_user": [
        ("email", "Email"), ("phone", "Phone"),
        ("first_name", "First Name"), ("firstName", "First Name"),
        ("last_name", "Last Name"), ("lastName", "Last Name"),
        ("role", "Role"), ("type", "Account Type"),
    ],
    "create_ai_agent": [
        ("business_name", "Business"), ("businessName", "Business"),
        ("mode", "Mode"),
        ("personality", "Personality"),
        ("goal", "Goal"),
    ],
    "create_knowledge_base": [
        ("description", "Description"),
    ],
    "create_kb_faq": [
        ("question", "Question"), ("answer", "Answer"),
    ],
    "create_custom_object": [
        ("key", "Key"), ("description", "Description"),
    ],
    "create_association": [
        ("key", "Key"),
        ("firstObjectKey", "Object A"), ("secondObjectKey", "Object B"),
        ("firstObjectToSecondObjectCardinality", "Cardinality"),
    ],
    "create_calendar_notification": [
        ("channel", "Channel"), ("notificationType", "Type"),
        ("receiverType", "Receiver"), ("body", "Message"),
    ],
}


def _describe_command(cmd: dict) -> dict:
    """
    Extract meaningful properties from a command for report detail.
    Returns a dict of {label: value} pairs.
    """
    action = cmd.get("action", "")
    keys = _DETAIL_KEYS.get(action, [])
    props: dict[str, str] = {}
    seen_labels: set[str] = set()

    for cmd_key, label in keys:
        if label in seen_labels:
            continue
        val = cmd.get(cmd_key)
        if val is not None and val != "":
            # Truncate long strings
            if isinstance(val, str) and len(val) > 80:
                val = val[:77] + "..."
            elif isinstance(val, list):
                if len(val) <= 6:
                    val = ", ".join(str(v) for v in val)
                else:
                    val = ", ".join(str(v) for v in val[:5]) + f"... (+{len(val)-5})"
            props[label] = str(val)
            seen_labels.add(label)

    # Also include action name as "Action"
    props["Action"] = action

    return props


def _describe_match(match: dict, action: str) -> dict:
    """
    Extract meaningful properties from an existing matched resource.
    """
    props: dict[str, str] = {}
    # Common fields to pull from existing resources
    for key, label in [
        ("name", "Name"), ("email", "Email"), ("key", "Key"),
        ("dataType", "Type"), ("data_type", "Type"),
        ("phone", "Phone"), ("companyName", "Company"),
        ("calendarType", "Calendar Type"), ("type", "Type"),
        ("mode", "Mode"), ("status", "Status"),
        ("value", "Value"),
    ]:
        val = match.get(key)
        if val and label not in props:
            if isinstance(val, str) and len(val) > 80:
                val = val[:77] + "..."
            props[label] = str(val)
    return props


# ===========================================================================
# PREFLIGHT AUDIT — GET all existing resources concurrently
# ===========================================================================

class PreflightAudit:
    """
    Fetch ALL existing resources from GHL location before any creation.
    Uses asyncio.gather() for maximum speed.
    """

    @staticmethod
    async def run(engine: PrimeFlowEngine) -> dict[str, Any]:
        """
        Run full preflight audit.

        Returns:
            {
                "location": {...},
                "custom_fields": [...],
                "custom_values": [...],
                "tags": [...],
                "pipelines": [...],
                "contacts": [...],
                "custom_objects": [...],
                "associations": [...],
                "ai_agents": [...],
                "users": [...],
                "calendars": [...],
                "funnels": [...],
                "templates": [...],
                "workflows": [...],
                "knowledge_bases": [...],
                "opportunities": [...],
            }
        """
        print("\n" + "=" * 60)
        print("  PREFLIGHT AUDIT — Fetching all existing resources...")
        print("=" * 60 + "\n")

        ghl = engine.ghl
        snapshot: dict[str, Any] = {}

        # Define all GET tasks
        async def _get_location():
            r = await ghl.get_location(ghl.location_id)
            loc = r.get("data", {}).get("location", r.get("data", {}))
            snapshot["location"] = loc
            return loc

        async def _get_custom_fields():
            r = await ghl.get_custom_fields()
            data = r.get("data", {}).get("customFields", [])
            snapshot["custom_fields"] = data
            return data

        async def _get_custom_values():
            r = await ghl.get_custom_values()
            data = r.get("data", {}).get("customValues", [])
            snapshot["custom_values"] = data
            return data

        async def _get_tags():
            r = await ghl.get_tags()
            data = r.get("data", {}).get("tags", [])
            snapshot["tags"] = data
            return data

        async def _get_pipelines():
            r = await ghl.get_pipelines()
            data = r.get("data", {}).get("pipelines", [])
            snapshot["pipelines"] = data
            return data

        async def _get_contacts():
            # Get ALL contacts — paginate until no more pages
            # GHL uses startAfterId cursor (not offset), limit max 100
            all_contacts = []
            limit = 100
            start_after = ""
            max_pages = 50  # Safety cap: 5000 contacts max
            for page in range(max_pages):
                params = {
                    "locationId": ghl.location_id,
                    "limit": limit,
                }
                if start_after:
                    params["startAfterId"] = start_after
                r = await ghl.request("GET", "/contacts/",
                                      query_params=params)
                raw = r.get("data", {})
                batch = raw.get("contacts", [])
                all_contacts.extend(batch)
                # Check for next page
                meta = raw.get("meta", {})
                start_after = meta.get("startAfterId", "")
                if len(batch) < limit or not start_after:
                    break
            snapshot["contacts"] = all_contacts
            return all_contacts

        async def _get_custom_objects():
            r = await ghl.request("GET", "/objects/",
                                  query_params={"locationId": ghl.location_id})
            data = r.get("data", {}).get("objects", [])
            snapshot["custom_objects"] = data
            return data

        async def _get_associations():
            r = await ghl.request("GET", "/associations/",
                                  query_params={"locationId": ghl.location_id})
            raw = r.get("data", {})
            data = raw.get("associations", raw.get("data", []))
            if not isinstance(data, list):
                data = []
            snapshot["associations"] = data
            return data

        async def _get_ai_agents():
            r = await ghl.get_ai_agents()
            raw = r.get("data", {})
            data = raw if isinstance(raw, list) else raw.get("agents", [])
            snapshot["ai_agents"] = data
            return data

        async def _get_users():
            # Need companyId from location — retry if location fetch failed
            loc = snapshot.get("location", {})
            company_id = loc.get("companyId", "")
            if not company_id:
                # Retry location fetch once
                try:
                    r = await ghl.get_location(ghl.location_id)
                    loc = r.get("data", {}).get("location", r.get("data", {}))
                    company_id = loc.get("companyId", "")
                    if loc:
                        snapshot["location"] = loc
                except Exception:
                    pass
            if not company_id:
                print("    [!] Users: companyId not available, skipping")
                snapshot["users"] = []
                return []
            # Use /users/search which works with private integration keys
            r = await ghl.request(
                "GET", "/users/search",
                query_params={
                    "companyId": company_id,
                    "locationId": ghl.location_id,
                })
            data = r.get("data", {}).get("users", [])
            snapshot["users"] = data
            return data

        async def _get_calendars():
            r = await ghl.get_calendars()
            data = r.get("data", {}).get("calendars", [])
            snapshot["calendars"] = data
            return data

        async def _get_funnels():
            r = await ghl.request(
                "GET", "/funnels/lookup",
                query_params={"locationId": ghl.location_id})
            raw = r.get("data", {})
            data = raw.get("funnels", raw.get("data", []))
            if not isinstance(data, list):
                data = []
            snapshot["funnels"] = data
            return data

        async def _get_templates():
            r = await ghl.get_templates()
            data = r.get("data", {}).get("templates", [])
            snapshot["templates"] = data
            return data

        async def _get_workflows():
            r = await ghl.get_workflows()
            data = r.get("data", {}).get("workflows", [])
            snapshot["workflows"] = data
            return data

        async def _get_knowledge_bases():
            try:
                r = await ghl.get_knowledge_bases()
                # GHL KB API response can be:
                #   {"data": [...]}               — list directly under data
                #   {"data": {"knowledgeBases": [...]}}
                #   {"data": {"data": [...]}}
                #   {"knowledgeBases": [...]}      — top-level
                raw = r.get("data", r)
                if raw is None:
                    raw = {}
                if isinstance(raw, list):
                    kb_list = raw
                elif isinstance(raw, dict):
                    kb_list = (
                        raw.get("knowledgeBases")
                        or raw.get("knowledge_bases")
                        or raw.get("data")
                        or []
                    )
                else:
                    kb_list = []
                if not isinstance(kb_list, list):
                    kb_list = []
                # Ensure all items are dicts
                snapshot["knowledge_bases"] = [
                    item for item in kb_list
                    if isinstance(item, dict)
                ]
            except Exception as e:
                print(f"    [!] Knowledge bases fetch failed: {e}")
                snapshot["knowledge_bases"] = []
            return snapshot["knowledge_bases"]

        async def _get_opportunities():
            # Get all opportunities from all pipelines
            all_opps = []
            pipelines = snapshot.get("pipelines", [])
            for p in pipelines:
                pid = p.get("id", "")
                if pid:
                    r = await ghl.request(
                        "GET", "/opportunities/search",
                        query_params={
                            "location_id": ghl.location_id,
                            "pipeline_id": pid,
                            "limit": 100,
                        })
                    opps = r.get("data", {}).get("opportunities", [])
                    all_opps.extend(opps)
            snapshot["opportunities"] = all_opps
            return all_opps

        # Phase 1: Get location first (needed for users companyId)
        await _get_location()

        # Phase 2: Everything else in parallel
        phase2_tasks = [
            ("custom_fields", _get_custom_fields()),
            ("custom_values", _get_custom_values()),
            ("tags", _get_tags()),
            ("pipelines", _get_pipelines()),
            ("contacts", _get_contacts()),
            ("custom_objects", _get_custom_objects()),
            ("associations", _get_associations()),
            ("ai_agents", _get_ai_agents()),
            ("users", _get_users()),
            ("calendars", _get_calendars()),
            ("funnels", _get_funnels()),
            ("templates", _get_templates()),
            ("workflows", _get_workflows()),
            ("knowledge_bases", _get_knowledge_bases()),
        ]
        results = await asyncio.gather(
            *(task for _, task in phase2_tasks),
            return_exceptions=True,
        )
        # Check for failed GETs and ensure snapshot has safe defaults
        for (name, _), result in zip(phase2_tasks, results):
            if isinstance(result, Exception):
                print(f"    [!] Preflight GET {name} failed: {result}")
                if name not in snapshot:
                    snapshot[name] = []

        # Phase 3: Opportunities (needs pipelines from phase 2)
        try:
            await _get_opportunities()
        except Exception as e:
            print(f"    [!] Preflight GET opportunities failed: {e}")
            snapshot.setdefault("opportunities", [])

        # Print summary
        print("  Preflight Audit Complete:")
        for key, val in snapshot.items():
            if key == "location":
                name = val.get("name", val.get("businessName", "?"))
                print(f"    Location: {name}")
            elif isinstance(val, list):
                print(f"    {key}: {len(val)} found")
        print()

        return snapshot


# ===========================================================================
# SMART EXECUTOR — Compare existing vs. requested, create/update/skip
# ===========================================================================

class SmartExecutor:
    """
    Execute commands with smart deduplication.
    Compares each command against the preflight snapshot.
    """

    @staticmethod
    def _find_match(
        snapshot: dict[str, Any],
        action: str,
        cmd: dict,
    ) -> dict | None:
        """
        Find an existing resource that matches this command.

        Returns the matching resource dict, or None.
        """
        dedup = DEDUP_MAP.get(action)
        if not dedup:
            return None

        audit_key = dedup["audit_key"]
        match_field = dedup["match_on"]
        cmd_field = dedup["cmd_field"]

        existing_list = snapshot.get(audit_key, [])
        cmd_value = cmd.get(cmd_field, "")

        # Auto-generate key for custom objects if not provided
        if not cmd_value and action == "create_custom_object":
            from server.core.engine import PrimeFlowEngine
            labels = cmd.get("labels", {})
            if not labels:
                name = cmd.get("name", "")
                if name:
                    labels = {"singular": name, "plural": f"{name}s"}
            plural = labels.get("plural", labels.get("singular", ""))
            if plural:
                slug = PrimeFlowEngine._to_english_slug(plural)
                cmd_value = f"custom_objects.{slug}"
                # Also set it on cmd so the handler can use it
                cmd["key"] = cmd_value

        if not cmd_value:
            return None

        # Normalize for comparison
        cmd_value_lower = str(cmd_value).lower().strip()

        if match_field == "contact_pipeline":
            # Special: match by contact_id + pipeline_id
            cmd_contact = cmd.get("contact_id", cmd.get("contactId", ""))
            cmd_pipeline = cmd.get("pipeline_id", cmd.get("pipelineId", ""))
            for existing in existing_list:
                if not isinstance(existing, dict):
                    continue
                e_contact = existing.get("contact", {}).get("id",
                            existing.get("contactId", ""))
                e_pipeline = existing.get("pipelineId", "")
                if e_contact == cmd_contact and e_pipeline == cmd_pipeline:
                    return existing
        else:
            # Standard field match
            for existing in existing_list:
                if not isinstance(existing, dict):
                    continue
                existing_value = str(existing.get(match_field, "")).lower().strip()
                if existing_value == cmd_value_lower:
                    return existing

        return None

    @staticmethod
    async def execute(
        engine: PrimeFlowEngine,
        commands: list[dict],
        snapshot: dict[str, Any],
    ) -> list[ActionResult]:
        """
        Execute commands with dedup awareness.

        For each command:
        - If match found and on_match == "skip": tag as duplicate
        - If match found and on_match == "update": run update action
        - If no match: run create action
        - If action not in DEDUP_MAP: run as-is (passthrough)
        """
        results: list[ActionResult] = []

        # --- Smart command ordering ---
        # Actions that depend on other created resources must run last.
        # Priority: create_ai_agent last (depends on calendars, custom fields),
        #           create_association near-last (depends on custom objects).
        _LATE_ACTIONS = {"create_association": 1, "create_ai_agent": 2}
        commands = sorted(
            commands,
            key=lambda c: _LATE_ACTIONS.get(c.get("action", ""), 0),
        )

        print("\n" + "=" * 60)
        print("  SMART EXECUTION — Processing commands...")
        print("=" * 60 + "\n")

        for i, cmd in enumerate(commands, 1):
            action = cmd.get("action", "")
            category = ACTION_TO_CATEGORY.get(action, action)
            resource_name = cmd.get("name", "")
            if not resource_name:
                # Fallback name extraction for different action types
                if action == "create_calendar_notification":
                    ch = cmd.get("channel", "")
                    nt = cmd.get("notificationType", "")
                    rv = cmd.get("receiverType", "")
                    resource_name = f"{ch}/{nt} → {rv}"
                else:
                    resource_name = (
                        cmd.get("question", "")
                        or cmd.get("email", "")
                        or cmd.get("subject", "")
                        or action
                    )
            cmd_props = _describe_command(cmd)

            print(f"  [{i}/{len(commands)}] {action}: {resource_name[:50]}")

            # ---------------------------------------------------------------
            # SMART ID RESOLUTION + DIFF for update_* commands
            # 1. If missing ID → resolve from snapshot by name/email
            # 2. Compare new values vs existing → only send changed fields
            # 3. If nothing changed → report as duplicate (skip)
            # ---------------------------------------------------------------
            lookup = UPDATE_LOOKUP_MAP.get(action)
            if lookup:
                cmd_id_field = lookup["cmd_id_field"]
                has_id = bool(cmd.get(cmd_id_field, ""))

                # Meta fields to exclude from data comparison
                _meta_fields = {
                    "action", cmd_id_field,
                    "current_name", "current_question",
                }

                resolved_entry = None  # the existing resource from snapshot

                if not has_id:
                    # Try to resolve ID from snapshot
                    audit_key = lookup["audit_key"]
                    lookup_field = lookup["lookup_field"]
                    cmd_field = lookup["cmd_field"]
                    id_field = lookup["id_field"]

                    lookup_value = cmd.get(cmd_field, "")
                    if lookup_value:
                        lookup_lower = str(lookup_value).lower().strip()
                        existing_list = snapshot.get(audit_key, [])
                        for existing in existing_list:
                            if not isinstance(existing, dict):
                                continue
                            existing_val = str(
                                existing.get(lookup_field, "")
                            ).lower().strip()
                            if existing_val == lookup_lower:
                                resolved_entry = existing
                                break

                        if resolved_entry:
                            resolved_id = resolved_entry.get(id_field, "")
                            cmd[cmd_id_field] = resolved_id
                            # Remove lookup field so it doesn't confuse GHL
                            if cmd_field.startswith("current_"):
                                cmd.pop(cmd_field, None)
                            print(
                                f"    🔍 RESOLVED {cmd_id_field} from "
                                f"'{lookup_value}' → {resolved_id[:16]}..."
                            )
                        else:
                            # Cannot resolve — report error
                            print(
                                f"    ❌ Cannot resolve {cmd_id_field}: "
                                f"'{lookup_value}' not found in {audit_key}"
                            )
                            results.append(ActionResult(
                                action=action,
                                status="error",
                                category=category,
                                resource_name=resource_name,
                                error=(
                                    f"Cannot find {audit_key} with "
                                    f"{lookup_field}='{lookup_value}' — "
                                    f"provide {cmd_id_field} directly or "
                                    f"check that the resource exists."
                                ),
                                properties=cmd_props,
                            ))
                            continue
                    elif not has_id:
                        # No ID and no lookup value — error
                        print(
                            f"    ❌ Missing {cmd_id_field} and no "
                            f"'{cmd_field}' to look up"
                        )
                        results.append(ActionResult(
                            action=action,
                            status="error",
                            category=category,
                            resource_name=resource_name,
                            error=(
                                f"Missing required '{cmd_id_field}'. "
                                f"Provide the ID directly or use "
                                f"'{cmd_field}' for automatic lookup."
                            ),
                            properties=cmd_props,
                        ))
                        continue

                # --- SMART DIFF ---
                # Compare command fields vs existing snapshot entry.
                # Only keep fields that are NEW or CHANGED.
                # If nothing changed → duplicate (skip API call).
                if resolved_entry:
                    data_fields = {
                        k: v for k, v in cmd.items()
                        if k not in _meta_fields
                    }
                    changed_fields: dict = {}
                    for field_key, new_val in data_fields.items():
                        # GHL uses camelCase; try both snake_case and camelCase
                        existing_val = resolved_entry.get(field_key)
                        if existing_val is None:
                            # Try camelCase conversion (first_name → firstName)
                            parts = field_key.split("_")
                            camel = parts[0] + "".join(
                                p.capitalize() for p in parts[1:]
                            )
                            existing_val = resolved_entry.get(camel)

                        # Normalize for comparison
                        new_str = str(new_val).strip() if new_val is not None else ""
                        ext_str = str(existing_val).strip() if existing_val is not None else ""

                        if new_str.lower() != ext_str.lower():
                            changed_fields[field_key] = new_val

                    if not changed_fields:
                        # Everything is identical — DUPLICATE
                        resolved_id = cmd.get(cmd_id_field, "")
                        print(
                            f"    ⏭️  DUPLICATE — all values identical, "
                            f"nothing to update"
                        )
                        results.append(ActionResult(
                            action=action,
                            status="duplicate",
                            category=category,
                            resource_name=resource_name,
                            resource_id=resolved_id,
                            detail="All values identical — no update needed",
                            properties=cmd_props,
                        ))
                        continue
                    else:
                        # Keep only changed fields + required ID
                        diff_summary = ", ".join(
                            f"{k}" for k in changed_fields
                        )
                        print(
                            f"    📝 DIFF: {len(changed_fields)} field(s) "
                            f"changed: {diff_summary}"
                        )
                        # Rebuild cmd with only changed fields + ID + action
                        clean_cmd = {"action": action, cmd_id_field: cmd[cmd_id_field]}
                        clean_cmd.update(changed_fields)
                        cmd = clean_cmd

            dedup = DEDUP_MAP.get(action)

            if dedup:
                # Check for existing match
                match = SmartExecutor._find_match(snapshot, action, cmd)

                if match:
                    existing_id = match.get(dedup.get("id_field", "id"), "")
                    match_props = _describe_match(match, action)
                    # Merge: cmd_props (what was requested) + match props (what exists)
                    merged_props = {**cmd_props, **match_props}

                    if dedup["on_match"] == "skip":
                        # DUPLICATE — Skip
                        print(f"    ⏭️  DUPLICATE — skipping (existing: {existing_id[:12]}...)")
                        results.append(ActionResult(
                            action=action,
                            status="duplicate",
                            category=category,
                            resource_name=resource_name,
                            resource_id=existing_id,
                            detail=f"Already exists with ID {existing_id}",
                            properties=merged_props,
                        ))
                        # Register in engine for cross-command linking
                        # (even duplicates are "available" for AI agent actions)
                        if action == "create_calendar":
                            engine._register_created("calendars", {
                                "id": existing_id,
                                "name": cmd.get("name", ""),
                                "description": cmd.get("description", ""),
                                "calendarType": cmd.get("calendarType", "event"),
                                "slotDuration": cmd.get("slotDuration", 30),
                            })
                        elif action == "create_custom_field":
                            engine._register_created("custom_fields", {
                                "id": existing_id,
                                "name": cmd.get("name", ""),
                                "fieldKey": cmd.get("fieldKey", ""),
                                "dataType": cmd.get("data_type", cmd.get("dataType", "TEXT")),
                                "options": cmd.get("options", []),
                            })
                        continue

                    elif dedup["on_match"] == "update":
                        # UPDATE existing — with Smart Diff
                        update_action = dedup.get("update_action", "")
                        if update_action:
                            update_cmd = dict(cmd)
                            update_cmd["action"] = update_action

                            # Set the ID for the update
                            id_field_map = {
                                "create_contact": "contact_id",
                                "create_opportunity": "opportunity_id",
                                "create_custom_value": "value_id",
                                "create_kb_faq": "faq_id",
                            }
                            id_key = id_field_map.get(action, "")
                            if id_key:
                                update_cmd[id_key] = existing_id

                            # --- SMART DIFF for dedup-triggered updates ---
                            # Compare command fields vs existing snapshot
                            # Only send fields that are NEW or CHANGED
                            dedup_meta = {"action", id_key, "current_name",
                                          "current_question"}
                            data_fields = {
                                k: v for k, v in update_cmd.items()
                                if k not in dedup_meta
                            }
                            changed = {}
                            for fk, nv in data_fields.items():
                                ev = match.get(fk)
                                if ev is None:
                                    # Try camelCase
                                    parts = fk.split("_")
                                    camel = parts[0] + "".join(
                                        p.capitalize() for p in parts[1:]
                                    )
                                    ev = match.get(camel)
                                ns = str(nv).strip() if nv is not None else ""
                                es = str(ev).strip() if ev is not None else ""
                                if ns.lower() != es.lower():
                                    changed[fk] = nv

                            if not changed:
                                # All values identical — DUPLICATE
                                print(
                                    f"    ⏭️  DUPLICATE — all values "
                                    f"identical, nothing to update"
                                )
                                results.append(ActionResult(
                                    action=action,
                                    status="duplicate",
                                    category=category,
                                    resource_name=resource_name,
                                    resource_id=existing_id,
                                    detail=(
                                        "Already exists with identical "
                                        "data — no update needed"
                                    ),
                                    properties=merged_props,
                                ))
                                continue

                            # Rebuild cmd with only changed fields
                            diff_summary = ", ".join(changed.keys())
                            print(
                                f"    🔄 UPDATING {len(changed)} changed "
                                f"field(s): {diff_summary} "
                                f"(ID: {existing_id[:12]}...)"
                            )
                            clean_update = {
                                "action": update_action,
                                id_key: existing_id,
                            }
                            clean_update.update(changed)

                            r = await engine.run(clean_update)
                            success = r.get("result", {}).get("success", False)

                            if success:
                                results.append(ActionResult(
                                    action=update_action,
                                    status="updated",
                                    category=category,
                                    resource_name=resource_name,
                                    resource_id=existing_id,
                                    detail=f"Updated existing resource",
                                    properties=cmd_props,
                                ))
                                # Update snapshot with new data
                                _update_snapshot(snapshot, dedup["audit_key"],
                                                 existing_id, cmd)
                            else:
                                error_msg = r.get("result", {}).get("error", "Unknown")
                                status_code = r.get("result", {}).get("status_code", 0)
                                resp_body = r.get("result", {}).get("response_body", "")
                                print(f"    ❌ Update failed: {error_msg}")
                                results.append(ActionResult(
                                    action=update_action,
                                    status="error",
                                    category=category,
                                    resource_name=resource_name,
                                    resource_id=existing_id,
                                    error=str(error_msg),
                                    error_status_code=status_code,
                                    error_response=resp_body,
                                    properties=cmd_props,
                                ))
                            continue

                # No match found — create new
                print(f"    ➕ CREATING new resource")

            else:
                # No dedup map — passthrough
                if action.startswith("update_"):
                    print(f"    🔄 Executing update (direct)")
                else:
                    print(f"    ▶️  Executing (no dedup)")

            # Execute the command with SmartRetry for rate-limit/server errors
            retry_result = await SmartRetry.execute(
                engine.run, cmd, action_name=action)

            r_data = retry_result.get("data", {})
            success = retry_result.get("success", False)

            # Also check: if "success" is False but error is empty and
            # status_code is 0 or 200, treat as success (API returned data
            # but response format was unexpected)
            if not success and r_data and isinstance(r_data, dict):
                inner = r_data if not r_data.get("result") else r_data.get("result", {})
                err = inner.get("error", "")
                sc = inner.get("status_code", 0)
                if (not err or err == "Unknown") and sc in (0, 200, 201):
                    # Looks like success with unexpected format
                    success = True
                    r_data = inner

            if success:
                # Extract ID from result
                if isinstance(r_data, dict):
                    result_data = r_data.get("data", r_data)
                else:
                    result_data = r_data or {}
                new_id = _extract_id(result_data)
                attempts = retry_result.get("attempts", 1)
                retry_note = f" (after {attempts} attempts)" if attempts > 1 else ""

                # Determine if this is an update or create
                is_update = action.startswith("update_")
                status_label = "updated" if is_update else "created"
                verb = "Updated" if is_update else "Created"

                # For updates, prefer the resolved ID from the command
                if is_update and not new_id:
                    lookup = UPDATE_LOOKUP_MAP.get(action, {})
                    new_id = cmd.get(lookup.get("cmd_id_field", ""), "") or ""

                print(f"    ✅ {verb} (ID: {new_id[:12] if new_id else 'N/A'}...)"
                      f"{retry_note}")

                results.append(ActionResult(
                    action=action,
                    status=status_label,
                    category=category,
                    resource_name=resource_name,
                    resource_id=new_id,
                    detail=f"{verb} resource{retry_note}",
                    properties=cmd_props,
                ))

                # Add to snapshot for subsequent dedup checks
                if not is_update:
                    _add_to_snapshot(snapshot, action, result_data, cmd, new_id)
            else:
                # Get error details from inner result or retry wrapper
                inner = r_data.get("result", r_data) if isinstance(r_data, dict) else {}
                error_msg = inner.get("error", retry_result.get("error_detail", "Unknown"))
                status_code = inner.get("status_code", 0)
                resp_body = inner.get("response_body", "")

                # Check if error is actually a duplicate
                classified = ErrorClassifier.classify(
                    inner if isinstance(inner, dict) else {}, action)
                if classified.category == "duplicate":
                    print(f"    ⏭️  DUPLICATE (API rejected)")
                    results.append(ActionResult(
                        action=action,
                        status="duplicate",
                        category=category,
                        resource_name=resource_name,
                        error=str(error_msg),
                        detail="API rejected as duplicate",
                        properties=cmd_props,
                    ))
                else:
                    print(f"    ❌ Error: {error_msg}")
                    results.append(ActionResult(
                        action=action,
                        status="error",
                        category=category,
                        resource_name=resource_name,
                        error=str(error_msg),
                        error_status_code=status_code,
                        error_response=resp_body,
                        properties=cmd_props,
                    ))

        return results


def _extract_id(data: Any) -> str:
    """Extract resource ID from various API response formats."""
    if isinstance(data, dict):
        # Try common patterns
        for key in ("id", "_id", "contactId", "opportunityId"):
            if data.get(key):
                return str(data[key])
        # Nested patterns
        for wrapper in ("contact", "opportunity", "tag", "customField",
                        "customValue", "calendar", "template", "user",
                        "agent", "knowledgeBase"):
            inner = data.get(wrapper, {})
            if isinstance(inner, dict):
                for key in ("id", "_id"):
                    if inner.get(key):
                        return str(inner[key])
    return ""


def _add_to_snapshot(
    snapshot: dict, action: str, result_data: Any,
    cmd: dict, new_id: str,
):
    """Add newly created resource to snapshot for subsequent dedup."""
    dedup = DEDUP_MAP.get(action)
    if not dedup:
        return
    audit_key = dedup["audit_key"]
    match_field = dedup["match_on"]
    cmd_field = dedup["cmd_field"]

    new_entry = {"id": new_id}
    if match_field == "contact_pipeline":
        new_entry["contactId"] = cmd.get("contact_id", cmd.get("contactId", ""))
        new_entry["pipelineId"] = cmd.get("pipeline_id", cmd.get("pipelineId", ""))
    else:
        new_entry[match_field] = cmd.get(cmd_field, "")

    if audit_key not in snapshot:
        snapshot[audit_key] = []
    snapshot[audit_key].append(new_entry)


def _update_snapshot(
    snapshot: dict, audit_key: str,
    existing_id: str, cmd: dict,
):
    """Update snapshot entry after an update operation."""
    items = snapshot.get(audit_key, [])
    for item in items:
        if item.get("id") == existing_id:
            # Merge cmd fields into existing item
            for k, v in cmd.items():
                if k not in ("action",):
                    item[k] = v
            break


# ===========================================================================
# PRIMEFLOW ORCHESTRATOR — Main Entry Point
# ===========================================================================

class PrimeFlowOrchestrator:
    """
    Main orchestration layer. Wraps engine with:
    - Automatic preflight audit
    - Smart deduplication
    - Structured reporting
    - Email delivery
    """

    def __init__(self, engine: PrimeFlowEngine | None = None):
        self.engine = engine or PrimeFlowEngine()

    async def run(
        self,
        commands: list[dict],
        send_report: bool = True,
        report_subject: str = "",
    ) -> dict:
        """
        Execute commands with full orchestration.

        Args:
            commands: List of engine command dicts
            send_report: Whether to email the report
            report_subject: Custom subject for the report email

        Returns:
            {
                "snapshot": dict,
                "results": list[ActionResult],
                "report_data": ReportData,
                "report_html": str,
                "report_text": str,
                "email_result": dict,
            }
        """
        start_time = time.time()
        start_dt = datetime.now().isoformat()

        print("\n" + "=" * 70)
        print("  PRIMEFLOW ORCHESTRATOR")
        print(f"  Commands: {len(commands)}")
        print(f"  Started: {start_dt}")
        print("=" * 70)

        # Step 1: Preflight Audit
        snapshot = await PreflightAudit.run(self.engine)

        # Step 2: Smart Execution
        results = await SmartExecutor.execute(
            self.engine, commands, snapshot)

        # Step 3: Build Report Data
        end_dt = datetime.now().isoformat()
        duration = time.time() - start_time

        location = snapshot.get("location", {})
        report_data = ReportData(
            location_id=self.engine.ghl.location_id,
            location_name=location.get("name", ""),
            company_name=location.get("companyName",
                          location.get("company", {}).get("name", "")),
            business_phone=location.get("phone", location.get("businessPhone", "")),
            business_name=location.get("businessName",
                           location.get("business", {}).get("name", "")),
            results=results,
            start_time=start_dt,
            end_time=end_dt,
            duration_seconds=duration,
            generated_passwords=self.engine.generated_passwords,
        )

        # Step 4: Generate Reports (text + HTML email + HTML interactive + PDF)
        report_text = ReportGenerator.generate_text(report_data)
        report_html = ReportGenerator.generate_html(report_data)           # email: expanded
        report_html_i = ReportGenerator.generate_html_interactive(report_data)  # browser: dropdowns
        report_pdf = ReportGenerator.generate_pdf(report_data)

        # Print text report to console
        print("\n" + report_text)

        # Step 5: Send Report Email (with PDF)
        email_result = {"sent": False, "method": None, "detail": "Skipped"}
        if send_report:
            subject = report_subject or (
                f"PrimeFlow Report — "
                f"{len(report_data.created)} created, "
                f"{len(report_data.updated)} updated, "
                f"{len(report_data.duplicates)} dups, "
                f"{len(report_data.errors)} errors"
            )
            email_result = await ReportEmailer.send(
                self.engine, report_html, report_text,
                report_pdf_bytes=report_pdf, subject=subject,
                report_html_interactive=report_html_i)

        print("\n" + "=" * 70)
        print("  ORCHESTRATION COMPLETE")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Created: {len(report_data.created)}")
        print(f"  Updated: {len(report_data.updated)}")
        print(f"  Duplicates: {len(report_data.duplicates)}")
        print(f"  Errors: {len(report_data.errors)}")
        print(f"  Report: {email_result.get('method', 'N/A')}")
        print("=" * 70 + "\n")

        return {
            "snapshot": snapshot,
            "results": results,
            "report_data": report_data,
            "report_html": report_html,
            "report_text": report_text,
            "report_pdf": report_pdf,
            "email_result": email_result,
        }

    async def close(self):
        """Close the underlying engine."""
        await self.engine.close()
