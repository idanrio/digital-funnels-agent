"""
PrimeFlow Engine — Build "Test B" Digital Funnel
=================================================
Full funnel build for a Hebrew marketing company:
1. 10 Custom Fields
2. Sales Database (Custom Object) linked to Contacts
3. Hebrew Conversation AI Assistant
4. 3 Workers (Dany, Fany, Rany)
5. "Test B" Pipeline with appropriate stages
6. 5 Random Test Contacts
7. "Test B" Funnel — Hebrew, Pink & Black branding
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


async def build_funnel():
    engine = PrimeFlowEngine()
    results = {}
    ts = datetime.now().strftime("%H%M%S")

    print("=" * 60)
    print("  🚀 PrimeFlow — Building 'Test B' Digital Funnel")
    print("  📍 Location: 0ryDxpttZ3SBRNMgXp57")
    print(f"  🕐 Time: {datetime.now().isoformat()}")
    print("=" * 60)

    # ==================================================================
    # STEP 1: CREATE 10 CUSTOM FIELDS
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  📋 STEP 1: Creating 10 Custom Fields")
    print(f"{'─'*50}")

    # NOTE: GHL strips Hebrew from fieldKey, so we add unique English suffixes
    # to prevent fieldKey collisions (e.g. "contact.__190620" duplicate)
    custom_fields = [
        {"name": f"שם מלא fullname{ts}", "data_type": "TEXT", "placeholder": "הכנס שם מלא"},
        {"name": f"תקציב משוער budget{ts}", "data_type": "NUMERICAL", "placeholder": "סכום בשח"},
        {"name": f"מקור הגעה source{ts}", "data_type": "SINGLE_OPTIONS",
         "options": ["גוגל", "פייסבוק", "אינסטגרם", "הפניה", "אתר", "אחר"]},
        {"name": f"סטטוס ליד status{ts}", "data_type": "SINGLE_OPTIONS",
         "options": ["חדש", "בטיפול", "מעוניין", "סגירה", "לקוח", "אבוד"]},
        {"name": f"סוג שירות service{ts}", "data_type": "SINGLE_OPTIONS",
         "options": ["ניהול רשתות", "קמפיינים", "בניית אתר", "SEO", "ברנדינג", "חבילה מלאה"]},
        {"name": f"תאריך פגישה meetdate{ts}", "data_type": "DATE", "placeholder": "בחר תאריך"},
        {"name": f"הערות נוספות notes{ts}", "data_type": "LARGE_TEXT", "placeholder": "כתוב הערות..."},
        {"name": f"דירוג ליד rating{ts}", "data_type": "SINGLE_OPTIONS",
         "options": ["חם", "חמים", "קר", "קפוא"]},
        {"name": f"האם נקבעה פגישה booked{ts}", "data_type": "SINGLE_OPTIONS",
         "options": ["כן", "לא", "ממתין"]},
        {"name": f"ערוץ תקשורת מועדף channel{ts}", "data_type": "SINGLE_OPTIONS",
         "options": ["וואטסאפ", "טלפון", "אימייל", "SMS"]},
    ]

    field_ids = []
    for i, field in enumerate(custom_fields, 1):
        r = await engine.run({
            "action": "create_custom_field",
            **field,
        })
        fid = r.get("result", {}).get("data", {}).get("customField", {}).get("id", "")
        field_ids.append(fid)
        status = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {status} Field {i}/10: {field['name']} → {fid or 'FAILED'}")

    results["custom_fields"] = field_ids
    print(f"\n  ✅ Created {len([f for f in field_ids if f])} custom fields")

    # ==================================================================
    # STEP 2: CREATE SALES DATABASE (Custom Object)
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  🗄️  STEP 2: Creating Sales Database (Custom Object)")
    print(f"{'─'*50}")

    # Create the Custom Object schema for Sales via raw API
    r = await engine.run({
        "action": "raw",
        "method": "POST",
        "endpoint": "/objects/",
        "body": {
            "locationId": engine.ghl.location_id,
            "labels": {
                "singular": "מכירה",
                "plural": "מכירות"
            },
            "key": f"sales_{ts}",
            "description": "מאגר מכירות כללי - כל עסקה מקושרת לאיש קשר",
            "primaryDisplayPropertyDetails": {
                "name": "deal_name",
                "key": "deal_name",
                "dataType": "TEXT",
            },
        },
    })
    schema_result = r.get("result", {})
    schema_data = schema_result.get("data", {})
    # API returns {object: {key: "custom_objects.sales_xxx", ...}}
    obj_data = schema_data.get("object", schema_data)
    schema_key = obj_data.get("key", f"custom_objects.sales_{ts}")
    print(f"  {'✅' if schema_result.get('success') else '❌'} Sales Object Schema: {schema_key}")

    # Create association between Sales and Contacts (many sales -> one contact)
    r = await engine.run({
        "action": "raw",
        "method": "POST",
        "endpoint": "/associations/",
        "body": {
            "locationId": engine.ghl.location_id,
            "key": f"sales_to_contact_{ts}",
            "firstObjectKey": schema_key,
            "secondObjectKey": "contact",
            "firstObjectLabel": "Sales",
            "secondObjectLabel": "Contact",
        },
    })
    assoc_result = r.get("result", {})
    print(f"  {'✅' if assoc_result.get('success') else '❌'} Association: Sales → Contact (Many-to-One)")

    results["sales_schema"] = schema_key

    # ==================================================================
    # STEP 3: BUILD HEBREW CONVERSATION AI ASSISTANT
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  🤖 STEP 3: Building Hebrew AI Marketing Assistant")
    print(f"{'─'*50}")

    ai_personality = """אתה עוזר שיווק מקצועי ואדיב של סוכנות השיווק שלנו.
