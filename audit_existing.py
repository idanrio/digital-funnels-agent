"""Audit ALL existing GHL resources to avoid duplicates in Test C build."""
import asyncio, os, sys, json, httpx
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

API_KEY = os.environ["GHL_API_KEY"]
LOC_ID = os.environ["GHL_LOCATION_ID"]
BASE = "https://services.leadconnectorhq.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


async def audit():
    async with httpx.AsyncClient(timeout=30) as c:
        print("=" * 70)
        print("  FULL GHL LOCATION AUDIT")
        print(f"  Location: {LOC_ID}")
        print(f"  API Key: {API_KEY[:20]}...")
        print("=" * 70)

        # 1. Custom Fields
        print("\n📋 CUSTOM FIELDS:")
        r = await c.get(f"{BASE}/locations/{LOC_ID}/customFields", headers=HEADERS)
        fields = r.json().get("customFields", [])
        print(f"  Total: {len(fields)}")
        for f in fields:
            print(f"    [{f.get('id')[:10]}] {f.get('name')} | type={f.get('dataType')}")

        # 2. Custom Values
        print("\n🏷️ CUSTOM VALUES:")
        r = await c.get(f"{BASE}/locations/{LOC_ID}/customValues", headers=HEADERS)
        vals = r.json().get("customValues", [])
        print(f"  Total: {len(vals)}")
        for v in vals:
            print(f"    [{v.get('id')[:10]}] {v.get('name')} = {str(v.get('value', ''))[:50]}")

        # 3. Tags
        print("\n🏷️ TAGS:")
        r = await c.get(f"{BASE}/locations/{LOC_ID}/tags", headers=HEADERS)
        tags = r.json().get("tags", [])
        print(f"  Total: {len(tags)}")
        for t in tags:
            print(f"    [{t.get('id')[:10]}] {t.get('name')}")

        # 4. Pipelines
        print("\n🔀 PIPELINES:")
        r = await c.get(f"{BASE}/opportunities/pipelines?locationId={LOC_ID}", headers=HEADERS)
        pipes = r.json().get("pipelines", [])
        print(f"  Total: {len(pipes)}")
        for p in pipes:
            stages = p.get("stages", [])
            print(f"    [{p.get('id')[:10]}] {p.get('name')} | {len(stages)} stages")
            for s in stages:
                print(f"        Stage: {s.get('name')} (ID: {s.get('id')[:10]})")

        # 5. Contacts (first 20)
        print("\n👤 CONTACTS (first 20):")
        r = await c.get(f"{BASE}/contacts/?locationId={LOC_ID}&limit=20", headers=HEADERS)
        contacts = r.json().get("contacts", [])
        print(f"  Total shown: {len(contacts)}")
        for ct in contacts:
            name = f"{ct.get('firstName', '')} {ct.get('lastName', '')}".strip()
            print(f"    [{ct.get('id')[:10]}] {name} | {ct.get('email', '')} | tags: {ct.get('tags', [])}")

        # 6. Custom Objects
        print("\n🗄️ CUSTOM OBJECTS:")
        r = await c.get(f"{BASE}/objects/?locationId={LOC_ID}", headers=HEADERS)
        objects = r.json().get("objects", [])
        print(f"  Total: {len(objects)}")
        for o in objects:
            labels = o.get("labels", {})
            print(f"    key={o.get('key')} | {labels.get('singular')}/{labels.get('plural')}")

        # 7. Associations
        print("\n🔗 ASSOCIATIONS:")
        r = await c.get(f"{BASE}/associations/?locationId={LOC_ID}", headers=HEADERS)
        assocs_data = r.json()
        assocs = assocs_data.get("associations", assocs_data.get("data", []))
        if isinstance(assocs, list):
            print(f"  Total: {len(assocs)}")
            for a in assocs:
                print(f"    [{a.get('id', '')[:10]}] {a.get('firstObjectKey')} ↔ {a.get('secondObjectKey')} (key: {a.get('key')})")
        else:
            print(f"  Response: {json.dumps(assocs_data)[:300]}")

        # 8. AI Agents
        print("\n🤖 AI AGENTS:")
        r = await c.get(f"{BASE}/conversation-ai/agents?locationId={LOC_ID}", headers=HEADERS)
        if r.status_code == 200:
            agents_data = r.json()
            agents = agents_data if isinstance(agents_data, list) else agents_data.get("agents", [])
            print(f"  Total: {len(agents)}")
            for a in agents:
                print(f"    [{a.get('id', '')[:10]}] {a.get('name')} | mode={a.get('mode')}")
        else:
            print(f"  Status: {r.status_code} | {r.text[:200]}")

        # 9. Users
        print("\n👥 USERS:")
        # Need companyId for users
        loc_r = await c.get(f"{BASE}/locations/{LOC_ID}", headers=HEADERS)
        loc_data = loc_r.json().get("location", {})
        company_id = loc_data.get("companyId", "")
        if company_id:
            r = await c.get(f"{BASE}/users/?companyId={company_id}&locationId={LOC_ID}", headers=HEADERS)
            if r.status_code == 200:
                users = r.json().get("users", [])
                print(f"  Total: {len(users)}")
                for u in users:
                    print(f"    [{u.get('id', '')[:10]}] {u.get('firstName', '')} {u.get('lastName', '')} | {u.get('email', '')}")
            else:
                print(f"  Status: {r.status_code} | {r.text[:200]}")

        # 10. Calendars
        print("\n📅 CALENDARS:")
        r = await c.get(f"{BASE}/calendars/?locationId={LOC_ID}", headers=HEADERS)
        if r.status_code == 200:
            cals = r.json().get("calendars", [])
            print(f"  Total: {len(cals)}")
            for cal in cals:
                print(f"    [{cal.get('id', '')[:10]}] {cal.get('name')} | type={cal.get('calendarType', cal.get('type', ''))}")
        else:
            print(f"  Status: {r.status_code} | {r.text[:200]}")

        # 11. Funnels
        print("\n🌐 FUNNELS:")
        r = await c.get(f"{BASE}/funnels/lookup?locationId={LOC_ID}", headers=HEADERS)
        if r.status_code == 200:
            funnels_data = r.json()
            funnels = funnels_data.get("funnels", funnels_data.get("data", []))
            if isinstance(funnels, list):
                print(f"  Total: {len(funnels)}")
                for fn in funnels:
                    print(f"    [{fn.get('id', fn.get('_id', ''))[:10]}] {fn.get('name')} | steps={fn.get('steps', fn.get('pages', []))}")
            else:
                print(f"  Raw: {json.dumps(funnels_data)[:300]}")
        else:
            print(f"  Status: {r.status_code} | {r.text[:200]}")

        # 12. Funnels via funnel/page listing
        print("\n🌐 FUNNELS (funnel list endpoint):")
        r = await c.get(f"{BASE}/funnels/funnel/list?locationId={LOC_ID}", headers=HEADERS)
        if r.status_code == 200:
            print(f"  Response: {json.dumps(r.json())[:500]}")
        else:
            print(f"  Status: {r.status_code} | {r.text[:200]}")

        # 13. Templates (snippets)
        print("\n📧 TEMPLATES:")
        r = await c.get(f"{BASE}/locations/{LOC_ID}/templates?originId={LOC_ID}&deleted=false&limit=100", headers=HEADERS)
        if r.status_code == 200:
            templates = r.json().get("templates", [])
            print(f"  Total: {len(templates)}")
            for t in templates[:15]:
                print(f"    [{t.get('id', '')[:10]}] {t.get('name', '')} | type={t.get('type', t.get('templateType', ''))}")
        else:
            print(f"  Status: {r.status_code} | {r.text[:200]}")

        # 14. Workflows
        print("\n⚙️ WORKFLOWS:")
        r = await c.get(f"{BASE}/workflows/?locationId={LOC_ID}", headers=HEADERS)
        if r.status_code == 200:
            wfs = r.json().get("workflows", [])
            print(f"  Total: {len(wfs)}")
            for w in wfs[:10]:
                print(f"    [{w.get('id', '')[:10]}] {w.get('name')} | status={w.get('status')}")
        else:
            print(f"  Status: {r.status_code} | {r.text[:200]}")


asyncio.run(audit())
