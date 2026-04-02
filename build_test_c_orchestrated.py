"""
PrimeFlow Engine — Build "Test C" via Orchestrator
====================================================
Same Test C resources as build_test_c_funnel.py, but using the new
PrimeFlowOrchestrator which automatically:
  1. Runs preflight GET audit on ALL resource types
  2. Smart-compares each command against existing resources
  3. Skips duplicates / updates existing / creates new
  4. Generates structured report (HTML + text)
  5. Emails report to support@primeflow.ai (fallback: local file)

RULES:
  - No manual GET-before-CREATE — the orchestrator does it
  - Commands that need special handling (raw API, pipeline lookup)
    still run as regular engine commands first
  - Orchestrator handles: custom_fields, tags, contacts, custom_values,
    calendars, templates, users, ai_agents, knowledge_bases, kb_faqs,
    custom_objects, associations
"""
from __future__ import annotations
import asyncio
import json
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


async def build_funnel():
    engine = PrimeFlowEngine()
    orchestrator = PrimeFlowOrchestrator(engine)

    print("=" * 65)
    print("  PrimeFlow Orchestrator — Building 'Test C' Digital Funnel")
    print(f"  Location: {engine.ghl.location_id}")
    print(f"  Time: {datetime.now().isoformat()}")
    print("=" * 65)

    # ══════════════════════════════════════════════════════════════════
    # PRE-ORCHESTRATOR: Get pipeline info (not in DEDUP_MAP — manual)
    # ══════════════════════════════════════════════════════════════════
    print("\n  Fetching pipeline info (needed for opportunities)...")
    pipes_r = await engine.run({"action": "get_pipelines"})
    all_pipes = pipes_r.get("result", {}).get("data", {}).get("pipelines", [])
    pipeline = next((p for p in all_pipes if p.get("name") == "Sales Pipeline"), None)
    if not pipeline:
        pipeline = all_pipes[0] if all_pipes else {}
    pipeline_id = pipeline.get("id", "")
    stages = pipeline.get("stages", [])
    first_stage_id = stages[0].get("id", "") if stages else ""
    print(f"  Pipeline: '{pipeline.get('name', '')}' ({pipeline_id[:12]}...)")
    print(f"  Stages: {len(stages)}, first: '{stages[0].get('name', '')}'" if stages else "  No stages")

    # Get company ID for user creation
    loc_r = await engine.run({"action": "get_location"})
    loc_data = loc_r.get("result", {}).get("data", {}).get("location",
               loc_r.get("result", {}).get("data", {}))
    company_id = loc_data.get("companyId", "")

    # ══════════════════════════════════════════════════════════════════
    # BUILD COMMAND LIST — All resources as flat commands
    # The orchestrator will GET-before-CREATE automatically
    # ══════════════════════════════════════════════════════════════════
    commands: list[dict] = []

    # --- 10 Custom Fields ---
    fields = [
        {"name": "Test C - Full Name",      "data_type": "TEXT",           "placeholder": "Enter full name"},
        {"name": "Test C - Budget",          "data_type": "NUMERICAL",     "placeholder": "Amount in NIS"},
        {"name": "Test C - Lead Source",     "data_type": "SINGLE_OPTIONS",
         "options": ["Google", "Facebook", "Instagram", "Referral", "Website", "Other"]},
        {"name": "Test C - Lead Status",     "data_type": "SINGLE_OPTIONS",
         "options": ["New", "In Progress", "Interested", "Closing", "Customer", "Lost"]},
        {"name": "Test C - Service Type",    "data_type": "SINGLE_OPTIONS",
         "options": ["Social Media", "Campaigns", "Website Build", "SEO", "Branding", "Full Package"]},
        {"name": "Test C - Meeting Date",    "data_type": "DATE",          "placeholder": "Pick a date"},
        {"name": "Test C - Notes",           "data_type": "LARGE_TEXT",    "placeholder": "Write notes..."},
        {"name": "Test C - Lead Rating",     "data_type": "SINGLE_OPTIONS",
         "options": ["Hot", "Warm", "Cold", "Frozen"]},
        {"name": "Test C - Meeting Booked",  "data_type": "SINGLE_OPTIONS",
         "options": ["Yes", "No", "Pending"]},
        {"name": "Test C - Preferred Channel", "data_type": "SINGLE_OPTIONS",
         "options": ["WhatsApp", "Phone", "Email", "SMS"]},
    ]
    for f in fields:
        commands.append({"action": "create_custom_field", **f})

    # --- 8 Tags ---
    tags = [
        "test-c", "test-c-funnel", "test-c-marketing",
        "new-lead-testc", "hot-lead-testc", "test-c-customer",
        "test-c-meeting-booked", "test-c-hebrew",
    ]
    for tag in tags:
        commands.append({"action": "create_tag", "name": tag})

    # --- 3 Workers ---
    workers = [
        {"first_name": "Test C", "last_name": "Dany",
         "email": "testc.dany@testprimeflow.com", "phone": "+972523334444"},
        {"first_name": "Test C", "last_name": "Fany",
         "email": "testc.fany@testprimeflow.com", "phone": "+972532223333"},
        {"first_name": "Test C", "last_name": "Rany",
         "email": "testc.rany@testprimeflow.com", "phone": "+972543332222"},
    ]
    for w in workers:
        commands.append({
            "action": "create_user",
            "company_id": company_id,
            "first_name": w["first_name"],
            "last_name": w["last_name"],
            "email": w["email"],
            "phone": w["phone"],
            "password": "TestC2026!Pf",
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

    # --- Calendar ---
    commands.append({
        "action": "create_calendar",
        "name": "Test C - Marketing Consultation",
        "description": "Test C - Schedule a free marketing consultation with our team",
        "calendarType": "event",
        "slotDuration": 30,
        "slotInterval": 30,
    })

    # --- 5 Test Contacts ---
    contacts = [
        {"first_name": "TestC Yossi",  "last_name": "Cohen",
         "email": "testc.yossi@testprimeflow.com", "phone": "+97250111001",
         "tags": ["test-c", "new-lead-testc"], "source": "Google",
         "companyName": "Cafe Yossi Ltd"},
        {"first_name": "TestC Michal", "last_name": "Levy",
         "email": "testc.michal@testprimeflow.com", "phone": "+97252111002",
         "tags": ["test-c", "new-lead-testc"], "source": "Facebook",
         "companyName": "Michal Designs"},
        {"first_name": "TestC Avi",    "last_name": "Israeli",
         "email": "testc.avi@testprimeflow.com", "phone": "+97253111003",
         "tags": ["test-c", "hot-lead-testc"], "source": "Referral",
         "companyName": "Israeli Real Estate"},
        {"first_name": "TestC Noa",    "last_name": "David",
         "email": "testc.noa@testprimeflow.com", "phone": "+97254111004",
         "tags": ["test-c", "new-lead-testc"], "source": "Instagram",
         "companyName": "Noa Beauty"},
        {"first_name": "TestC Dani",   "last_name": "Mizrachi",
         "email": "testc.dani@testprimeflow.com", "phone": "+97258111005",
         "tags": ["test-c", "hot-lead-testc"], "source": "Website",
         "companyName": "Mizrachi Tech"},
    ]
    for c in contacts:
        commands.append({"action": "create_contact", **c})

    # --- AI Agent ---
    ai_personality = (
        "אתה נציג אנושי של סוכנות השיווק Test C. "
        "אתה מדבר בעברית, בטון רגוע וטבעי כמו אדם אמיתי שמכיר את התחום. "
        "אתה לא רובוט, אתה חלק מהצוות. "
        "אתה כותב הודעות קצרות וברורות, בלי סימני קריאה מיותרים, "
        "בלי משפטים ארוכים ובלי קלישאות. "
        "אתה מקשיב קודם, מבין את הצורך, ורק אז מציע פתרון."
    )
    ai_goal = (
        "1. לתת מענה מקצועי ומדויק לשאלות של לקוחות\n"
        "2. להבין את הצורך האמיתי של הלקוח לפני שמציעים שירות\n"
        "3. להוביל בעדינות לפגישת ייעוץ עם הצוות\n"
        "4. לשמור על שיחה טבעית, קצרה וללא לחץ"
    )
    ai_instructions = (
        "כללי התנהגות:\n"
        "- דבר תמיד בעברית, בטון שיחתי וטבעי\n"
        "- כתוב הודעות קצרות, 1-3 משפטים מקסימום\n"
        "- אל תשתמש בסימני קריאה אלא אם באמת מתאים\n"
        "- אל תכתוב רשימות ארוכות בהודעה אחת\n"
        "- הקשב לשאלה, ענה בצורה ממוקדת, ושאל שאלה אחת בלבד בכל פעם\n"
        "- אם שואלים אם אתה בוט, תגיד שאתה נציג מצוות Test C\n"
        "- אל תמציא מחירים, תגיד שתשמח לתאם שיחה קצרה עם הצוות\n"
        "- אל תספר על כל השירותים בבת אחת, תשאל מה רלוונטי\n\n"
        "שירותים שלנו: ניהול רשתות, קמפיינים ממומנים, בניית אתרים, SEO, ברנדינג\n"
        "שעות פעילות: א-ה 09:00-18:00 | טלפון: 03-7654321\n\n"
        "דוגמה לפתיחת שיחה:\n"
        "\"היי, מה שלומך? אני מצוות Test C. ראיתי שפנית אלינו, אשמח לעזור. מה מעניין אותך?\"\n\n"
        "דוגמה לתגובה כשליד שואל על מחירים:\n"
        "\"המחירים תלויים בכמה דברים, מה שהייתי מציע זה שיחה קצרה של 10 דקות עם הצוות שלנו, "
        "ככה נוכל לתת לך הצעה מדויקת. מתי נוח לך?\""
    )
    commands.append({
        "action": "create_ai_agent",
        "name": "Test C - עוזר שיווק",
        "business_name": "Test C Marketing Agency",
        "mode": "suggestive",
        "personality": ai_personality,
        "goal": ai_goal,
        "instructions": ai_instructions,
    })

    # --- Knowledge Base for AI Agent ---
    commands.append({
        "action": "create_knowledge_base",
        "name": "Test C - Marketing FAQ",
        "description": "Knowledge base for Test C marketing assistant - Hebrew Q&A",
    })

    # --- 5 Email + SMS Templates ---
    email_html = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Heebo',Arial,sans-serif;background:#1a1a1a;">
  <div style="max-width:600px;margin:0 auto;background:#000;">
    <div style="background:linear-gradient(135deg,#FF1493,#FF69B4);padding:40px 30px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:32px;font-weight:800;">Test C</h1>
      <p style="color:#fff0f5;margin:10px 0 0;font-size:16px;">סוכנות השיווק הדיגיטלי שלך</p>
    </div>
    <div style="padding:40px 30px;background:#1a1a1a;color:#fff;">
      <h2 style="color:#FF69B4;font-size:24px;margin-bottom:20px;">שלום {{contact.first_name}}!</h2>
      <p style="font-size:16px;line-height:1.8;color:#ccc;">תודה שפנית אלינו! אנחנו שמחים שבחרת ב-Test C.</p>
      <div style="text-align:center;margin:35px 0;">
        <a href="#" style="background:linear-gradient(135deg,#FF1493,#FF69B4);color:#fff;padding:15px 40px;text-decoration:none;border-radius:30px;font-size:18px;font-weight:700;display:inline-block;">קבע/י פגישת ייעוץ חינמית</a>
      </div>
      <p style="font-size:14px;color:#888;text-align:center;">שאלות? דברו איתנו: 03-7654321</p>
    </div>
    <div style="background:#000;padding:25px 30px;text-align:center;border-top:2px solid #FF1493;">
      <p style="color:#FF69B4;font-size:14px;margin:0;">Test C | סוכנות שיווק דיגיטלי 2026</p>
    </div>
  </div>
</body>
</html>"""

    commands.append({
        "action": "create_template",
        "name": "Test C - Welcome Email",
        "type": "email",
        "subject": "Test C - ברוכים הבאים! פגישת ייעוץ חינמית מחכה לך",
        "html": email_html,
    })

    followup_html = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Heebo',Arial,sans-serif;background:#1a1a1a;">
  <div style="max-width:600px;margin:0 auto;background:#000;">
    <div style="background:#FF1493;padding:30px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:26px;">Test C - תזכורת</h1>
    </div>
    <div style="padding:30px;background:#1a1a1a;color:#fff;">
      <p style="font-size:16px;line-height:1.8;color:#ccc;">שלום {{contact.first_name}}, רצינו לבדוק אם עדיין מעוניין/ת בפגישת הייעוץ החינמית שלנו.</p>
      <div style="text-align:center;margin:30px 0;">
        <a href="#" style="background:#FF1493;color:#fff;padding:12px 35px;text-decoration:none;border-radius:25px;font-size:16px;font-weight:700;">כן, אני רוצה פגישה!</a>
      </div>
    </div>
  </div>
</body>
</html>"""

    commands.append({
        "action": "create_template",
        "name": "Test C - Follow Up Email",
        "type": "email",
        "subject": "Test C - עדיין מעוניין/ת? פגישת ייעוץ חינמית",
        "html": followup_html,
    })

    sms_templates = [
        ("Test C - Welcome SMS",
         "שלום {{contact.first_name}}! כאן Test C - סוכנות השיווק. נשמח לקבוע פגישת ייעוץ חינמית. השיבו 'כן' ונחזור אליכם! 03-7654321"),
        ("Test C - Reminder SMS",
         "היי {{contact.first_name}}, תזכורת מ-Test C: יש לנו הצעה מיוחדת בשבילך! התקשרו 03-7654321 או השיבו להודעה."),
        ("Test C - Thank You SMS",
         "תודה רבה {{contact.first_name}}! שמחנו לדבר איתך. צוות Test C כאן בשבילך - 03-7654321"),
    ]
    for tmpl_name, tmpl_body in sms_templates:
        commands.append({
            "action": "create_template",
            "name": tmpl_name,
            "type": "sms",
            "body": tmpl_body,
        })

    # --- 7 Brand Custom Values ---
    brand_values = [
        {"name": "company.testc.name", "value": "Test C - Digital Marketing Agency"},
        {"name": "company.testc.phone", "value": "03-7654321"},
        {"name": "company.testc.email", "value": "info@testc-marketing.co.il"},
        {"name": "company.testc.address", "value": "Tel Aviv, Rothschild Blvd 1"},
        {"name": "company.testc.colors", "value": "Pink (#FF1493) & Black (#000000)"},
        {"name": "company.testc.website", "value": "https://testc-marketing.co.il"},
        {"name": "company.testc.slogan", "value": "Test C - שיווק דיגיטלי שעובד"},
    ]
    for bv in brand_values:
        commands.append({"action": "create_custom_value", **bv})

    # --- Opportunities (need contact_id, so handled separately after) ---
    # Note: Opportunities require contact IDs from the contact creation step.
    # Since the orchestrator runs commands sequentially and contacts are created
    # above, we need to handle opportunities after the orchestrator finishes,
    # using the contact IDs from the snapshot.

    # ══════════════════════════════════════════════════════════════════
    # RUN ORCHESTRATOR
    # ══════════════════════════════════════════════════════════════════
    print(f"\n  Total commands: {len(commands)}")
    print(f"  Running orchestrator...\n")

    result = await orchestrator.run(
        commands,
        send_report=True,
        report_subject=f"PrimeFlow Test C Build — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    # ══════════════════════════════════════════════════════════════════
    # POST-ORCHESTRATOR: Opportunities (need contact IDs from snapshot)
    # ══════════════════════════════════════════════════════════════════
    snapshot = result.get("snapshot", {})
    contacts_in_snapshot = snapshot.get("contacts", [])

    # Map email → contact ID
    contact_email_to_id = {}
    for c in contacts_in_snapshot:
        email = (c.get("email") or "").lower()
        if email:
            contact_email_to_id[email] = c.get("id", "")

    # Also check if new contacts were created (from results)
    for ar in result.get("results", []):
        if ar.action == "create_contact" and ar.status == "created" and ar.resource_id:
            # The resource_name is the email for contacts
            pass  # IDs already in snapshot from _add_to_snapshot

    if pipeline_id and first_stage_id:
        print(f"\n{'='*60}")
        print("  POST-ORCHESTRATOR: Creating/Updating Opportunities")
        print(f"{'='*60}\n")

        opp_data = [
            ("testc.yossi@testprimeflow.com", "Test C - Social Media - Cafe Yossi", 3500),
            ("testc.michal@testprimeflow.com", "Test C - Logo Design - Michal Designs", 2000),
            ("testc.avi@testprimeflow.com", "Test C - Website - Israeli Real Estate", 12000),
            ("testc.noa@testprimeflow.com", "Test C - Instagram Campaign - Noa Beauty", 5000),
            ("testc.dani@testprimeflow.com", "Test C - Full Package - Mizrachi Tech", 18000),
        ]

        for email, opp_name, opp_value in opp_data:
            cid = contact_email_to_id.get(email, "")
            if not cid:
                print(f"  ⚠️  No contact ID for {email} — skipping opportunity")
                continue

            # Check existing opportunities for this contact
            opps_r = await engine.run({
                "action": "raw", "method": "GET",
                "endpoint": f"/opportunities/search?location_id={engine.ghl.location_id}"
                            f"&contact_id={cid}&pipeline_id={pipeline_id}&limit=10",
            })
            existing_opps = opps_r.get("result", {}).get("data", {}).get("opportunities", [])

            if existing_opps:
                opp_id = existing_opps[0].get("id", "")
                existing_name = existing_opps[0].get("name", "")
                if existing_name == opp_name:
                    print(f"  ⏭️  '{opp_name}' already set")
                    continue
                r = await engine.run({
                    "action": "update_opportunity",
                    "opportunity_id": opp_id,
                    "name": opp_name,
                    "monetaryValue": opp_value,
                    "status": "open",
                })
                ok = "✅" if r.get("result", {}).get("success") else "❌"
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
                ok = "✅" if r.get("result", {}).get("success") else "❌"
                print(f"  {ok} Created: {opp_name} (NIS {opp_value:,})")
    else:
        print("\n  ⚠️  No pipeline/stage — skipping opportunities")

    # ══════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════
    report_data = result.get("report_data")
    print(f"\n{'='*65}")
    print(f"  ORCHESTRATED TEST C BUILD — COMPLETE")
    print(f"{'='*65}")
    if report_data:
        print(f"  Created:    {len(report_data.created)}")
        print(f"  Updated:    {len(report_data.updated)}")
        print(f"  Duplicates: {len(report_data.duplicates)}")
        print(f"  Errors:     {len(report_data.errors)}")
    print(f"  Report:     {result.get('email_result', {}).get('method', 'N/A')}")
    print(f"{'='*65}\n")

    await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(build_funnel())
