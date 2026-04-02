"""
PrimeFlow Engine — Test D: Full Function Coverage
====================================================
Comprehensive test that exercises ALL engine functions through the
orchestrator. Tests every resource type supported by PrimeFlow:

  1.  Custom Fields (TEXT, NUMERICAL, SINGLE_OPTIONS, DATE, LARGE_TEXT)
  2.  Tags
  3.  Users / Workers
  4.  Calendar
  5.  Contacts
  6.  AI Agent (new human-quality personality)
  7.  Knowledge Base + FAQs
  8.  Email Templates
  9.  SMS Templates
  10. Custom Values (Brand settings)
  11. Opportunities (post-orchestrator, per contact)
  12. Custom Object + Association (Many-to-One)
  13. Report: PDF + HTML + text → email to primeflow.ai@gmail.com

RULES:
  - Uses PrimeFlowOrchestrator for all resources in DEDUP_MAP
  - Pre-orchestrator: fetches pipeline info + company_id
  - Post-orchestrator: opportunities (need contact IDs from snapshot)
  - Post-orchestrator: custom object + association (raw API)
  - Report sent FROM support@primeflow.ai TO primeflow.ai@gmail.com
"""
from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from server.core.engine import PrimeFlowEngine
from server.core.orchestrator import PrimeFlowOrchestrator

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