אתה מדבר בעברית בלבד, בצורה חמה ומקצועית.
אתה עוזר ללקוחות עם שאלות כלליות על השירותים שלנו,
עונה על שאלות תמיכה, ומנסה להמיר לידים לפגישות."""

    ai_goal = """המטרה העיקרית שלך היא:
1. לענות על שאלות תמיכה כלליות בצורה מקצועית
2. להציג את השירותים שלנו (ניהול רשתות, קמפיינים, בניית אתרים, SEO, ברנדינג)
3. להמיר לידים חמים לפגישות עם צוות המכירות
4. לאסוף פרטי קשר מלידים מעוניינים
5. לתאם פגישות ולשלוח תזכורות"""

    ai_instructions = """הנחיות חשובות:
- דבר תמיד בעברית
- היה אדיב, מקצועי וחם
- כשליד מביע עניין, הצע פגישת ייעוץ חינמית
- שאל על תקציב, סוג השירות, ולוח זמנים
- אם הלקוח לא מעוניין, הצע לשלוח חומר שיווקי באימייל
- אל תמציא מחירים - הפנה לפגישה עם צוות המכירות
- בסוף כל שיחה שאל אם יש עוד משהו שאפשר לעזור בו

השירותים שלנו:
🎯 ניהול רשתות חברתיות - פייסבוק, אינסטגרם, טיקטוק, לינקדאין
📈 קמפיינים ממומנים - גוגל אדס, פייסבוק אדס, אינסטגרם
🌐 בניית אתרים - אתרי תדמית, חנויות אונליין, דפי נחיתה
🔍 קידום אורגני SEO
🎨 ברנדינג ועיצוב גרפי - לוגו, זהות מותגית, חומרי דפוס
📦 חבילה מלאה - כל השירותים במחיר מיוחד

