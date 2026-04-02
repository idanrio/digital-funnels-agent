"""Check existing custom fields for duplicate names."""
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


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE}/locations/{LOC_ID}/customFields", headers=HEADERS)
        data = r.json()
        fields = data.get("customFields", [])
        print(f"Total custom fields: {len(fields)}\n")
        for f in fields:
            print(f"  ID={f.get('id')[:12]}... | name={f.get('name')} | type={f.get('dataType')}")

        # Also try creating AI agent with different mode values
        print("\n\nTrying AI agent with mode='suggestive'...")
        r = await client.post(
            f"{BASE}/conversation-ai/agents?locationId={LOC_ID}",
            headers=HEADERS,
            json={
                "name": "Debug Agent Test",
                "businessName": "Test Biz",
                "mode": "suggestive",
                "personality": "Friendly",
                "goal": "Help",
                "instructions": "Be helpful",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        print("\nTrying AI agent with mode='auto'...")
        r = await client.post(
            f"{BASE}/conversation-ai/agents?locationId={LOC_ID}",
            headers=HEADERS,
            json={
                "name": "Debug Agent Test Auto",
                "businessName": "Test Biz",
                "mode": "auto",
                "personality": "Friendly",
                "goal": "Help",
                "instructions": "Be helpful",
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")

        # Also check custom object - the error said we need "key" not "name"
        print("\n\nTrying Custom Object with corrected fields...")
        r = await client.post(
            f"{BASE}/objects/",
            headers=HEADERS,
            json={
                "locationId": LOC_ID,
                "labels": {"singular": "DebugSale", "plural": "DebugSales"},
                "key": "debug_sale_test",
                "description": "Test object",
                "primaryDisplayPropertyDetails": {
                    "key": "deal_name",
                    "dataType": "TEXT",
                },
                "searchableProperties": ["deal_name"],
            },
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body: {r.text[:500]}")


asyncio.run(main())
