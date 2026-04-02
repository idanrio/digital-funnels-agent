"""Debug script — get actual error response bodies from failing GHL API calls."""
import asyncio, os, sys, json, httpx
from pathlib import Path
from datetime import datetime

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


async def debug():
    ts = datetime.now().strftime("%H%M%S")
    async with httpx.AsyncClient(timeout=30) as client:

        print("=" * 60)
        print("DEBUG 1: Custom Field — NUMERICAL type")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/locations/{LOC_ID}/customFields",
            headers=HEADERS,
            json={
                "name": f"Debug Numerical {ts}",
                "dataType": "NUMERICAL",
                "placeholder": "Enter number",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\n" + "=" * 60)
        print("DEBUG 2: Custom Field — SINGLE_OPTIONS with options")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/locations/{LOC_ID}/customFields",
            headers=HEADERS,
            json={
                "name": f"Debug Options {ts}",
                "dataType": "SINGLE_OPTIONS",
                "options": ["A", "B", "C"],
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\n" + "=" * 60)
        print("DEBUG 3: Custom Field — DATE type")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/locations/{LOC_ID}/customFields",
            headers=HEADERS,
            json={
                "name": f"Debug Date {ts}",
                "dataType": "DATE",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\n" + "=" * 60)
        print("DEBUG 4: Custom Field — LARGE_TEXT type")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/locations/{LOC_ID}/customFields",
            headers=HEADERS,
            json={
                "name": f"Debug LargeText {ts}",
                "dataType": "LARGE_TEXT",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\n" + "=" * 60)
        print("DEBUG 5: Custom Object creation")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/objects/",
            headers=HEADERS,
            json={
                "locationId": LOC_ID,
                "labels": {"singular": "TestSale", "plural": "TestSales"},
                "key": f"test_sale_{ts}",
                "description": "Debug test object",
                "primaryDisplayPropertyDetails": {
                    "name": "deal_name",
                    "label": "Deal Name",
                    "dataType": "TEXT",
                    "fieldType": "STANDARD",
                },
                "searchableProperties": ["deal_name"],
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\n" + "=" * 60)
        print("DEBUG 6: AI Agent creation")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/conversation-ai/agents?locationId={LOC_ID}",
            headers=HEADERS,
            json={
                "name": f"Debug Agent {ts}",
                "businessName": "Test Business",
                "mode": "bot",
                "personality": "Friendly helper",
                "goal": "Help customers",
                "instructions": "Be helpful and polite",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\n" + "=" * 60)
        print("DEBUG 7: Custom Values creation")
        print("=" * 60)
        r = await client.post(
            f"{BASE}/locations/{LOC_ID}/customValues",
            headers=HEADERS,
            json={
                "name": f"debug.testvalue.{ts}",
                "value": "Hello World",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        # Also try getting existing custom fields to see the schema
        print("\n" + "=" * 60)
        print("DEBUG 8: GET custom fields (check valid dataTypes)")
        print("=" * 60)
        r = await client.get(
            f"{BASE}/locations/{LOC_ID}/customFields",
            headers=HEADERS,
        )
        print(f"  Status: {r.status_code}")
        data = r.json()
        fields = data.get("customFields", [])
        print(f"  Total existing fields: {len(fields)}")
        types_found = set()
        for f in fields[:5]:
            types_found.add(f.get("dataType"))
            print(f"    - {f.get('name')} | type={f.get('dataType')} | model={f.get('model')}")
        print(f"  Data types in use: {types_found}")


asyncio.run(debug())