שעות פעילות: א'-ה' 09:00-18:00
טלפון: 03-1234567
כתובת: תל אביב, רחוב רוטשילד 1"""

    r = await engine.run({
        "action": "raw",
        "method": "POST",
        "endpoint": f"/conversation-ai/agents?locationId={engine.ghl.location_id}",
        "body": {
            "name": "עוזר שיווק - Test B",
            "businessName": "סוכנות השיווק Test B",
            "mode": "suggestive",
            "personality": ai_personality,
            "goal": ai_goal,
            "instructions": ai_instructions,
        },
    })
    agent_result = r.get("result", {})
    agent_id = agent_result.get("data", {}).get("agent", {}).get("id",
               agent_result.get("data", {}).get("id", ""))
    print(f"  {'✅' if agent_result.get('success') else '❌'} AI Agent: עוזר שיווק - Test B → {agent_id}")
    results["ai_agent_id"] = agent_id

    # ==================================================================
    # STEP 4: CREATE 3 WORKERS
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  👥 STEP 4: Creating 3 Workers")
    print(f"{'─'*50}")

    workers = [
        {
            "first_name": "Test", "last_name": "Dany",
            "email": "testdany@gmail.com", "phone": "+972523334444",
            "role": "user", "permissions": {},
        },
        {
            "first_name": "Test", "last_name": "Fany",
            "email": "testfany@gmail.com", "phone": "+972532223333",
            "role": "user", "permissions": {},
        },
        {
            "first_name": "Test", "last_name": "Rany",
            "email": "testrany@gmail.com", "phone": "+972543332222",
            "role": "user", "permissions": {},
        },
    ]

    # For users, we need companyId — try to get it from location
    loc_r = await engine.run({"action": "get_location"})
    loc_data = loc_r.get("result", {}).get("data", {}).get("location",
               loc_r.get("result", {}).get("data", {}))
    company_id = loc_data.get("companyId", "")
    print(f"  📍 Company ID: {company_id}")

    worker_ids = []
    for w in workers:
        r = await engine.run({
            "action": "create_user",
            "company_id": company_id,
            "first_name": w["first_name"],
            "last_name": w["last_name"],
            "email": w["email"],
            "phone": w["phone"],
            "password": f"PrimeFlow2026!",
            "type": "account",
            "role": w["role"],
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
        status = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {status} Worker: {w['first_name']} {w['last_name']} ({w['email']}) → {uid or 'FAILED'}")

    results["worker_ids"] = worker_ids

    # ==================================================================
    # STEP 5: CREATE "TEST B" PIPELINE WITH STAGES
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  🔀 STEP 5: Creating 'Test B' Pipeline & Stages")
    print(f"{'─'*50}")

    # Create pipeline using raw API call (GHL pipelines endpoint)
    pipeline_data = {
        "name": "Test B",
        "stages": [
            {"name": "ליד חדש 🆕", "position": 0},
            {"name": "יצירת קשר ראשוני 📞", "position": 1},
            {"name": "פגישת ייעוץ נקבעה 📅", "position": 2},
            {"name": "הצעת מחיר נשלחה 📄", "position": 3},
            {"name": "משא ומתן 🤝", "position": 4},
            {"name": "סגירה / חתימה ✅", "position": 5},
            {"name": "אבוד ❌", "position": 6},
        ],
        "locationId": engine.ghl.location_id,
    }

    r = await engine.run({
        "action": "raw",
        "method": "POST",
        "endpoint": "/opportunities/pipelines",
        "body": pipeline_data,
    })
    pipeline_result = r.get("result", {})
    raw_data = pipeline_result.get("data", {})
    pipeline_id = raw_data.get("id", raw_data.get("pipeline", {}).get("id", ""))
    print(f"  {'✅' if pipeline_result.get('success') else '❌'} Pipeline: Test B → {pipeline_id}")

    # Get the stages from the pipeline
    stages = raw_data.get("stages", raw_data.get("pipeline", {}).get("stages", []))
    if stages:
        print(f"  📊 Stages created:")
        for s in stages:
            print(f"      • {s.get('name', '')} (ID: {s.get('id', '')[:12]}...)")
        first_stage_id = stages[0].get("id", "")
    else:
        # If stages not in response, get pipelines to find them
        pipes_r = await engine.run({"action": "get_pipelines"})
        all_pipes = pipes_r.get("result", {}).get("data", {}).get("pipelines", [])
        test_b_pipe = next((p for p in all_pipes if p.get("name") == "Test B"), None)
        if test_b_pipe:
            pipeline_id = test_b_pipe.get("id", pipeline_id)
            stages = test_b_pipe.get("stages", [])
            first_stage_id = stages[0].get("id", "") if stages else ""
            print(f"  📊 Found pipeline: {pipeline_id} with {len(stages)} stages")
        else:
            first_stage_id = ""
            print(f"  ⚠️  Could not find stages, will use empty stage ID")

    results["pipeline_id"] = pipeline_id
    results["stages"] = stages

    # ==================================================================
    # STEP 6: CREATE 5 RANDOM TEST CONTACTS
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  👤 STEP 6: Creating 5 Test Contacts")
    print(f"{'─'*50}")

    test_contacts = [
        {
            "first_name": "יוסי", "last_name": "כהן",
            "email": f"yossi.cohen.{ts}@test-primeflow.com",
            "phone": f"+97250{ts}01",
            "tags": ["ליד-חדש", "test-b"],
            "source": "גוגל",
            "companyName": "קפה יוסי בע\"מ",
        },
        {
            "first_name": "מיכל", "last_name": "לוי",
            "email": f"michal.levy.{ts}@test-primeflow.com",
            "phone": f"+97252{ts}02",
            "tags": ["ליד-חדש", "test-b"],
            "source": "פייסבוק",
            "companyName": "מיכל עיצובים",
        },
        {
            "first_name": "אבי", "last_name": "ישראלי",
            "email": f"avi.israeli.{ts}@test-primeflow.com",
            "phone": f"+97253{ts}03",
            "tags": ["ליד-חם", "test-b"],
            "source": "הפניה",
            "companyName": "ישראלי נדל\"ן",
        },
        {
            "first_name": "נועה", "last_name": "דוד",
            "email": f"noa.david.{ts}@test-primeflow.com",
            "phone": f"+97254{ts}04",
            "tags": ["ליד-חדש", "test-b"],
            "source": "אינסטגרם",
            "companyName": "נועה ביוטי",
        },
        {
            "first_name": "דני", "last_name": "מזרחי",
            "email": f"dani.mizrachi.{ts}@test-primeflow.com",
            "phone": f"+97258{ts}05",
            "tags": ["ליד-חם", "test-b"],
            "source": "אתר",
            "companyName": "מזרחי טכנולוגיות",
        },
    ]

    contact_ids = []
    for i, c in enumerate(test_contacts, 1):
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
        status = "✅" if r.get("result", {}).get("success") else "❌"
        print(f"  {status} Contact {i}/5: {c['first_name']} {c['last_name']} ({c['companyName']}) → {cid or 'FAILED'}")

    results["contact_ids"] = contact_ids

    # Create opportunities for each contact in the pipeline
    if pipeline_id and first_stage_id:
        print(f"\n  📊 Creating opportunities for contacts in pipeline...")
        opp_names = [
            "ניהול רשתות - קפה יוסי",
            "עיצוב לוגו - מיכל עיצובים",
            "בניית אתר - ישראלי נדל\"ן",
            "קמפיין אינסטגרם - נועה ביוטי",
            "חבילה מלאה - מזרחי טכנולוגיות",
        ]
        values = [3500, 2000, 12000, 5000, 18000]
        for i, (cid, name, val) in enumerate(zip(contact_ids, opp_names, values)):
            if cid:
                r = await engine.run({
                    "action": "create_opportunity",
                    "pipeline_id": pipeline_id,
                    "stage_id": first_stage_id,
                    "name": name,
                    "contact_id": cid,
                    "monetary_value": val,
                    "status": "open",
                })
                status = "✅" if r.get("result", {}).get("success") else "❌"
                print(f"  {status} Opportunity: {name} (₪{val:,})")

    # ==================================================================
    # STEP 7: BUILD "TEST B" FUNNEL — Hebrew, Pink & Black
    # ==================================================================
    print(f"\n{'─'*50}")
    print("  🎨 STEP 7: Building 'Test B' Funnel (Hebrew + Pink/Black)")
    print(f"{'─'*50}")

    # Create tags for funnel
    funnel_tags = [f"test-b-funnel-{ts}", f"marketing-{ts}", f"hebrew-{ts}"]
    for tag in funnel_tags:
        await engine.run({"action": "create_tag", "name": tag})
    print(f"  ✅ Created funnel tags: {funnel_tags}")

    # Create email template with pink/black branding
    r = await engine.run({
        "action": "create_template",
        "name": f"Test B - תבנית שיווק {ts}",
        "type": "email",
        "subject": "🎯 סוכנות השיווק Test B - הצעה מיוחדת בשבילך!",
        "html": """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="margin:0; padding:0; font-family: 'Heebo', Arial, sans-serif; background-color: #1a1a1a;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #000000;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #FF1493, #FF69B4); padding: 40px 30px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 32px; font-weight: 800;">
                🎯 Test B
            </h1>
            <p style="color: #fff0f5; margin: 10px 0 0 0; font-size: 16px;">
                סוכנות השיווק הדיגיטלי שלך
            </p>
        </div>

        <!-- Body -->
        <div style="padding: 40px 30px; background-color: #1a1a1a; color: #ffffff;">
            <h2 style="color: #FF69B4; font-size: 24px; margin-bottom: 20px;">
                שלום {{contact.first_name}}! 👋
            </h2>
            <p style="font-size: 16px; line-height: 1.8; color: #cccccc;">
                תודה שפנית אלינו! אנחנו שמחים שבחרת ב-Test B,
                סוכנות השיווק הדיגיטלי המובילה.
            </p>
            <p style="font-size: 16px; line-height: 1.8; color: #cccccc;">
                אנחנו מתמחים ב:
            </p>
            <ul style="color: #FF69B4; font-size: 15px; line-height: 2;">
                <li><span style="color: #ffffff;">ניהול רשתות חברתיות</span></li>
                <li><span style="color: #ffffff;">קמפיינים ממומנים</span></li>
                <li><span style="color: #ffffff;">בניית אתרים ודפי נחיתה</span></li>
                <li><span style="color: #ffffff;">SEO וקידום אורגני</span></li>
                <li><span style="color: #ffffff;">ברנדינג ועיצוב</span></li>
            </ul>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 35px 0;">
                <a href="#" style="background: linear-gradient(135deg, #FF1493, #FF69B4);
                   color: #ffffff; padding: 15px 40px; text-decoration: none;
                   border-radius: 30px; font-size: 18px; font-weight: 700;
                   display: inline-block; box-shadow: 0 4px 15px rgba(255,20,147,0.4);">
                    קבע/י פגישת ייעוץ חינמית 🚀
                </a>
            </div>

            <p style="font-size: 14px; color: #888888; text-align: center; margin-top: 30px;">
                יש שאלות? דברו איתנו בוואטסאפ או התקשרו: 03-1234567
            </p>
        </div>

        <!-- Footer -->
        <div style="background-color: #000000; padding: 25px 30px; text-align: center; border-top: 2px solid #FF1493;">
            <p style="color: #FF69B4; font-size: 14px; margin: 0;">
                © 2026 Test B | סוכנות שיווק דיגיטלי
            </p>
            <p style="color: #666666; font-size: 12px; margin: 10px 0 0 0;">
                תל אביב | רחוב רוטשילד 1 | 03-1234567
            </p>
        </div>
    </div>