async def build_test_d():
    engine = PrimeFlowEngine()
    orchestrator = PrimeFlowOrchestrator(engine)

    print("=" * 65)
    print("  PrimeFlow Test D — Full Function Coverage")
    print(f"  Location: {engine.ghl.location_id}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    # ══════════════════════════════════════════════════════════════════
    # PRE-ORCHESTRATOR: Get pipeline info + company_id
    # ══════════════════════════════════════════════════════════════════
    print("\n  Fetching pipeline info...")
    pipes_r = await engine.run({"action": "get_pipelines"})
    all_pipes = pipes_r.get("result", {}).get("data", {}).get("pipelines", [])
    pipeline = next((p for p in all_pipes if p.get("name") == "Sales Pipeline"), None)
    if not pipeline:
        pipeline = all_pipes[0] if all_pipes else {}
    pipeline_id = pipeline.get("id", "")
    stages = pipeline.get("stages", [])
    first_stage_id = stages[0].get("id", "") if stages else ""
    print(f"  Pipeline: '{pipeline.get('name', '')}' ({pipeline_id[:12]}...)")

    # Get company ID for user creation (retry up to 3 times)
    company_id = ""
    for attempt in range(3):
        loc_r = await engine.run({"action": "get_location"})
        loc_data = loc_r.get("result", {}).get("data", {}).get("location",
                   loc_r.get("result", {}).get("data", {}))
        company_id = loc_data.get("companyId", "")
        if company_id:
            break
        print(f"  Retry get_location ({attempt+1}/3)...")
        await asyncio.sleep(2)
    print(f"  Company ID: {company_id[:12]}..." if company_id else "  Company ID: NOT FOUND")

    # ══════════════════════════════════════════════════════════════════
    # BUILD COMMAND LIST — All resources as flat commands
    # ══════════════════════════════════════════════════════════════════
    commands: list[dict] = []

    # ─── 1. Custom Fields (12 fields, covering all data types) ───
    fields = [
        {"name": "TestD - Full Name",       "data_type": "TEXT",            "placeholder": "Enter full name"},
        {"name": "TestD - Phone Number",    "data_type": "TEXT",            "placeholder": "+972..."},
        {"name": "TestD - Budget",          "data_type": "NUMERICAL",       "placeholder": "Amount in NIS"},
        {"name": "TestD - Revenue",         "data_type": "NUMERICAL",       "placeholder": "Monthly revenue"},
        {"name": "TestD - Lead Source",     "data_type": "SINGLE_OPTIONS",
         "options": ["Google", "Facebook", "Instagram", "LinkedIn", "Referral", "Website", "WhatsApp", "Other"]},
        {"name": "TestD - Lead Status",     "data_type": "SINGLE_OPTIONS",
         "options": ["New", "Contacted", "Interested", "Negotiation", "Customer", "Lost"]},
        {"name": "TestD - Service Type",    "data_type": "SINGLE_OPTIONS",
         "options": ["Social Media", "Paid Ads", "Website", "SEO", "Branding", "Full Package", "Consulting"]},
        {"name": "TestD - Meeting Date",    "data_type": "DATE",            "placeholder": "Pick a date"},
        {"name": "TestD - Follow Up Date",  "data_type": "DATE",            "placeholder": "Next follow up"},
        {"name": "TestD - Notes",           "data_type": "LARGE_TEXT",      "placeholder": "Write notes here..."},
        {"name": "TestD - Lead Rating",     "data_type": "SINGLE_OPTIONS",
         "options": ["Hot", "Warm", "Cold", "Frozen"]},
        {"name": "TestD - Preferred Channel", "data_type": "SINGLE_OPTIONS",
         "options": ["WhatsApp", "Phone", "Email", "SMS", "In Person"]},
    ]
    for f in fields:
        commands.append({"action": "create_custom_field", **f})

    # ─── 2. Tags (10 tags) ───
    tags = [
        "test-d", "testd-funnel", "testd-marketing", "testd-vip",
        "testd-new-lead", "testd-hot-lead", "testd-customer",
        "testd-meeting-booked", "testd-follow-up", "testd-automation",
    ]
    for tag in tags:
        commands.append({"action": "create_tag", "name": tag})

    # ─── 3. Workers / Users (3 team members) ───
    workers = [
        {"first_name": "TestD", "last_name": "Manager",
         "email": "testd.manager@testprimeflow.com", "phone": "+972501110001"},
        {"first_name": "TestD", "last_name": "Sales",
         "email": "testd.sales@testprimeflow.com", "phone": "+972502220002"},
        {"first_name": "TestD", "last_name": "Support",
         "email": "testd.support@testprimeflow.com", "phone": "+972503330003"},
    ]
    for w in workers:
        commands.append({
            "action": "create_user",
            "company_id": company_id,
            "first_name": w["first_name"],
            "last_name": w["last_name"],
            "email": w["email"],
            "phone": w["phone"],
            "password": "TestD2026!Pf",
            "type": "account",
            "role": "user",
            "locationIds": [engine.ghl.location_id],
            "permissions": {
                "campaignsEnabled": True,
                "contactsEnabled": True,
                "opportunitiesEnabled": True,
                "dashboardStatsEnabled": True,
            },
        })

    # ─── 4. Calendar ───
    commands.append({
        "action": "create_calendar",
        "name": "TestD - Strategy Session",
        "description": "TestD - Free 30min strategy session with our marketing team",
        "calendarType": "event",
        "slotDuration": 30,
        "slotInterval": 30,
    })

    # ─── 5. Contacts (6 test contacts) ───
    contacts = [
        {"first_name": "TestD Lior",   "last_name": "Goldberg",
         "email": "testd.lior@testprimeflow.com",   "phone": "+97250200001",
         "tags": ["test-d", "testd-new-lead"], "source": "Google",
         "companyName": "Goldberg Consulting"},
        {"first_name": "TestD Maya",   "last_name": "Shapira",
         "email": "testd.maya@testprimeflow.com",    "phone": "+97252200002",
         "tags": ["test-d", "testd-hot-lead"], "source": "Facebook",
         "companyName": "Maya Fashion"},
        {"first_name": "TestD Oren",   "last_name": "Benari",
         "email": "testd.oren@testprimeflow.com",    "phone": "+97253200003",
         "tags": ["test-d", "testd-hot-lead"], "source": "Referral",
         "companyName": "Benari Properties"},
        {"first_name": "TestD Shira",  "last_name": "Katz",
         "email": "testd.shira@testprimeflow.com",   "phone": "+97254200004",
         "tags": ["test-d", "testd-new-lead"], "source": "Instagram",
         "companyName": "Shira Design Studio"},
        {"first_name": "TestD Amir",   "last_name": "Rosenberg",
         "email": "testd.amir@testprimeflow.com",    "phone": "+97255200005",
         "tags": ["test-d", "testd-vip"], "source": "LinkedIn",
         "companyName": "Rosenberg Tech"},
        {"first_name": "TestD Dana",   "last_name": "Peretz",
         "email": "testd.dana@testprimeflow.com",    "phone": "+97258200006",
         "tags": ["test-d", "testd-customer"], "source": "Website",
         "companyName": "Dana Events"},
    ]
    for c in contacts:
        commands.append({"action": "create_contact", **c})

    # ─── 6. AI Agent (human-quality, no bot detection) ───
    ai_personality = (
        "You are a human representative from TestD Digital Agency. "
        "You speak naturally, calmly, and professionally. "
        "You write short messages, 1-3 sentences max, no exclamation marks. "
        "You listen first, understand the need, then suggest a solution. "
        "You never reveal you are a bot. If asked, say you are from the TestD team."
    )
    ai_goal = (
        "1. Answer client questions professionally and accurately\n"
        "2. Understand the client's real need before suggesting a service\n"
        "3. Gently lead to a consultation with the team\n"
        "4. Keep the conversation natural, short, and pressure-free"
    )
    ai_instructions = (
        "Behavior rules:\n"
        "- Write short messages, 1-3 sentences max\n"
        "- No exclamation marks unless truly appropriate\n"
        "- No long lists in a single message\n"
        "- Listen, answer with focus, ask one question at a time\n"
        "- If asked about pricing, say you'd be happy to set up a quick call with the team\n"
        "- Don't list all services at once, ask what's relevant\n\n"
        "Services: Social Media, Paid Ads, Website, SEO, Branding, Consulting\n"
        "Hours: Sun-Thu 09:00-18:00 | Phone: 03-9876543\n\n"
        "Example opening:\n"
        "\"Hi, how are you? I'm from the TestD team. I saw you reached out, happy to help. "
        "What are you looking for?\"\n\n"
        "Example pricing response:\n"
        "\"Pricing depends on a few things. I'd suggest a quick 10-minute call with our team "
        "so we can give you an accurate proposal. When works for you?\""
    )
    commands.append({
        "action": "create_ai_agent",
        "name": "TestD - Digital Assistant",
        "business_name": "TestD Digital Agency",
        "mode": "suggestive",
        "personality": ai_personality,
        "goal": ai_goal,
        "instructions": ai_instructions,
    })

    # ─── 7. Knowledge Base ───
    commands.append({
        "action": "create_knowledge_base",
        "name": "TestD - Agency FAQ",
        "description": "Knowledge base for TestD digital agency assistant",
    })

    # ─── 8. Email Templates (3) ───
    welcome_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#2c3e50;padding:30px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:28px;">TestD Digital Agency</h1>
      <p style="color:#ecf0f1;margin:8px 0 0;font-size:14px;">Smart Marketing Solutions</p>
    </div>
    <div style="padding:30px;">
      <h2 style="color:#2c3e50;font-size:20px;">Welcome, {{contact.first_name}}</h2>
      <p style="font-size:15px;line-height:1.7;color:#555;">
        Thank you for reaching out. We look forward to helping you grow your business.
      </p>
      <div style="text-align:center;margin:25px 0;">
        <a href="#" style="background:#2c3e50;color:#fff;padding:12px 30px;text-decoration:none;border-radius:6px;font-size:16px;">Book a Free Strategy Session</a>
      </div>
      <p style="font-size:13px;color:#999;text-align:center;">Questions? Call us: 03-9876543</p>
    </div>
    <div style="background:#ecf0f1;padding:15px;text-align:center;">
      <p style="color:#7f8c8d;font-size:12px;margin:0;">TestD Digital Agency 2026</p>
    </div>
  </div>
</body></html>"""

    commands.append({
        "action": "create_template",
        "name": "TestD - Welcome Email",
        "type": "email",
        "subject": "Welcome to TestD - Your free strategy session awaits",
        "html": welcome_html,
    })

    followup_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#34495e;padding:25px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;">TestD - Follow Up</h1>
    </div>
    <div style="padding:25px;">
      <p style="font-size:15px;line-height:1.7;color:#555;">
        Hi {{contact.first_name}}, just checking in. Are you still interested in our strategy session?
      </p>
      <div style="text-align:center;margin:20px 0;">
        <a href="#" style="background:#27ae60;color:#fff;padding:10px 25px;text-decoration:none;border-radius:6px;font-size:15px;">Yes, book my session</a>
      </div>
    </div>
  </div>
</body></html>"""

    commands.append({
        "action": "create_template",
        "name": "TestD - Follow Up Email",
        "type": "email",
        "subject": "TestD - Still interested? Your free session is waiting",
        "html": followup_html,
    })

    closing_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#2c3e50;padding:25px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;">TestD - Thank You</h1>
    </div>
    <div style="padding:25px;">
      <p style="font-size:15px;line-height:1.7;color:#555;">
        Thank you {{contact.first_name}} for choosing TestD. We're excited to work with you.
      </p>
      <p style="font-size:13px;color:#999;text-align:center;">Support: 03-9876543 | info@testd-agency.com</p>
    </div>
  </div>
</body></html>"""

    commands.append({
        "action": "create_template",
        "name": "TestD - Thank You Email",
        "type": "email",
        "subject": "TestD - Thank you for joining us",
        "html": closing_html,
    })

    # ─── 9. SMS Templates (3) ───
    sms_templates = [
        ("TestD - Welcome SMS",
         "Hi {{contact.first_name}}, this is TestD Digital Agency. "
         "We'd love to set up a free strategy session. "
         "Reply YES and we'll reach out. 03-9876543"),
        ("TestD - Reminder SMS",
         "Hi {{contact.first_name}}, friendly reminder from TestD. "
         "We have a special offer for you. "
         "Call 03-9876543 or reply to this message."),
        ("TestD - Thank You SMS",
         "Thanks {{contact.first_name}}! Great talking with you. "
         "TestD team is here for you. 03-9876543"),
    ]
    for tmpl_name, tmpl_body in sms_templates:
        commands.append({
            "action": "create_template",
            "name": tmpl_name,
            "type": "sms",
            "body": tmpl_body,
        })

    # ─── 10. Custom Values / Brand Settings (8 values) ───
    brand_values = [
        {"name": "company.testd.name",     "value": "TestD Digital Agency"},
        {"name": "company.testd.phone",    "value": "03-9876543"},
        {"name": "company.testd.email",    "value": "info@testd-agency.com"},
        {"name": "company.testd.address",  "value": "Tel Aviv, Dizengoff 100"},
        {"name": "company.testd.website",  "value": "https://testd-agency.com"},
        {"name": "company.testd.colors",   "value": "Navy (#2c3e50) & Green (#27ae60)"},
        {"name": "company.testd.slogan",   "value": "TestD - Smart Marketing That Works"},
        {"name": "company.testd.hours",    "value": "Sun-Thu 09:00-18:00"},
    ]
    for bv in brand_values:
        commands.append({"action": "create_custom_value", **bv})

    # ══════════════════════════════════════════════════════════════════
    # RUN ORCHESTRATOR — All commands through smart dedup engine
    # ══════════════════════════════════════════════════════════════════
    total_cmds = len(commands)
    print(f"\n  Total orchestrator commands: {total_cmds}")
    print(f"  Categories: custom_fields({len(fields)}), tags({len(tags)}), "
          f"users({len(workers)}), calendar(1), contacts({len(contacts)}), "
          f"ai_agent(1), kb(1), templates(6), custom_values({len(brand_values)})")
    print(f"  Running orchestrator...\n")

    result = await orchestrator.run(
        commands,
        send_report=True,
        report_subject=(
            f"PrimeFlow Test D — Full Coverage Report — "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    # POST-ORCHESTRATOR: Custom Object + Association (raw API)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("  POST-ORCHESTRATOR: Custom Object + Association")
    print(f"{'='*60}\n")

    # Check if TestD Sales object exists
    obj_r = await engine.run({
        "action": "raw", "method": "GET",
        "endpoint": f"/objects/?locationId={engine.ghl.location_id}",
    })
    existing_objects = obj_r.get("result", {}).get("data", {}).get("objects", [])
    testd_obj = None
    schema_key = "custom_objects.testd_deals"
    for obj in existing_objects:
        if obj.get("key") == "testd_deals" or obj.get("key") == "custom_objects.testd_deals":
            testd_obj = obj
            schema_key = obj.get("key", schema_key)
            break

    if testd_obj:
        print(f"  [=] Custom Object already exists: {schema_key}")
    else:
        r = await engine.run({
            "action": "raw", "method": "POST", "endpoint": "/objects/",
            "body": {
                "locationId": engine.ghl.location_id,
                "labels": {"singular": "TestD Deal", "plural": "TestD Deals"},
                "key": "testd_deals",
                "description": "TestD - Deals database, each deal linked to a contact",
                "primaryDisplayPropertyDetails": {
                    "name": "deal_name", "key": "deal_name", "dataType": "TEXT",
                },
            },
        })
        obj_data = r.get("result", {}).get("data", {}).get("object", {})
        schema_key = obj_data.get("key", schema_key)
        ok = "[+]" if r.get("result", {}).get("success") else "[X]"
        print(f"  {ok} Created Custom Object: {schema_key}")

    # Check if association exists
    assoc_r = await engine.run({
        "action": "raw", "method": "GET",
        "endpoint": f"/associations/?locationId={engine.ghl.location_id}",
    })
    existing_assocs = assoc_r.get("result", {}).get("data", {})
    assoc_list = existing_assocs.get("associations",
                  existing_assocs if isinstance(existing_assocs, list) else [])
    testd_assoc = None
    for a in (assoc_list if isinstance(assoc_list, list) else []):
        if isinstance(a, dict) and a.get("key") == "testd_deals_contact":
            testd_assoc = a
            break

    if testd_assoc:
        print(f"  [=] Association already exists: testd_deals_contact")
    else:
        r = await engine.run({
            "action": "raw", "method": "POST", "endpoint": "/associations/",
            "body": {
                "locationId": engine.ghl.location_id,
                "key": "testd_deals_contact",
                "firstObjectKey": schema_key,
                "secondObjectKey": "contact",
                "firstObjectLabel": "Deals",
                "secondObjectLabel": "Contact",
            },
        })
        ok = "[+]" if r.get("result", {}).get("success") else "[X]"
        # Note: Cardinality must be configured via GHL UI (API doesn't support it)
        print(f"  {ok} Association: TestD Deals <-> Contact")

    # ══════════════════════════════════════════════════════════════════
    # POST-ORCHESTRATOR: Opportunities (need contact IDs from snapshot)
    # ══════════════════════════════════════════════════════════════════
    snapshot = result.get("snapshot", {})
    contacts_in_snapshot = snapshot.get("contacts", [])

    # Map email -> contact ID
    contact_email_to_id = {}
    for c in contacts_in_snapshot:
        email = (c.get("email") or "").lower()
        if email:
            contact_email_to_id[email] = c.get("id", "")

    if pipeline_id and first_stage_id:
        print(f"\n{'='*60}")
        print("  POST-ORCHESTRATOR: Opportunities")
        print(f"{'='*60}\n")

        opp_data = [
            ("testd.lior@testprimeflow.com",  "TestD - Consulting - Goldberg",     8000),
            ("testd.maya@testprimeflow.com",   "TestD - Social Media - Maya Fashion", 4500),
            ("testd.oren@testprimeflow.com",   "TestD - Website - Benari Properties", 15000),
            ("testd.shira@testprimeflow.com",  "TestD - Branding - Shira Design",    6000),
            ("testd.amir@testprimeflow.com",   "TestD - Full Package - Rosenberg Tech", 25000),
            ("testd.dana@testprimeflow.com",   "TestD - Event Marketing - Dana Events", 10000),
        ]

        for email, opp_name, opp_value in opp_data:
            cid = contact_email_to_id.get(email, "")
            if not cid:
                print(f"  [!] No contact ID for {email} — skipping")
                continue

            # Check existing
            opps_r = await engine.run({
                "action": "raw", "method": "GET",
                "endpoint": f"/opportunities/search?location_id={engine.ghl.location_id}"
                            f"&contact_id={cid}&pipeline_id={pipeline_id}&limit=10",
            })
            existing_opps = opps_r.get("result", {}).get("data", {}).get("opportunities", [])

            if existing_opps:
                existing_name = existing_opps[0].get("name", "")
                if existing_name == opp_name:
                    print(f"  [=] '{opp_name}' already set")
                    continue
                opp_id = existing_opps[0].get("id", "")
                r = await engine.run({
                    "action": "update_opportunity",
                    "opportunity_id": opp_id,
                    "name": opp_name,
                    "monetaryValue": opp_value,
                    "status": "open",
                })
                ok = "[U]" if r.get("result", {}).get("success") else "[X]"
                print(f"  {ok} Updated: {opp_name} (NIS {opp_value:,})")
            else:
                r = await engine.run({
                    "action": "create_opportunity",
                    "pipeline_id": pipeline_id,
                    "stage_id": first_stage_id,
                    "name": opp_name,
                    "contact_id": cid,
                    "monetary_value": opp_value,
                    "status": "open",
                })
                ok = "[+]" if r.get("result", {}).get("success") else "[X]"
                print(f"  {ok} Created: {opp_name} (NIS {opp_value:,})")
    else:
        print("\n  [!] No pipeline/stage — skipping opportunities")

    # ══════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════
    report_data = result.get("report_data")
    email_result = result.get("email_result", {})

    print(f"\n{'='*65}")
    print(f"  TEST D — COMPLETE")
    print(f"{'='*65}")
    if report_data:
        print(f"  Orchestrated: {len(report_data.results)} commands")
        print(f"  Created:      {len(report_data.created)}")
        print(f"  Updated:      {len(report_data.updated)}")
        print(f"  Duplicates:   {len(report_data.duplicates)}")
        print(f"  Errors:       {len(report_data.errors)}")
    print(f"  Email:        {email_result.get('method', 'N/A')} — {email_result.get('detail', '')}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    asyncio.run(build_test_d())
