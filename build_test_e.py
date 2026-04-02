"""
PrimeFlow Engine — Test E: Full Function Coverage + Report Validation
=======================================================================
Comprehensive test that exercises ALL engine functions through the
orchestrator. Same scope as Test D but with unique "TestE" prefixes
and fresh resource names to validate:

  - Email HTML: all categories expanded (no dropdowns — email-safe)
  - Interactive HTML: <details>/<summary> dropdowns (for browser)
  - PDF: fully expanded, attached to email
  - Text: console output

Resource types tested:
  1.  Custom Fields (TEXT, NUMERICAL, SINGLE_OPTIONS, DATE, LARGE_TEXT)
  2.  Tags
  3.  Users / Workers
  4.  Calendar
  5.  Contacts
  6.  AI Agent
  7.  Knowledge Base + FAQs
  8.  Email Templates
  9.  SMS Templates
  10. Custom Values (Brand settings)
  11. Opportunities (post-orchestrator, per contact)
  12. Custom Object + Association (Many-to-One)
  13. Report: PDF + HTML(email) + HTML(interactive) + text → email

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


async def build_test_e():
    engine = PrimeFlowEngine()
    orchestrator = PrimeFlowOrchestrator(engine)

    print("=" * 65)
    print("  PrimeFlow Test E — Full Function Coverage + Report Validation")
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
        {"name": "TestE - Client Name",       "data_type": "TEXT",            "placeholder": "Enter client name"},
        {"name": "TestE - Mobile Number",      "data_type": "TEXT",            "placeholder": "+972..."},
        {"name": "TestE - Project Budget",     "data_type": "NUMERICAL",       "placeholder": "Budget in NIS"},
        {"name": "TestE - Monthly Revenue",    "data_type": "NUMERICAL",       "placeholder": "Revenue per month"},
        {"name": "TestE - Traffic Source",     "data_type": "SINGLE_OPTIONS",
         "options": ["Google Ads", "Meta Ads", "TikTok", "LinkedIn", "Referral", "Organic", "Email", "Other"]},
        {"name": "TestE - Deal Stage",        "data_type": "SINGLE_OPTIONS",
         "options": ["Discovery", "Proposal", "Negotiation", "Closed Won", "Closed Lost", "On Hold"]},
        {"name": "TestE - Package Type",      "data_type": "SINGLE_OPTIONS",
         "options": ["Starter", "Growth", "Premium", "Enterprise", "Custom", "Trial"]},
        {"name": "TestE - Kickoff Date",      "data_type": "DATE",            "placeholder": "Project start date"},
        {"name": "TestE - Next Review Date",   "data_type": "DATE",            "placeholder": "Next review"},
        {"name": "TestE - Internal Notes",     "data_type": "LARGE_TEXT",      "placeholder": "Internal notes..."},
        {"name": "TestE - Priority Level",     "data_type": "SINGLE_OPTIONS",
         "options": ["Critical", "High", "Medium", "Low"]},
        {"name": "TestE - Contact Method",     "data_type": "SINGLE_OPTIONS",
         "options": ["WhatsApp", "Phone", "Email", "Zoom", "In Person"]},
    ]
    for f in fields:
        commands.append({"action": "create_custom_field", **f})

    # ─── 2. Tags (10 tags) ───
    tags = [
        "test-e", "teste-funnel", "teste-paid-ads", "teste-premium",
        "teste-new-lead", "teste-qualified", "teste-active-client",
        "teste-meeting-set", "teste-nurture", "teste-referral",
    ]
    for tag in tags:
        commands.append({"action": "create_tag", "name": tag})

    # ─── 3. Workers / Users (3 team members) ───
    workers = [
        {"first_name": "TestE", "last_name": "Director",
         "email": "teste.director@testprimeflow.com", "phone": "+972501110011"},
        {"first_name": "TestE", "last_name": "Marketing",
         "email": "teste.marketing@testprimeflow.com", "phone": "+972502220022"},
        {"first_name": "TestE", "last_name": "Operations",
         "email": "teste.operations@testprimeflow.com", "phone": "+972503330033"},
    ]
    for w in workers:
        commands.append({
            "action": "create_user",
            "company_id": company_id,
            "first_name": w["first_name"],
            "last_name": w["last_name"],
            "email": w["email"],
            "phone": w["phone"],
            "password": "TestE2026!Pf",
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
        "name": "TestE - Discovery Call",
        "description": "TestE - Free 20min discovery call with marketing strategist",
        "calendarType": "event",
        "slotDuration": 20,
        "slotInterval": 15,
    })

    # ─── 5. Contacts (6 test contacts) ───
    contacts = [
        {"first_name": "TestE Yael",   "last_name": "Cohen",
         "email": "teste.yael@testprimeflow.com",    "phone": "+97250300001",
         "tags": ["test-e", "teste-new-lead"], "source": "Google Ads",
         "companyName": "Cohen Law Firm"},
        {"first_name": "TestE Noam",   "last_name": "Levi",
         "email": "teste.noam@testprimeflow.com",    "phone": "+97252300002",
         "tags": ["test-e", "teste-qualified"], "source": "Meta Ads",
         "companyName": "Levi Restaurants"},
        {"first_name": "TestE Tal",    "last_name": "Mizrahi",
         "email": "teste.tal@testprimeflow.com",     "phone": "+97253300003",
         "tags": ["test-e", "teste-qualified"], "source": "Referral",
         "companyName": "Mizrahi Real Estate"},
        {"first_name": "TestE Noa",    "last_name": "Avraham",
         "email": "teste.noa@testprimeflow.com",     "phone": "+97254300004",
         "tags": ["test-e", "teste-new-lead"], "source": "TikTok",
         "companyName": "Noa Beauty Studio"},
        {"first_name": "TestE Eyal",   "last_name": "Ben David",
         "email": "teste.eyal@testprimeflow.com",    "phone": "+97255300005",
         "tags": ["test-e", "teste-premium"], "source": "LinkedIn",
         "companyName": "Ben David Consulting"},
        {"first_name": "TestE Roni",   "last_name": "Shahar",
         "email": "teste.roni@testprimeflow.com",    "phone": "+97258300006",
         "tags": ["test-e", "teste-active-client"], "source": "Organic",
         "companyName": "Shahar Media"},
    ]
    for c in contacts:
        commands.append({"action": "create_contact", **c})

    # ─── 6. AI Agent (professional tone, no bot detection) ───
    ai_personality = (
        "You are a human marketing consultant from TestE Growth Agency. "
        "You are calm, knowledgeable, and solution-oriented. "
        "You write short messages, 1-3 sentences max, with zero fluff. "
        "You ask smart questions to understand what the client truly needs. "
        "You never reveal you are a bot. If asked, say you are from the TestE team."
    )
    ai_goal = (
        "1. Answer client questions with clarity and confidence\n"
        "2. Understand the client's business goals before recommending services\n"
        "3. Guide the conversation toward a discovery call\n"
        "4. Keep it natural, brief, and value-driven"
    )
    ai_instructions = (
        "Behavior rules:\n"
        "- Messages: 1-3 sentences max, no walls of text\n"
        "- No exclamation marks unless truly appropriate\n"
        "- Ask one question at a time, listen first\n"
        "- If asked about pricing, suggest a quick call to give accurate quote\n"
        "- Don't list all services unless asked specifically\n\n"
        "Services: Paid Ads, Social Media, SEO, Website Design, Branding, Automation\n"
        "Hours: Sun-Thu 09:00-18:00 | Phone: 03-1234567\n\n"
        "Example opening:\n"
        "\"Hi, this is the TestE team. I saw your inquiry and wanted to follow up. "
        "What are you looking to achieve with your marketing?\"\n\n"
        "Example pricing response:\n"
        "\"It really depends on the scope of work. A quick 15-minute call would help "
        "me understand your needs and give you an accurate quote. When works for you?\""
    )
    commands.append({
        "action": "create_ai_agent",
        "name": "TestE - Growth Consultant",
        "business_name": "TestE Growth Agency",
        "mode": "suggestive",
        "personality": ai_personality,
        "goal": ai_goal,
        "instructions": ai_instructions,
    })

    # ─── 7. Knowledge Base ───
    commands.append({
        "action": "create_knowledge_base",
        "name": "TestE - Growth Agency FAQ",
        "description": "Knowledge base for TestE growth agency assistant",
    })

    # ─── 8. Email Templates (3) ───
    welcome_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#1a365d;padding:30px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:28px;">TestE Growth Agency</h1>
      <p style="color:#cbd5e0;margin:8px 0 0;font-size:14px;">Results-Driven Marketing</p>
    </div>
    <div style="padding:30px;">
      <h2 style="color:#1a365d;font-size:20px;">Welcome, {{contact.first_name}}</h2>
      <p style="font-size:15px;line-height:1.7;color:#555;">
        Thank you for reaching out to TestE. We specialize in helping businesses
        grow through smart marketing strategies.
      </p>
      <div style="text-align:center;margin:25px 0;">
        <a href="#" style="background:#1a365d;color:#fff;padding:12px 30px;text-decoration:none;border-radius:6px;font-size:16px;">Book a Discovery Call</a>
      </div>
      <p style="font-size:13px;color:#999;text-align:center;">Questions? Call us: 03-1234567</p>
    </div>
    <div style="background:#edf2f7;padding:15px;text-align:center;">
      <p style="color:#718096;font-size:12px;margin:0;">TestE Growth Agency 2026</p>
    </div>
  </div>
</body></html>"""

    commands.append({
        "action": "create_template",
        "name": "TestE - Welcome Email",
        "type": "email",
        "subject": "Welcome to TestE - Let's grow your business",
        "html": welcome_html,
    })

    followup_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#2d3748;padding:25px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;">TestE - Quick Follow Up</h1>
    </div>
    <div style="padding:25px;">
      <p style="font-size:15px;line-height:1.7;color:#555;">
        Hi {{contact.first_name}}, just following up from our earlier conversation.
        Still interested in exploring how we can help your business grow?
      </p>
      <div style="text-align:center;margin:20px 0;">
        <a href="#" style="background:#38a169;color:#fff;padding:10px 25px;text-decoration:none;border-radius:6px;font-size:15px;">Schedule a Call</a>
      </div>
    </div>
  </div>
