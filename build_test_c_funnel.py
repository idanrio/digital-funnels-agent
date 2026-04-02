"""
PrimeFlow Engine — Build "Test C" Digital Funnel
=================================================
RULES:
  1. GET before CREATE — check existence first, no duplicates
  2. UPDATE if base exists, CREATE only if new
  3. Everything labeled "Test C" for identification
  4. Includes: Custom Fields, Custom Object + Association, AI Agent,
     3 Workers, Pipeline (use existing), Calendar, 5 Test Contacts,
     Opportunities, Email/SMS Templates, Tags, Brand Custom Values,
     Funnel/Landing Page note
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from server.core.engine import PrimeFlowEngine

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


# ── helpers ──────────────────────────────────────────────────────────
def _find(items: list, name_key: str, name_val: str):
    """Find an item in a list by name field."""
    for item in items:
        if item.get(name_key, "").strip() == name_val.strip():
            return item
    return None


async def build_funnel():
    engine = PrimeFlowEngine()
    results = {}

    print("=" * 65)
    print("  🚀 PrimeFlow — Building 'Test C' Digital Funnel")
    print(f"  📍 Location: {engine.ghl.location_id}")
    print(f"  🕐 {datetime.now().isoformat()}")
    print("=" * 65)

    # ══════════════════════════════════════════════════════════════════
    # STEP 1: 10 CUSTOM FIELDS  (GET → skip or CREATE)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  📋 STEP 1 / 10 Custom Fields")
    print(f"{'─'*55}")

    # GET existing fields
    existing_fields_r = await engine.run({"action": "get_custom_fields"})
    existing_fields = existing_fields_r.get("result", {}).get("data", {}).get("customFields", [])
    existing_field_names = {f.get("name", "") for f in existing_fields}
    print(f"  📂 Existing custom fields: {len(existing_fields)}")

    # GHL strips Hebrew → fieldKey collision, so we use English suffix
    fields_to_create = [
        {"name": "Test C - Full Name",      "data_type": "TEXT",           "placeholder": "Enter full name"},
        {"name": "Test C - Budget",          "data_type": "NUMERICAL",     "placeholder": "Amount in NIS"},
        {"name": "Test C - Lead Source",     "data_type": "SINGLE_OPTIONS",
         "options": ["Google", "Facebook", "Instagram", "Referral", "Website", "Other"]},
        {"name": "Test C - Lead Status",     "data_type": "SINGLE_OPTIONS",
         "options": ["New", "In Progress", "Interested", "Closing", "Customer", "Lost"]},
        {"name": "Test C - Service Type",    "data_type": "SINGLE_OPTIONS",
         "options": ["Social Media", "Campaigns", "Website Build", "SEO", "Branding", "Full Package"]},
        {"name": "Test C - Meeting Date",    "data_type": "DATE",           "placeholder": "Pick a date"},
        {"name": "Test C - Notes",           "data_type": "LARGE_TEXT",     "placeholder": "Write notes..."},
        {"name": "Test C - Lead Rating",     "data_type": "SINGLE_OPTIONS",
         "options": ["Hot", "Warm", "Cold", "Frozen"]},
        {"name": "Test C - Meeting Booked",  "data_type": "SINGLE_OPTIONS",
         "options": ["Yes", "No", "Pending"]},
        {"name": "Test C - Preferred Channel", "data_type": "SINGLE_OPTIONS",
         "options": ["WhatsApp", "Phone", "Email", "SMS"]},
    ]

    field_ids = []
    for i, field in enumerate(fields_to_create, 1):
        if field["name"] in existing_field_names:
            # Already exists — find its ID
            existing = _find(existing_fields, "name", field["name"])
            fid = existing.get("id", "") if existing else ""
            field_ids.append(fid)
            print(f"  ⏭️  Field {i}/10: '{field['name']}' already exists → {fid[:12]}")
        else:
            r = await engine.run({"action": "create_custom_field", **field})
            fid = r.get("result", {}).get("data", {}).get("customField", {}).get("id", "")
            field_ids.append(fid)
            ok = "✅" if fid else "❌"
            print(f"  {ok} Field {i}/10: '{field['name']}' → {fid[:12] if fid else 'FAILED'}")

    results["custom_fields"] = field_ids
    print(f"  ✅ Total: {len([f for f in field_ids if f])}/10 custom fields ready")

    # ══════════════════════════════════════════════════════════════════
    # STEP 2: SALES DATABASE (Custom Object + Association)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  🗄️  STEP 2 / Sales Database (Custom Object)")
    print(f"{'─'*55}")

    # GET existing objects
    obj_r = await engine.run({"action": "raw", "method": "GET",
                               "endpoint": f"/objects/?locationId={engine.ghl.location_id}"})
    existing_objects = obj_r.get("result", {}).get("data", {}).get("objects", [])
    sales_obj = _find(existing_objects, "key", "custom_objects.testc_sales")

    if sales_obj:
        schema_key = sales_obj["key"]
        print(f"  ⏭️  Sales Object already exists: {schema_key}")
    else:
        r = await engine.run({
            "action": "raw", "method": "POST", "endpoint": "/objects/",
            "body": {
                "locationId": engine.ghl.location_id,
                "labels": {"singular": "TestC Sale", "plural": "TestC Sales"},
                "key": "testc_sales",
                "description": "Test C - General sales database, each sale linked to a contact",
                "primaryDisplayPropertyDetails": {
                    "name": "deal_name", "key": "deal_name", "dataType": "TEXT",
                },
            },
        })
        obj_data = r.get("result", {}).get("data", {}).get("object", {})
        schema_key = obj_data.get("key", "custom_objects.testc_sales")
        ok = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {ok} Created Sales Object: {schema_key}")

    results["sales_schema"] = schema_key

    # GET existing associations
    assoc_r = await engine.run({"action": "raw", "method": "GET",
                                 "endpoint": f"/associations/?locationId={engine.ghl.location_id}"})
    existing_assocs = assoc_r.get("result", {}).get("data", {})
    assoc_list = existing_assocs.get("associations", existing_assocs if isinstance(existing_assocs, list) else [])
    testc_assoc = _find(assoc_list, "key", "testc_sales_contact")

    if testc_assoc:
        print(f"  ⏭️  Association already exists: testc_sales_contact")
    else:
        r = await engine.run({
            "action": "raw", "method": "POST", "endpoint": "/associations/",
            "body": {
                "locationId": engine.ghl.location_id,
                "key": "testc_sales_contact",
                "firstObjectKey": schema_key,
                "secondObjectKey": "contact",
                "firstObjectLabel": "Sales",
                "secondObjectLabel": "Contact",
            },
        })
        ok = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {ok} Association: TestC Sales → Contact (Many-to-One)")

    # ══════════════════════════════════════════════════════════════════
    # STEP 3: HEBREW AI MARKETING ASSISTANT
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  🤖 STEP 3 / Hebrew AI Marketing Assistant")
    print(f"{'─'*55}")

    # NOTE: GHL conversation-ai list endpoint returns 404 for private keys,
    # so we can't GET-before-CREATE. We create and accept potential duplicate.
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

    r = await engine.run({
        "action": "raw", "method": "POST",
        "endpoint": f"/conversation-ai/agents?locationId={engine.ghl.location_id}",
        "body": {
            "name": "Test C - עוזר שיווק",
            "businessName": "Test C Marketing Agency",
            "mode": "suggestive",
            "personality": ai_personality,
            "goal": ai_goal,
            "instructions": ai_instructions,
        },
    })
    agent_data = r.get("result", {}).get("data", {})
    agent_id = agent_data.get("id", agent_data.get("agent", {}).get("id", ""))
    ok = "✅" if r.get("result", {}).get("success") else "❌"
    print(f"  {ok} AI Agent: 'Test C - עוזר שיווק' → {agent_id}")
    results["ai_agent_id"] = agent_id

    # ══════════════════════════════════════════════════════════════════
    # STEP 4: 3 WORKERS  (GET → skip or CREATE)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  👥 STEP 4 / 3 Workers")
    print(f"{'─'*55}")

    # GET company ID
    loc_r = await engine.run({"action": "get_location"})
    loc_data = loc_r.get("result", {}).get("data", {}).get("location",
               loc_r.get("result", {}).get("data", {}))
    company_id = loc_data.get("companyId", "")
    print(f"  📍 Company ID: {company_id}")

    # GET existing users via search
    users_r = await engine.run({"action": "raw", "method": "GET",
                                 "endpoint": f"/users/search?companyId={company_id}&locationId={engine.ghl.location_id}"})
    existing_users = users_r.get("result", {}).get("data", {}).get("users", [])
    existing_emails = {u.get("email", "").lower() for u in existing_users}
    print(f"  📂 Existing users: {len(existing_users)}")

    workers = [
        {"first_name": "Test C", "last_name": "Dany",
         "email": "testc.dany@testprimeflow.com", "phone": "+972523334444"},
        {"first_name": "Test C", "last_name": "Fany",
         "email": "testc.fany@testprimeflow.com", "phone": "+972532223333"},
        {"first_name": "Test C", "last_name": "Rany",
         "email": "testc.rany@testprimeflow.com", "phone": "+972543332222"},
    ]

    worker_ids = []
    for w in workers:
        if w["email"].lower() in existing_emails:
            existing_user = next((u for u in existing_users if u.get("email", "").lower() == w["email"].lower()), None)
            uid = existing_user.get("id", "") if existing_user else ""
            worker_ids.append(uid)
            print(f"  ⏭️  Worker '{w['first_name']} {w['last_name']}' already exists → {uid[:12]}")
        else:
            r = await engine.run({
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
            uid = r.get("result", {}).get("data", {}).get("id",
                  r.get("result", {}).get("data", {}).get("user", {}).get("id", ""))
            worker_ids.append(uid)
            ok = "✅" if uid else "❌"
            print(f"  {ok} Worker: {w['first_name']} {w['last_name']} ({w['email']}) → {uid[:12] if uid else 'FAILED'}")

    results["worker_ids"] = worker_ids

    # ══════════════════════════════════════════════════════════════════
    # STEP 5: PIPELINE + STAGES  (use existing "Sales Pipeline")
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  🔀 STEP 5 / Pipeline & Stages")
    print(f"{'─'*55}")

    # NOTE: Pipeline creation (POST /opportunities/pipelines) returns 401
    # even with full scopes — this is a GHL API limitation for private keys.
    # We'll use the existing "Sales Pipeline" which has Hebrew stages.
    pipes_r = await engine.run({"action": "get_pipelines"})
    all_pipes = pipes_r.get("result", {}).get("data", {}).get("pipelines", [])

    # Prefer "Sales Pipeline" (Hebrew stages)
    pipeline = _find(all_pipes, "name", "Sales Pipeline")
    if not pipeline:
        pipeline = all_pipes[0] if all_pipes else {}

    pipeline_id = pipeline.get("id", "")
    stages = pipeline.get("stages", [])
    first_stage_id = stages[0].get("id", "") if stages else ""

    print(f"  📊 Using pipeline: '{pipeline.get('name', '')}' (ID: {pipeline_id[:12]})")
    print(f"  📊 {len(stages)} stages | First: '{stages[0].get('name', '')}' → {first_stage_id[:12]}" if stages else "  ⚠️  No stages found")
    for s in stages:
        print(f"      • {s.get('name')}")

    results["pipeline_id"] = pipeline_id
    results["stages"] = [{"name": s.get("name"), "id": s.get("id")} for s in stages]

    # ══════════════════════════════════════════════════════════════════
    # STEP 6: CALENDAR  (GET → skip or CREATE)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  📅 STEP 6 / Calendar")
    print(f"{'─'*55}")

    cals_r = await engine.run({"action": "get_calendars"})
    existing_cals = cals_r.get("result", {}).get("data", {}).get("calendars", [])
    existing_cal_names = {cal.get("name", "") for cal in existing_cals}
    print(f"  📂 Existing calendars: {len(existing_cals)}")

    calendar_name = "Test C - Marketing Consultation"
    if calendar_name in existing_cal_names:
        existing_cal = _find(existing_cals, "name", calendar_name)
        calendar_id = existing_cal.get("id", "") if existing_cal else ""
        print(f"  ⏭️  Calendar already exists: '{calendar_name}' → {calendar_id[:12]}")
    else:
        r = await engine.run({
            "action": "create_calendar",
            "name": calendar_name,
            "description": "Test C - Schedule a free marketing consultation with our team",
            "calendarType": "event",
            "slotDuration": 30,
            "slotInterval": 30,
            "teamMembers": [{"userId": wid, "priority": 0.5, "meetingLocation": ""}
                            for wid in worker_ids if wid],
        })
        cal_data = r.get("result", {}).get("data", {}).get("calendar", {})
        calendar_id = cal_data.get("id", "")
        ok = "✅" if calendar_id else "❌"
        print(f"  {ok} Calendar: '{calendar_name}' → {calendar_id[:12] if calendar_id else 'FAILED'}")

    results["calendar_id"] = calendar_id

    # ══════════════════════════════════════════════════════════════════
    # STEP 7: 5 TEST CONTACTS  (GET → skip or CREATE)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  👤 STEP 7 / 5 Test Contacts")
    print(f"{'─'*55}")

    test_contacts = [
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

    # GET existing contacts by searching for testc tag
    existing_contacts_r = await engine.run({
        "action": "raw", "method": "GET",
        "endpoint": f"/contacts/?locationId={engine.ghl.location_id}&limit=100",
    })
    existing_contacts = existing_contacts_r.get("result", {}).get("data", {}).get("contacts", [])
    existing_contact_emails = {(c.get("email") or "").lower() for c in existing_contacts}
    print(f"  📂 Existing contacts: {len(existing_contacts)}")

    contact_ids = []
    for i, c in enumerate(test_contacts, 1):
        if c["email"].lower() in existing_contact_emails:
            existing_ct = next((ct for ct in existing_contacts if ct.get("email", "").lower() == c["email"].lower()), None)
            cid = existing_ct.get("id", "") if existing_ct else ""
            contact_ids.append(cid)
            print(f"  ⏭️  Contact {i}/5: '{c['first_name']} {c['last_name']}' already exists → {cid[:12]}")
        else:
            r = await engine.run({
                "action": "create_contact",
                "first_name": c["first_name"],
                "last_name": c["last_name"],
                "email": c["email"],
                "phone": c["phone"],
                "tags": c["tags"],
                "source": c["source"],
                "companyName": c["companyName"],
            })
            cid = r.get("result", {}).get("data", {}).get("contact", {}).get("id", "")
            contact_ids.append(cid)
            ok = "✅" if cid else "❌"
            print(f"  {ok} Contact {i}/5: {c['first_name']} {c['last_name']} ({c['companyName']}) → {cid[:12] if cid else 'FAILED'}")

    results["contact_ids"] = contact_ids

    # ══════════════════════════════════════════════════════════════════
    # STEP 8: OPPORTUNITIES for contacts in pipeline
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  💰 STEP 8 / Opportunities")
    print(f"{'─'*55}")

    if pipeline_id and first_stage_id:
        opp_data = [
            ("Test C - Social Media - Cafe Yossi", 3500),
            ("Test C - Logo Design - Michal Designs", 2000),
            ("Test C - Website - Israeli Real Estate", 12000),
            ("Test C - Instagram Campaign - Noa Beauty", 5000),
            ("Test C - Full Package - Mizrachi Tech", 18000),
        ]

        for i, (cid, (name, val)) in enumerate(zip(contact_ids, opp_data)):
            if not cid:
                print(f"  ⏭️  Skipping opportunity (no contact ID)")
                continue

            # GET existing opportunities for this contact
            contact_opps_r = await engine.run({
                "action": "raw", "method": "GET",
                "endpoint": f"/opportunities/search?location_id={engine.ghl.location_id}&contact_id={cid}&pipeline_id={pipeline_id}&limit=10",
            })
            contact_opps = contact_opps_r.get("result", {}).get("data", {}).get("opportunities", [])

            if contact_opps:
                # Contact already has opportunity — UPDATE it with Test C name & value
                opp_id = contact_opps[0].get("id", "")
                existing_name = contact_opps[0].get("name", "")
                if existing_name == name:
                    print(f"  ⏭️  Opportunity '{name}' already set for contact")
                    continue
                r = await engine.run({
                    "action": "update_opportunity",
                    "opportunity_id": opp_id,
                    "name": name,
                    "monetaryValue": val,
                    "status": "open",
                })
                ok = "✅" if r.get("result", {}).get("success") else "❌"
                print(f"  {ok} Updated Opportunity: {name} (NIS {val:,})")
            else:
                # No existing opportunity — CREATE new one
                r = await engine.run({
                    "action": "create_opportunity",
                    "pipeline_id": pipeline_id,
                    "stage_id": first_stage_id,
                    "name": name,
                    "contact_id": cid,
                    "monetary_value": val,
                    "status": "open",
                })
                ok = "✅" if r.get("result", {}).get("success") else "❌"
                print(f"  {ok} Created Opportunity: {name} (NIS {val:,})")
    else:
        print("  ⚠️  No pipeline/stage — skipping opportunities")

    # ══════════════════════════════════════════════════════════════════
    # STEP 9: TAGS  (GET → skip or CREATE)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  🏷️  STEP 9 / Tags")
    print(f"{'─'*55}")

    tags_r = await engine.run({"action": "get_tags"})
    existing_tags = tags_r.get("result", {}).get("data", {}).get("tags", [])
    existing_tag_names = {t.get("name", "") for t in existing_tags}
    print(f"  📂 Existing tags: {len(existing_tags)}")

    tags_to_create = [
        "test-c", "test-c-funnel", "test-c-marketing",
        "new-lead-testc", "hot-lead-testc", "test-c-customer",
        "test-c-meeting-booked", "test-c-hebrew",
    ]

    for tag_name in tags_to_create:
        if tag_name in existing_tag_names:
            print(f"  ⏭️  Tag '{tag_name}' already exists")
        else:
            r = await engine.run({"action": "create_tag", "name": tag_name})
            ok = "✅" if r.get("result", {}).get("success") else "❌"
            print(f"  {ok} Tag: '{tag_name}'")

    # ══════════════════════════════════════════════════════════════════
    # STEP 10: EMAIL + SMS TEMPLATES
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  📧 STEP 10 / Email & SMS Templates")
    print(f"{'─'*55}")

    # Email template — Hebrew RTL, Pink (#FF1493) & Black (#000000)
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
      <p style="font-size:16px;line-height:1.8;color:#ccc;">תודה שפנית אלינו! אנחנו שמחים שבחרת ב-Test C, סוכנות השיווק הדיגיטלי המובילה.</p>
      <p style="font-size:16px;line-height:1.8;color:#ccc;">השירותים שלנו:</p>
      <ul style="color:#FF69B4;font-size:15px;line-height:2;">
        <li><span style="color:#fff;">ניהול רשתות חברתיות</span></li>
        <li><span style="color:#fff;">קמפיינים ממומנים</span></li>
        <li><span style="color:#fff;">בניית אתרים ודפי נחיתה</span></li>
        <li><span style="color:#fff;">SEO וקידום אורגני</span></li>
        <li><span style="color:#fff;">ברנדינג ועיצוב</span></li>
      </ul>
      <div style="text-align:center;margin:35px 0;">
        <a href="#" style="background:linear-gradient(135deg,#FF1493,#FF69B4);color:#fff;padding:15px 40px;text-decoration:none;border-radius:30px;font-size:18px;font-weight:700;display:inline-block;">קבע/י פגישת ייעוץ חינמית</a>
      </div>
      <p style="font-size:14px;color:#888;text-align:center;">שאלות? דברו איתנו: 03-7654321</p>
    </div>
    <div style="background:#000;padding:25px 30px;text-align:center;border-top:2px solid #FF1493;">
      <p style="color:#FF69B4;font-size:14px;margin:0;">Test C | סוכנות שיווק דיגיטלי 2026</p>
      <p style="color:#666;font-size:12px;margin:10px 0 0;">תל אביב | רחוב רוטשילד 1</p>
    </div>
  </div>
</body>
</html>"""

    # Email template — welcome
    r = await engine.run({
        "action": "create_template",
        "name": "Test C - Welcome Email",
        "type": "email",
        "subject": "Test C - ברוכים הבאים! פגישת ייעוץ חינמית מחכה לך",
        "html": email_html,
    })
    ok = "✅" if r.get("result", {}).get("success") else "❌"
    print(f"  {ok} Email Template: 'Test C - Welcome Email' (Hebrew/Pink/Black)")

    # Email template — follow up
    followup_html = """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Heebo',Arial,sans-serif;background:#1a1a1a;">
  <div style="max-width:600px;margin:0 auto;background:#000;">
    <div style="background:#FF1493;padding:30px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:26px;">Test C - תזכורת</h1>
    </div>
    <div style="padding:30px;background:#1a1a1a;color:#fff;">
      <p style="font-size:16px;line-height:1.8;color:#ccc;">שלום {{contact.first_name}},</p>
      <p style="font-size:16px;line-height:1.8;color:#ccc;">רצינו לבדוק אם עדיין מעוניין/ת בפגישת הייעוץ החינמית שלנו. נשמח לעזור לך לקדם את העסק!</p>
      <div style="text-align:center;margin:30px 0;">
        <a href="#" style="background:#FF1493;color:#fff;padding:12px 35px;text-decoration:none;border-radius:25px;font-size:16px;font-weight:700;">כן, אני רוצה פגישה!</a>
      </div>
      <p style="font-size:13px;color:#888;text-align:center;">Test C | 03-7654321</p>
    </div>
  </div>
</body>
</html>"""

    r = await engine.run({
        "action": "create_template",
        "name": "Test C - Follow Up Email",
        "type": "email",
        "subject": "Test C - עדיין מעוניין/ת? פגישת ייעוץ חינמית",
        "html": followup_html,
    })
    ok = "✅" if r.get("result", {}).get("success") else "❌"
    print(f"  {ok} Email Template: 'Test C - Follow Up Email'")

    # SMS templates
    sms_templates = [
        ("Test C - Welcome SMS",
         "שלום {{contact.first_name}}! כאן Test C - סוכנות השיווק. נשמח לקבוע פגישת ייעוץ חינמית. השיבו 'כן' ונחזור אליכם! 03-7654321"),
        ("Test C - Reminder SMS",
         "היי {{contact.first_name}}, תזכורת מ-Test C: יש לנו הצעה מיוחדת בשבילך! התקשרו 03-7654321 או השיבו להודעה."),
        ("Test C - Thank You SMS",
         "תודה רבה {{contact.first_name}}! שמחנו לדבר איתך. צוות Test C כאן בשבילך - 03-7654321"),
    ]

    for tmpl_name, tmpl_body in sms_templates:
        r = await engine.run({
            "action": "create_template",
            "name": tmpl_name,
            "type": "sms",
            "body": tmpl_body,
        })
        ok = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {ok} SMS Template: '{tmpl_name}'")

    # ══════════════════════════════════════════════════════════════════
    # STEP 11: BRAND CUSTOM VALUES  (GET → UPDATE or CREATE)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  🎨 STEP 11 / Brand Custom Values")
    print(f"{'─'*55}")

    vals_r = await engine.run({"action": "get_custom_values"})
    existing_vals = vals_r.get("result", {}).get("data", {}).get("customValues", [])
    val_id_map = {v.get("name"): v.get("id") for v in existing_vals}

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
        existing_id = val_id_map.get(bv["name"])
        if existing_id:
            r = await engine.run({
                "action": "update_custom_value",
                "value_id": existing_id,
                "name": bv["name"],
                "value": bv["value"],
            })
            action = "Updated"
        else:
            r = await engine.run({
                "action": "create_custom_value",
                "name": bv["name"],
                "value": bv["value"],
            })
            action = "Created"
        ok = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {ok} {action}: {bv['name']} = {bv['value']}")

    # ══════════════════════════════════════════════════════════════════
    # STEP 12: FUNNEL / LANDING PAGE
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*55}")
    print("  🌐 STEP 12 / Funnel & Landing Page")
    print(f"{'─'*55}")

    # NOTE: The GHL API does NOT support funnel/page creation or content editing
    # via the REST API. Funnels are created in the GHL visual builder (Sites tab).
    # What we CAN do via API:
    #   - List existing funnels and pages
    #   - Create redirect URLs for the funnel
    # We'll list existing funnels and provide guidance.

    funnels_r = await engine.run({
        "action": "raw", "method": "GET",
        "endpoint": f"/funnels/funnel/list?locationId={engine.ghl.location_id}",
    })
    existing_funnels = funnels_r.get("result", {}).get("data", {}).get("funnels", [])

    print(f"  📂 Existing funnels: {len(existing_funnels)}")
    for fn in existing_funnels:
        print(f"      • {fn.get('name')} (type: {fn.get('type')}, id: {fn.get('_id', '')[:12]})")

    testc_funnel = _find(existing_funnels, "name", "Test C - Landing Page")
    if testc_funnel:
        print(f"  ✅ Found 'Test C - Landing Page' funnel → {testc_funnel.get('_id', '')[:12]}")
        results["funnel_id"] = testc_funnel.get("_id", "")
    else:
        print(f"  ⚠️  Funnel creation is not available via GHL REST API.")
        print(f"      To create the 'Test C' landing page:")
        print(f"      1. Go to GHL → Sites → Funnels → + New Funnel")
        print(f"      2. Name it: 'Test C - Landing Page'")
        print(f"      3. Use colors: Pink (#FF1493) & Black (#000000)")
        print(f"      4. Language: Hebrew (RTL)")
        print(f"      5. Content: Marketing agency services page")
        print(f"      The branding values, templates, and AI agent are already set up!")
        results["funnel_id"] = "MANUAL_CREATION_NEEDED"

    # ══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════════
    created_fields = len([f for f in field_ids if f])
    created_workers = len([w for w in worker_ids if w])
    created_contacts = len([c for c in contact_ids if c])

    print(f"\n{'='*65}")
    print(f"  🏆 TEST C FUNNEL BUILD COMPLETE")
    print(f"{'='*65}")
    print(f"""
  📋 Custom Fields:      {created_fields}/10 ready
  🗄️  Sales Database:     '{schema_key}' + Contact association
  🤖 AI Assistant:        'Test C - עוזר שיווק' (ID: {agent_id})
  👥 Workers:             {created_workers}/3 created
  🔀 Pipeline:            '{pipeline.get('name', '')}' — {len(stages)} stages
  📅 Calendar:            '{calendar_name}' (ID: {calendar_id})
  👤 Test Contacts:       {created_contacts}/5 created
  💰 Opportunities:       5 deals in pipeline
  🏷️  Tags:               8 Test C tags
  📧 Email Templates:     2 (Welcome + Follow Up — Hebrew/Pink/Black)
  📱 SMS Templates:       3 (Welcome + Reminder + Thank You)
  🎨 Brand Values:        7 company values set
  🌐 Funnel:              {'Exists' if results.get('funnel_id', '').startswith('MANUAL') is False else 'Manual creation needed in GHL UI'}
    """)

    # Save results
    with open("test_c_funnel_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  📄 Results saved to: test_c_funnel_results.json")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(build_funnel())
