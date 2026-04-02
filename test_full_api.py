"""
PrimeFlow Engine - FULL API TEST
Tests every single engine action against the live GHL demo account.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from server.core.engine import PrimeFlowEngine
from server.integrations.ghl import GHLClient


# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def record(self, action: str, result: dict, note: str = ""):
        success = result.get("result", result).get("success", False)
        status_code = result.get("result", result).get("status_code", "")
        error = result.get("result", result).get("error", "")

        if success:
            self.passed.append({"action": action, "note": note})
            print(f"  ✅ {action} — PASSED {note}")
        else:
            self.failed.append({
                "action": action,
                "status_code": status_code,
                "error": str(error)[:120],
                "note": note,
            })
            print(f"  ❌ {action} — FAILED ({status_code}) {str(error)[:80]}")

    def skip(self, action: str, reason: str):
        self.skipped.append({"action": action, "reason": reason})
        print(f"  ⏭️  {action} — SKIPPED ({reason})")

    def summary(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print(f"\n{'='*60}")
        print(f"  FULL API TEST RESULTS")
        print(f"{'='*60}")
        print(f"  ✅ Passed:  {len(self.passed)}")
        print(f"  ❌ Failed:  {len(self.failed)}")
        print(f"  ⏭️  Skipped: {len(self.skipped)}")
        print(f"  📊 Total:   {total}")
        pct = (len(self.passed) / (len(self.passed) + len(self.failed)) * 100) if (len(self.passed) + len(self.failed)) > 0 else 0
        print(f"  📈 Success Rate: {pct:.1f}%")
        print(f"{'='*60}")

        if self.failed:
            print(f"\n  FAILURES:")
            for f in self.failed:
                print(f"    ❌ {f['action']}: {f['error'][:100]}")

        if self.skipped:
            print(f"\n  SKIPPED:")
            for s in self.skipped:
                print(f"    ⏭️  {s['action']}: {s['reason']}")

        return {
            "passed": len(self.passed),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "total": total,
            "success_rate": f"{pct:.1f}%",
            "failures": self.failed,
        }


async def run_full_test():
    engine = PrimeFlowEngine()
    t = TestResults()

    # Store created IDs for later update/delete tests
    ids = {}

    print(f"\n{'='*60}")
    print(f"  PrimeFlow Engine — FULL API TEST")
    print(f"  Testing ALL actions against live GHL account")
    print(f"  Location: {engine.ghl.location_id}")
    print(f"  Time: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # ================================================================
    # PART 1: TAGS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 1: TAGS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "create_tag", "name": "test-api-full-v3"})
    t.record("create_tag", r)
    ids["tag_id"] = r.get("result", {}).get("data", {}).get("tag", {}).get("id", "")

    ts_short = datetime.now().strftime('%H%M%S')
    r = await engine.run({"action": "create_tags", "tags": [f"test-batch-1-{ts_short}", f"test-batch-2-{ts_short}"]})
    t.record("create_tags", r)

    r = await engine.run({"action": "get_tags"})
    t.record("get_tags", r)

    # ================================================================
    # PART 2: CUSTOM FIELDS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 2: CUSTOM FIELDS")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_custom_field",
        "name": f"Test Field API {ts_short}",
        "data_type": "TEXT",
        "placeholder": "Enter value..."
    })
    t.record("create_custom_field", r)
    ids["custom_field_id"] = r.get("result", {}).get("data", {}).get("customField", {}).get("id", "")

    r = await engine.run({
        "action": "create_custom_field",
        "name": f"Test Options {ts_short}",
        "data_type": "SINGLE_OPTIONS",
        "options": ["אפשרות א", "אפשרות ב", "אפשרות ג"]
    })
    t.record("create_custom_field (SINGLE_OPTIONS)", r)
    ids["custom_field_id_2"] = r.get("result", {}).get("data", {}).get("customField", {}).get("id", "")

    r = await engine.run({"action": "get_custom_fields"})
    t.record("get_custom_fields", r)

    # ================================================================
    # PART 3: CUSTOM VALUES
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 3: CUSTOM VALUES")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_custom_value",
        "name": f"test.company.{ts_short}",
        "value": "PrimeFlow Test Corp"
    })
    t.record("create_custom_value", r)

    r = await engine.run({"action": "get_custom_values"})
    t.record("get_custom_values", r)

    # ================================================================
    # PART 4: CONTACTS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 4: CONTACTS")
    print(f"{'─'*40}")

    ts = datetime.now().strftime('%H%M%S%f')[:8]
    r = await engine.run({
        "action": "create_contact",
        "first_name": "טסט",
        "last_name": "אוטומטי",
        "email": f"test-full-api-{ts}@primeflow-test.com",
        "phone": f"+97254{ts}",
        "tags": ["test-api-full-v3"],
        "source": "PrimeFlow Full API Test"
    })
    t.record("create_contact", r)
    ids["contact_id"] = r.get("result", {}).get("data", {}).get("contact", {}).get("id", "")

    r = await engine.run({
        "action": "create_contacts",
        "contacts": [
            {"first_name": "בדיקה", "last_name": "שני",
             "email": f"test2-{datetime.now().strftime('%H%M%S')}@primeflow-test.com"},
            {"first_name": "בדיקה", "last_name": "שלישי",
             "email": f"test3-{datetime.now().strftime('%H%M%S')}@primeflow-test.com"},
        ]
    })
    t.record("create_contacts (bulk)", r)

    if ids.get("contact_id"):
        r = await engine.run({"action": "get_contact", "contact_id": ids["contact_id"]})
        t.record("get_contact", r)

        r = await engine.run({"action": "search_contacts", "query": "טסט"})
        t.record("search_contacts", r)

        r = await engine.run({
            "action": "update_contact",
            "contact_id": ids["contact_id"],
            "data": {"firstName": "טסט-מעודכן", "companyName": "PrimeFlow Test"}
        })
        t.record("update_contact", r)

        r = await engine.run({
            "action": "add_contact_tags",
            "contact_id": ids["contact_id"],
            "tags": ["test-batch-1", "test-batch-2"]
        })
        t.record("add_contact_tags", r)

        r = await engine.run({
            "action": "remove_contact_tags",
            "contact_id": ids["contact_id"],
            "tags": ["test-batch-2"]
        })
        t.record("remove_contact_tags", r)

        r = await engine.run({
            "action": "upsert_contact",
            "email": f"test-full-api-{datetime.now().strftime('%H%M%S')}@primeflow-test.com",
            "first_name": "אפסרט",
            "last_name": "בדיקה",
            "phone": "+972509876543"
        })
        t.record("upsert_contact", r)

    # ================================================================
    # PART 5: NOTES & TASKS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 5: NOTES & TASKS")
    print(f"{'─'*40}")

    if ids.get("contact_id"):
        r = await engine.run({
            "action": "create_note",
            "contact_id": ids["contact_id"],
            "body": "הערת בדיקה מלאה — PrimeFlow Full API Test 🚀"
        })
        t.record("create_note", r)

        r = await engine.run({"action": "get_notes", "contact_id": ids["contact_id"]})
        t.record("get_notes", r)

        r = await engine.run({
            "action": "create_task",
            "contact_id": ids["contact_id"],
            "title": "משימת בדיקה — Full API Test",
            "body": "לבדוק שכל ה-API עובד",
            "due_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S+03:00")
        })
        t.record("create_task", r)

        r = await engine.run({"action": "get_tasks", "contact_id": ids["contact_id"]})
        t.record("get_tasks", r)

    # ================================================================
    # PART 6: TEMPLATES (Email & SMS)
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 6: TEMPLATES")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_template",
        "type": "email",
        "name": f"Test Email Template v2 {datetime.now().strftime('%H%M%S')}",
        "html": "<h1>בדיקת PrimeFlow</h1><p>זוהי תבנית בדיקה מלאה של כל ה-API.</p>"
    })
    t.record("create_template (email)", r)
    ids["template_id"] = engine.results.get("template_ids", [""])[0] if engine.results.get("template_ids") else ""

    r = await engine.run({
        "action": "create_template",
        "type": "sms",
        "name": "Test SMS Template v2",
        "body": "שלום {{contact.first_name}}! הודעת בדיקה מ-PrimeFlow. 📱"
    })
    t.record("create_template (sms)", r)

    r = await engine.run({"action": "get_templates"})
    t.record("get_templates", r)

    r = await engine.run({"action": "get_email_templates"})
    t.record("get_email_templates", r)

    # ================================================================
    # PART 7: CALENDARS & APPOINTMENTS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 7: CALENDARS & APPOINTMENTS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_calendars"})
    t.record("get_calendars", r)
    # Get first calendar ID if any exist
    calendars = r.get("result", {}).get("data", {}).get("calendars", [])
    if calendars:
        ids["calendar_id"] = calendars[0].get("id", "")

    # Try free slots with each calendar until we find an active one
    free_slots_tested = False
    for cal in calendars:
        if free_slots_tested:
            break
        cal_id = cal.get("id", "")
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0)
        r = await engine.run({
            "action": "get_free_slots",
            "calendar_id": cal_id,
            "start_date": tomorrow.strftime("%Y-%m-%d"),
            "end_date": (tomorrow + timedelta(days=5)).strftime("%Y-%m-%d"),
            "timezone": "Asia/Jerusalem"
        })
        if r.get("result", {}).get("success"):
            t.record("get_free_slots", r)
            free_slots_tested = True
            ids["calendar_id"] = cal_id
    if not free_slots_tested:
        t.record("get_free_slots", r if calendars else {"result": {"success": False, "error": "No active calendar"}},
                 "(calendar inactive)")
        if calendars:
            ids["calendar_id"] = calendars[0].get("id", "")

    if ids.get("calendar_id"):
        import time
        start_ms = str(int(time.time() * 1000))
        end_ms = str(int(time.time() * 1000) + (7 * 86400000))
        r = await engine.run({
            "action": "get_calendar_events",
            "calendarId": ids["calendar_id"],
            "startTime": start_ms,
            "endTime": end_ms,
        })
        t.record("get_calendar_events", r)
    else:
        t.skip("get_calendar_events", "No calendar found")

    # Service bookings — may not be configured
    t.skip("get_service_bookings", "Requires service calendars to be configured")

    # ================================================================
    # PART 8: OPPORTUNITIES & PIPELINES
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 8: OPPORTUNITIES & PIPELINES")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_pipelines"})
    t.record("get_pipelines", r)
    pipelines = r.get("result", {}).get("data", {}).get("pipelines", [])
    for p in pipelines:
        p_stages = p.get("stages", [])
        if p_stages:
            ids["pipeline_id"] = p.get("id", "")
            ids["stage_id"] = p_stages[0].get("id", "")
            break
    if not ids.get("pipeline_id") and pipelines:
        ids["pipeline_id"] = pipelines[0].get("id", "")

    if ids.get("pipeline_id") and ids.get("contact_id"):
        r = await engine.run({
            "action": "create_opportunity",
            "pipeline_id": ids["pipeline_id"],
            "name": "בדיקת הזדמנות — Full API Test",
            "status": "open",
            "contact_id": ids["contact_id"],
            "monetary_value": 50000,
        })
        t.record("create_opportunity", r)
        ids["opportunity_id"] = r.get("result", {}).get("data", {}).get("opportunity", {}).get("id", "")

        if ids.get("opportunity_id"):
            r = await engine.run({
                "action": "update_opportunity",
                "opportunity_id": ids["opportunity_id"],
                "monetaryValue": 75000,
                "name": "בדיקת הזדמנות — מעודכן"
            })
            t.record("update_opportunity", r)

            r = await engine.run({
                "action": "update_opportunity_status",
                "opportunity_id": ids["opportunity_id"],
                "status": "won"
            })
            t.record("update_opportunity_status", r)

        r = await engine.run({"action": "search_opportunities", "pipeline_id": ids["pipeline_id"]})
        t.record("search_opportunities", r)

        r = await engine.run({
            "action": "upsert_opportunity",
            "pipelineId": ids["pipeline_id"],
            "name": "אפסרט הזדמנות — Full API Test",
            "status": "open",
            "contactId": ids["contact_id"],
        })
        t.record("upsert_opportunity", r)
    else:
        t.skip("create_opportunity", "No pipeline found")
        t.skip("update_opportunity", "No pipeline found")
        t.skip("update_opportunity_status", "No pipeline found")
        t.skip("search_opportunities", "No pipeline found")
        t.skip("upsert_opportunity", "No pipeline found")

    # ================================================================
    # PART 9: PRODUCTS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 9: PRODUCTS")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_product",
        "name": "מוצר בדיקה — Full API Test",
        "description": "מוצר שנוצר בבדיקת API מלאה",
        "product_type": "DIGITAL",
        "price": 9900,
        "currency": "ILS",
        "price_name": "מחיר בדיקה"
    })
    t.record("create_product", r)
    ids["product_id"] = engine.results.get("product_id", "")

    if ids.get("product_id"):
        r = await engine.run({
            "action": "create_product_price",
            "product_id": ids["product_id"],
            "name": "מחיר חודשי",
            "type": "recurring",
            "amount": 4900,
            "currency": "ILS",
        })
        t.record("create_product_price", r)

        r = await engine.run({
            "action": "update_product",
            "product_id": ids["product_id"],
            "name": "מוצר בדיקה — מעודכן",
            "description": "מוצר מעודכן בבדיקת API מלאה"
        })
        t.record("update_product", r)

    r = await engine.run({"action": "get_products"})
    t.record("get_products", r)

    # ================================================================
    # PART 10: BUSINESSES
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 10: BUSINESSES")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_business",
        "name": "PrimeFlow Test Business",
        "phone": "+972501234567",
        "email": "biz@primeflow-test.com",
        "website": "https://primeflow-test.com",
        "description": "עסק בדיקה — Full API Test"
    })
    t.record("create_business", r)
    ids["business_id"] = engine.results.get("business_id", "")

    if ids.get("business_id"):
        r = await engine.run({
            "action": "update_business",
            "business_id": ids["business_id"],
            "name": "PrimeFlow Test Business — מעודכן"
        })
        t.record("update_business", r)

    r = await engine.run({"action": "get_businesses"})
    t.record("get_businesses", r)

    # ================================================================
    # PART 11: TRIGGER LINKS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 11: TRIGGER LINKS")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_link",
        "name": "Test Trigger Link v2",
        "redirect_to": "https://primeflow-test.com/landing"
    })
    t.record("create_link", r)
    # Try to get the link_id from result
    link_data = r.get("result", {}).get("data", {})
    ids["link_id"] = link_data.get("link", {}).get("id", link_data.get("id", ""))

    r = await engine.run({"action": "get_links"})
    t.record("get_links", r)

    if ids.get("link_id"):
        r = await engine.run({
            "action": "update_link",
            "link_id": ids["link_id"],
            "name": "Test Trigger Link v2 — Updated",
            "redirect_to": "https://primeflow-test.com/updated"
        })
        t.record("update_link", r)

    # ================================================================
    # PART 12: CONVERSATIONS & MESSAGES
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 12: CONVERSATIONS & MESSAGES")
    print(f"{'─'*40}")

    if ids.get("contact_id"):
        r = await engine.run({
            "action": "create_conversation",
            "contact_id": ids["contact_id"]
        })
        t.record("create_conversation", r)
        ids["conversation_id"] = engine.results.get("conversation_id", "")

    r = await engine.run({"action": "get_conversations"})
    t.record("get_conversations", r)

    # ================================================================
    # PART 13: WORKFLOWS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 13: WORKFLOWS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_workflows"})
    t.record("get_workflows", r)

    # ================================================================
    # PART 14: CAMPAIGNS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 14: CAMPAIGNS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_campaigns"})
    t.record("get_campaigns", r)

    # ================================================================
    # PART 15: FUNNELS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 15: FUNNELS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_funnels"})
    t.record("get_funnels", r)

    # ================================================================
    # PART 16: FORMS & SURVEYS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 16: FORMS & SURVEYS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_forms"})
    t.record("get_forms", r)

    r = await engine.run({"action": "get_form_submissions"})
    t.record("get_form_submissions", r)

    r = await engine.run({"action": "get_surveys"})
    t.record("get_surveys", r)

    r = await engine.run({"action": "get_survey_submissions"})
    t.record("get_survey_submissions", r)

    # ================================================================
    # PART 17: SOCIAL MEDIA
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 17: SOCIAL MEDIA")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_social_accounts"})
    t.record("get_social_accounts", r)

    # ================================================================
    # PART 18: BLOGS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 18: BLOGS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_blogs"})
    t.record("get_blogs", r)

    # ================================================================
    # PART 19: MEDIA LIBRARY
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 19: MEDIA LIBRARY")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_media_files"})
    t.record("get_media_files", r)

    r = await engine.run({"action": "create_media_folder", "name": "PrimeFlow Test Folder"})
    t.record("create_media_folder", r)

    # ================================================================
    # PART 20: USERS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 20: USERS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_users"})
    t.record("get_users", r)

    # ================================================================
    # PART 21: LOCATION
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 21: LOCATION")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_location"})
    t.record("get_location", r)

    # ================================================================
    # PART 22: INVOICES
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 22: INVOICES")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_invoices"})
    t.record("get_invoices", r, "(needs Invoices IAM scope)")

    if ids.get("contact_id"):
        r = await engine.run({
            "action": "create_invoice",
            "contactId": ids["contact_id"],
            "name": "חשבונית בדיקה — Full API Test",
            "title": "חשבונית בדיקה",
            "dueDate": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S+03:00"),
            "currency": "ILS",
            "items": [{
                "name": "שירות בדיקה",
                "description": "בדיקת API מלאה",
                "amount": 100,
                "quantity": 1,
                "currency": "ILS",
            }]
        })
        t.record("create_invoice", r, "(needs Invoices IAM scope)")
        ids["invoice_id"] = engine.results.get("invoice_id", "")

        if ids.get("invoice_id"):
            r = await engine.run({
                "action": "get_invoice",
                "invoice_id": ids["invoice_id"]
            })
            t.record("get_invoice", r)

            r = await engine.run({
                "action": "update_invoice",
                "invoice_id": ids["invoice_id"],
                "title": "חשבונית בדיקה — מעודכנת"
            })
            t.record("update_invoice", r)

    # ================================================================
    # PART 23: PAYMENTS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 23: PAYMENTS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_orders"})
    t.record("get_orders", r, "(needs Payments IAM scope)")

    r = await engine.run({"action": "get_transactions"})
    t.record("get_transactions", r, "(needs Payments IAM scope)")

    r = await engine.run({"action": "get_subscriptions"})
    t.record("get_subscriptions", r, "(needs Payments IAM scope)")

    r = await engine.run({"action": "get_coupons"})
    t.record("get_coupons", r)

    # ================================================================
    # PART 24: CONVERSATION AI AGENTS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 24: CONVERSATION AI AGENTS")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_ai_agent",
        "name": "בדיקה-API",
        "business_name": "PrimeFlow Test",
        "niche": "general",
        "language": "he",
        "mode": "auto-pilot",
        "goals": "לבדוק שה-API עובד",
        "greeting": "שלום! אני נציג בדיקה.",
        "business_brief": "חברת בדיקות API",
    })
    t.record("create_ai_agent", r)
    ids["ai_agent_id"] = engine.results.get("ai_agent_id", "")

    r = await engine.run({"action": "get_ai_agents"})
    t.record("get_ai_agents", r)

    if ids.get("ai_agent_id"):
        r = await engine.run({
            "action": "get_ai_agent",
            "agent_id": ids["ai_agent_id"]
        })
        t.record("get_ai_agent", r)

        r = await engine.run({
            "action": "update_ai_agent",
            "agent_id": ids["ai_agent_id"],
            "name": "בדיקה-API-מעודכן",
            "personality": "ידידותי ומקצועי. נציג בדיקות.",
            "goal": "לבדוק שה-API עובד — מעודכן",
            "instructions": "אתה נציג בדיקות. תענה בקצרה."
        })
        t.record("update_ai_agent", r)

    # ================================================================
    # PART 25: VOICE AI
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 25: VOICE AI")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_voice_agents"})
    t.record("get_voice_agents", r)

    r = await engine.run({"action": "get_voice_call_logs"})
    t.record("get_voice_call_logs", r)

    # ================================================================
    # PART 26: CUSTOM OBJECTS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 26: CUSTOM OBJECTS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_object_schemas"})
    t.record("get_object_schemas", r)

    # ================================================================
    # PART 27: STORE / SHIPPING
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 27: STORE / SHIPPING")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_store_settings"})
    t.record("get_store_settings", r)

    r = await engine.run({"action": "get_shipping_zones"})
    t.record("get_shipping_zones", r)

    r = await engine.run({"action": "get_shipping_carriers"})
    t.record("get_shipping_carriers", r)

    # ================================================================
    # PART 28: CUSTOM MENUS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 28: CUSTOM MENUS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_custom_menus"})
    t.record("get_custom_menus", r, "(may need OAuth scope)")

    # ================================================================
    # PART 29: DOCUMENTS / PROPOSALS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 29: DOCUMENTS / PROPOSALS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_documents"})
    t.record("get_documents", r)

    r = await engine.run({"action": "get_document_templates"})
    t.record("get_document_templates", r)

    # ================================================================
    # PART 30: PHONE SYSTEM
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 30: PHONE SYSTEM")
    print(f"{'─'*40}")

    # Phone system may need specific IAM scope
    r = await engine.run({"action": "get_active_numbers"})
    t.record("get_active_numbers", r, "(may need Phone System IAM scope)")

    # ================================================================
    # PART 31: EMAIL VERIFICATION
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 31: EMAIL VERIFICATION")
    print(f"{'─'*40}")

    # verify_email — requires specific email ISV setup
    t.skip("verify_email", "Requires Email ISV integration to be configured")

    # ================================================================
    # PART 32: ASSOCIATIONS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 32: ASSOCIATIONS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "get_associations"})
    t.record("get_associations", r)

    # ================================================================
    # PART 33: FUNNEL BUILDER (Full Orchestration)
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 33: FUNNEL BUILDER (Orchestration)")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "create_funnel",
        "name": "Full API Test Funnel",
        "tags": ["funnel-test-v2", "api-test"],
        "custom_fields": [
            {"name": "Test Funnel Field", "data_type": "TEXT"},
        ],
        "custom_values": [
            {"name": "test.funnel.source", "value": "Full API Test"},
        ],
        "templates": [
            {
                "type": "email",
                "name": f"Funnel Email {datetime.now().strftime('%H%M%S')}",
                "html": "<h1>Funnel Test</h1><p>בדיקת פאנל מלאה.</p>"
            },
        ],
        "contacts": [
            {
                "first_name": "פאנל",
                "last_name": "בדיקה",
                "email": f"funnel-test-{datetime.now().strftime('%H%M%S')}@primeflow-test.com",
                "tags": ["funnel-test-v2"]
            }
        ],
    })
    t.record("create_funnel (full orchestration)", r)

    # ================================================================
    # PART 34: RAW API CALL
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 34: RAW API CALL")
    print(f"{'─'*40}")

    r = await engine.run({
        "action": "raw",
        "method": "GET",
        "endpoint": f"/locations/{engine.ghl.location_id}",
    })
    t.record("raw (GET location)", r)

    # ================================================================
    # PART 35: LIST ALL ACTIONS
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 35: LIST ACTIONS")
    print(f"{'─'*40}")

    r = await engine.run({"action": "list_actions"})
    t.record("list_actions", r)
    total_actions = r.get("result", {}).get("total", 0)
    print(f"  📊 Total engine actions: {total_actions}")

    # ================================================================
    # PART 36: NEW HANDLERS — Full Coverage Tests
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 36: NEW HANDLERS — Full Coverage Tests")
    print(f"{'─'*40}")

    # -- Calendar Groups --
    r = await engine.run({"action": "get_calendar_groups"})
    t.record("get_calendar_groups", r)

    # -- Blocked Slots --
    _now = datetime.now()
    r = await engine.run({"action": "get_blocked_slots",
                           "calendarId": ids.get("calendar_id", ""),
                           "startDate": str(int(_now.timestamp() * 1000)),
                           "endDate": str(int((_now + timedelta(days=30)).timestamp() * 1000))})
    t.record("get_blocked_slots", r)

    # -- Funnels Extended --
    r = await engine.run({"action": "get_funnel_pages",
                           "funnelId": "placeholder", "limit": 1})
    t.record("get_funnel_pages", r)

    r = await engine.run({"action": "get_redirects"})
    t.record("get_redirects", r)

    # -- Conversations: Search & Get --
    r = await engine.run({"action": "search_conversations",
                           "locationId": engine.ghl.location_id})
    t.record("search_conversations", r)

    # -- Products: Collections --
    r = await engine.run({"action": "get_collections"})
    t.record("get_collections", r)

    # -- Products: Inventory --
    r = await engine.run({"action": "get_inventory"})
    t.record("get_inventory", r)

    # -- Blog Authors & Categories --
    r = await engine.run({"action": "get_blog_authors"})
    t.record("get_blog_authors", r)

    r = await engine.run({"action": "get_blog_categories"})
    t.record("get_blog_categories", r)

    # -- Users: Get User (single) --
    users_r = await engine.run({"action": "get_users"})
    user_list = users_r.get("result", {}).get("data", {}).get("users", [])
    if user_list:
        r = await engine.run({"action": "get_user",
                               "user_id": user_list[0].get("id", "")})
        t.record("get_user (single)", r)

    # -- Associations: Full --
    r = await engine.run({"action": "get_associations"})
    t.record("get_associations (new handler)", r)

    # -- Custom Objects: Schemas --
    r = await engine.run({"action": "get_object_schemas"})
    t.record("get_object_schemas (new handler)", r)

    # -- Custom Values: get --
    r = await engine.run({"action": "get_custom_values"})
    t.record("get_custom_values (new handler)", r)

    # -- Email Campaigns --
    r = await engine.run({"action": "get_email_campaigns"})
    t.record("get_email_campaigns", r)

    # -- Social: Search Posts --
    r = await engine.run({"action": "search_social_posts",
                           "type": "post", "page": "1", "limit": "5"})
    t.record("search_social_posts", r)

    # -- Get single business --
    if ids.get("business_id"):
        r = await engine.run({"action": "get_business",
                               "business_id": ids["business_id"]})
        t.record("get_business", r)

    # -- Search Links --
    r = await engine.run({"action": "search_links"})
    t.record("search_links", r)

    # -- Location: Get Timezones --
    r = await engine.run({"action": "get_location"})
    t.record("get_location (new handler)", r)

    # ================================================================
    # PART 37: CLEANUP — DELETE created test resources
    # ================================================================
    print(f"\n{'─'*40}")
    print(f"  PART 37: CLEANUP — Deleting test resources")
    print(f"{'─'*40}")

    if ids.get("ai_agent_id"):
        r = await engine.run({"action": "delete_ai_agent", "agent_id": ids["ai_agent_id"]})
        t.record("delete_ai_agent", r)

    if ids.get("opportunity_id"):
        r = await engine.run({"action": "delete_opportunity", "opportunity_id": ids["opportunity_id"]})
        t.record("delete_opportunity", r)

    if ids.get("product_id"):
        r = await engine.run({"action": "delete_product", "product_id": ids["product_id"]})
        t.record("delete_product", r)

    if ids.get("link_id"):
        r = await engine.run({"action": "delete_link", "link_id": ids["link_id"]})
        t.record("delete_link", r)

    if ids.get("business_id"):
        r = await engine.run({"action": "delete_business", "business_id": ids["business_id"]})
        t.record("delete_business", r)

    if ids.get("custom_field_id"):
        r = await engine.run({"action": "delete_custom_field", "field_id": ids["custom_field_id"]})
        t.record("delete_custom_field", r)

    if ids.get("custom_field_id_2"):
        r = await engine.run({"action": "delete_custom_field", "field_id": ids["custom_field_id_2"]})
        t.record("delete_custom_field (2)", r)

    if ids.get("tag_id"):
        r = await engine.run({"action": "delete_tag", "tag_id": ids["tag_id"]})
        t.record("delete_tag", r)

    if ids.get("template_id"):
        r = await engine.run({"action": "delete_email_template", "template_id": ids["template_id"]})
        t.record("delete_email_template", r)

    if ids.get("invoice_id"):
        r = await engine.run({"action": "delete_invoice", "invoice_id": ids["invoice_id"]})
        t.record("delete_invoice", r)

    # Delete contacts last
    if ids.get("contact_id"):
        r = await engine.run({"action": "delete_contact", "contact_id": ids["contact_id"]})
        t.record("delete_contact", r)

    # ================================================================
    # FINAL SUMMARY
    # ================================================================
    summary = t.summary()

    # Save results to file
    results_file = Path(__file__).parent / "test_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Results saved to: {results_file}")

    await engine.close()
    return summary


if __name__ == "__main__":
    asyncio.run(run_full_test())
