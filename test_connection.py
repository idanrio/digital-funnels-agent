"""
Quick test: Verify GHL API + Anthropic API connections are working.
Run: python3 test_connection.py
"""

import asyncio
import os
import sys

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

print("=" * 50)
print("  PrimeFlow AI - Connection Test")
print("=" * 50)
print()

# ---- Test 1: GHL API ----
async def test_ghl():
    import httpx

    base_url = os.getenv("GHL_BASE_URL", "https://services.leadconnectorhq.com")
    api_key = os.getenv("GHL_API_KEY", "")
    location_id = os.getenv("GHL_LOCATION_ID", "")

    print(f"[GHL] Base URL:     {base_url}")
    print(f"[GHL] Location ID:  {location_id}")
    print(f"[GHL] API Key:      {api_key[:15]}...")
    print()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Version": "2021-07-28",
    }

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=15) as client:
        # Test 1a: Get contacts
        print("[TEST 1] Fetching contacts...")
        try:
            r = await client.get("/contacts/", params={"locationId": location_id, "limit": 3})
            if r.status_code == 200:
                data = r.json()
                contacts = data.get("contacts", [])
                print(f"  ✅ SUCCESS - Found {len(contacts)} contacts")
                for c in contacts[:3]:
                    name = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                    email = c.get("email", "no email")
                    print(f"     - {name} ({email})")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

        # Test 1b: Get custom fields
        print()
        print("[TEST 2] Fetching custom fields...")
        try:
            r = await client.get(f"/locations/{location_id}/customFields")
            if r.status_code == 200:
                data = r.json()
                fields = data.get("customFields", [])
                print(f"  ✅ SUCCESS - Found {len(fields)} custom fields")
                for f_item in fields[:5]:
                    print(f"     - {f_item.get('name')} ({f_item.get('dataType')})")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

        # Test 1c: Get workflows
        print()
        print("[TEST 3] Fetching workflows...")
        try:
            r = await client.get("/workflows/", params={"locationId": location_id})
            if r.status_code == 200:
                data = r.json()
                workflows = data.get("workflows", [])
                print(f"  ✅ SUCCESS - Found {len(workflows)} workflows")
                for w in workflows[:5]:
                    print(f"     - {w.get('name')} (status: {w.get('status', 'unknown')})")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

        # Test 1d: Get funnels
        print()
        print("[TEST 4] Fetching funnels...")
        try:
            r = await client.get("/funnels/funnel/list", params={"locationId": location_id})
            if r.status_code == 200:
                data = r.json()
                funnels = data.get("funnels", [])
                print(f"  ✅ SUCCESS - Found {len(funnels)} funnels")
                for fun in funnels[:5]:
                    print(f"     - {fun.get('name')} (steps: {fun.get('stepsCount', '?')})")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

        # Test 1e: Get pipelines
        print()
        print("[TEST 5] Fetching pipelines...")
        try:
            r = await client.get("/opportunities/pipelines", params={"locationId": location_id})
            if r.status_code == 200:
                data = r.json()
                pipelines = data.get("pipelines", [])
                print(f"  ✅ SUCCESS - Found {len(pipelines)} pipelines")
                for p in pipelines[:5]:
                    stages = [s.get("name") for s in p.get("stages", [])]
                    print(f"     - {p.get('name')} (stages: {', '.join(stages)})")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

        # Test 1f: Get calendars
        print()
        print("[TEST 6] Fetching calendars...")
        try:
            r = await client.get("/calendars/", params={"locationId": location_id})
            if r.status_code == 200:
                data = r.json()
                calendars = data.get("calendars", [])
                print(f"  ✅ SUCCESS - Found {len(calendars)} calendars")
                for cal in calendars[:5]:
                    print(f"     - {cal.get('name')}")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

        # Test 1g: Get tags
        print()
        print("[TEST 7] Fetching tags...")
        try:
            r = await client.get(f"/locations/{location_id}/tags")
            if r.status_code == 200:
                data = r.json()
                tags = data.get("tags", [])
                print(f"  ✅ SUCCESS - Found {len(tags)} tags")
                for t in tags[:10]:
                    print(f"     - {t.get('name')}")
            else:
                print(f"  ❌ FAILED - Status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")


# ---- Test 2: Anthropic API ----
def test_anthropic():
    print()
    print("=" * 50)
    print()
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    print(f"[Anthropic] API Key: {api_key[:20]}...")
    print()
    print("[TEST 8] Testing Claude API...")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": "Say 'PrimeFlow AI connection successful!' in Hebrew and English. Keep it short."}]
        )
        text = response.content[0].text
        print(f"  ✅ SUCCESS - Claude responded:")
        print(f"     {text}")
        print(f"     (tokens used: {response.usage.input_tokens} in, {response.usage.output_tokens} out)")
    except ImportError:
        print("  ⚠️  anthropic package not installed. Run: pip install anthropic")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")


# ---- Run ----
print()
asyncio.run(test_ghl())
test_anthropic()

print()
print("=" * 50)
print("  Tests complete!")
print("=" * 50)
print()