</body>
</html>""",
    })
    template_result = r.get("result", {})
    print(f"  {'✅' if template_result.get('success') else '❌'} Email Template: Test B - Hebrew/Pink/Black")

    # Create SMS template
    r = await engine.run({
        "action": "create_template",
        "name": f"Test B - SMS שיווק {ts}",
        "type": "sms",
        "body": "שלום {{contact.first_name}}! 🎯 כאן Test B - סוכנות השיווק. נשמח לקבוע איתך פגישת ייעוץ חינמית. השב 'כן' ונחזור אליך! 📞",
    })
    print(f"  {'✅' if r.get('result', {}).get('success') else '❌'} SMS Template: Test B - Hebrew")

    # Create/update custom values for the funnel
    # First, get existing custom values to find IDs for updates
    existing_vals_r = await engine.run({"action": "get_custom_values"})
    existing_vals = existing_vals_r.get("result", {}).get("data", {}).get("customValues", [])
    val_id_map = {v.get("name"): v.get("id") for v in existing_vals}

    brand_values = [
        {"name": "company.testb.name", "value": "Test B - סוכנות שיווק דיגיטלי"},
        {"name": "company.testb.phone", "value": "03-1234567"},
        {"name": "company.testb.email", "value": "info@testb.co.il"},
        {"name": "company.testb.address", "value": "תל אביב, רחוב רוטשילד 1"},
        {"name": "company.testb.colors", "value": "Pink (#FF1493) & Black (#000000)"},
    ]
    for bv in brand_values:
        existing_id = val_id_map.get(bv["name"])
        if existing_id:
            # Update existing value
            r = await engine.run({
                "action": "update_custom_value",
                "value_id": existing_id,
                "name": bv["name"],
                "value": bv["value"],
            })
        else:
            # Create new value
            r = await engine.run({
                "action": "create_custom_value",
                "name": bv["name"],
                "value": bv["value"],
            })
        status = "✅" if r.get("result", {}).get("success") else "❌"
        action = "Updated" if existing_id else "Created"
        print(f"  {status} {action} Brand Value: {bv['name']} = {bv['value']}")

    results["funnel"] = "Test B"

    # ==================================================================
    # SUMMARY
    # ==================================================================
    print(f"\n{'='*60}")
    print(f"  🏆 FUNNEL BUILD COMPLETE — 'Test B'")
    print(f"{'='*60}")
    print(f"""
  📋 Custom Fields:      {len([f for f in field_ids if f])}/10 created
  🗄️  Sales Database:     Custom Object '{schema_key}' + Contact Association
  🤖 AI Assistant:        עוזר שיווק - Test B (ID: {agent_id})
  👥 Workers:             {len([w for w in worker_ids if w])}/3 created
  🔀 Pipeline:            Test B → {len(stages)} stages (ID: {pipeline_id})
  👤 Test Contacts:       {len([c for c in contact_ids if c])}/5 created
  🎨 Funnel Branding:     Hebrew + Pink/Black themes
  📧 Email Template:      RTL Hebrew, gradient pink header
  📱 SMS Template:        Hebrew marketing message
  🏷️  Brand Values:        5 company values set
    """)

    # Save results
    with open("test_b_funnel_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  📄 Results saved to: test_b_funnel_results.json")

    await engine.close()


if __name__ == "__main__":
    asyncio.run(build_funnel())