</body></html>"""

    commands.append({
        "action": "create_template",
        "name": "TestE - Follow Up Email",
        "type": "email",
        "subject": "TestE - Quick follow up on your inquiry",
        "html": followup_html,
    })

    closing_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
  <div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#1a365d;padding:25px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;">TestE - Welcome Aboard</h1>
    </div>
    <div style="padding:25px;">
      <p style="font-size:15px;line-height:1.7;color:#555;">
        Welcome aboard {{contact.first_name}}! We're excited to start working together.
        Your dedicated strategist will be in touch within 24 hours.
      </p>
      <p style="font-size:13px;color:#999;text-align:center;">Support: 03-1234567 | hello@teste-agency.com</p>
    </div>
  </div>
</body></html>"""

    commands.append({
        "action": "create_template",
        "name": "TestE - Onboarding Email",
        "type": "email",
        "subject": "TestE - Welcome aboard, let's get started",
        "html": closing_html,
    })

    # ─── 9. SMS Templates (3) ───
    sms_templates = [
        ("TestE - Welcome SMS",
         "Hi {{contact.first_name}}, this is TestE Growth Agency. "
         "We'd love to schedule a quick discovery call. "
         "Reply YES and we'll set it up. 03-1234567"),
        ("TestE - Reminder SMS",
         "Hi {{contact.first_name}}, friendly reminder from TestE. "
         "We have a growth strategy ready for you. "
         "Call 03-1234567 or reply to schedule."),
        ("TestE - Thank You SMS",
         "Thanks {{contact.first_name}}! Great connecting with you. "
         "TestE team is here whenever you need us. 03-1234567"),
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
        {"name": "company.teste.name",     "value": "TestE Growth Agency"},
        {"name": "company.teste.phone",    "value": "03-1234567"},
        {"name": "company.teste.email",    "value": "hello@teste-agency.com"},
        {"name": "company.teste.address",  "value": "Tel Aviv, Rothschild 50"},
        {"name": "company.teste.website",  "value": "https://teste-agency.com"},
        {"name": "company.teste.colors",   "value": "Navy (#1a365d) & Green (#38a169)"},
        {"name": "company.teste.slogan",   "value": "TestE - Smart Growth, Real Results"},
        {"name": "company.teste.hours",    "value": "Sun-Thu 09:00-18:00"},
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
            f"PrimeFlow Test E — Full Coverage + Report Validation — "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    # POST-ORCHESTRATOR: Custom Object + Association (raw API)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("  POST-ORCHESTRATOR: Custom Object + Association")
    print(f"{'='*60}\n")

    # Check if TestE Projects object exists
    obj_r = await engine.run({
        "action": "raw", "method": "GET",
        "endpoint": f"/objects/?locationId={engine.ghl.location_id}",
    })
    existing_objects = obj_r.get("result", {}).get("data", {}).get("objects", [])
    testobj = None
    schema_key = "custom_objects.teste_projects"
    for obj in existing_objects:
        if obj.get("key") == "teste_projects" or obj.get("key") == "custom_objects.teste_projects":
            testobj = obj
            schema_key = obj.get("key", schema_key)
            break

    if testobj:
        print(f"  [=] Custom Object already exists: {schema_key}")
    else:
        r = await engine.run({
            "action": "raw", "method": "POST", "endpoint": "/objects/",
            "body": {
                "locationId": engine.ghl.location_id,
                "labels": {"singular": "TestE Project", "plural": "TestE Projects"},
                "key": "teste_projects",
                "description": "TestE - Projects database, each project linked to a contact",
                "primaryDisplayPropertyDetails": {
                    "name": "project_name", "key": "project_name", "dataType": "TEXT",
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
    testassoc = None
    for a in (assoc_list if isinstance(assoc_list, list) else []):
        if isinstance(a, dict) and a.get("key") == "teste_projects_contact":
            testassoc = a
            break

    if testassoc:
        print(f"  [=] Association already exists: teste_projects_contact")
    else:
        r = await engine.run({
            "action": "raw", "method": "POST", "endpoint": "/associations/",
            "body": {
                "locationId": engine.ghl.location_id,
                "key": "teste_projects_contact",
                "firstObjectKey": schema_key,
                "secondObjectKey": "contact",
                "firstObjectLabel": "Projects",
                "secondObjectLabel": "Contact",
            },
        })
        ok = "[+]" if r.get("result", {}).get("success") else "[X]"
        print(f"  {ok} Association: TestE Projects <-> Contact")

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
            ("teste.yael@testprimeflow.com",  "TestE - Legal Marketing - Cohen Law",     12000),
            ("teste.noam@testprimeflow.com",   "TestE - Restaurant Branding - Levi",       7500),
            ("teste.tal@testprimeflow.com",    "TestE - Real Estate Ads - Mizrahi",        18000),
            ("teste.noa@testprimeflow.com",    "TestE - Beauty Social Media - Noa Studio", 5000),
            ("teste.eyal@testprimeflow.com",   "TestE - Full Stack - Ben David Consulting", 30000),
            ("teste.roni@testprimeflow.com",   "TestE - Media Strategy - Shahar Media",    14000),
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
    print(f"  TEST E — COMPLETE")
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
    asyncio.run(build_test_e())
