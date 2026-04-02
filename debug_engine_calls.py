"""Debug — trace exactly what the engine sends to the API for failing calls."""
import asyncio, os, sys, json
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

from server.core.engine import PrimeFlowEngine

async def debug():
    engine = PrimeFlowEngine()
    ts = datetime.now().strftime("%H%M%S")

    # Test 1: Simple TEXT field (should work)
    print("=" * 60)
    print("TEST 1: TEXT custom field via engine")
    r = await engine.run({
        "action": "create_custom_field",
        "name": f"EngineTest TEXT {ts}",
        "data_type": "TEXT",
        "placeholder": "test",
    })
    print(f"  Success: {r.get('result', {}).get('success')}")
    print(f"  Error: {r.get('result', {}).get('error', 'none')}")
    print(f"  Response body: {r.get('result', {}).get('response_body', 'none')[:300]}")

    # Test 2: NUMERICAL field
    print("\n" + "=" * 60)
    print("TEST 2: NUMERICAL custom field via engine")
    r = await engine.run({
        "action": "create_custom_field",
        "name": f"EngineTest NUM {ts}",
        "data_type": "NUMERICAL",
    })
    print(f"  Success: {r.get('result', {}).get('success')}")
    print(f"  Error: {r.get('result', {}).get('error', 'none')}")
    print(f"  Response body: {r.get('result', {}).get('response_body', 'none')[:300]}")

    # Test 3: SINGLE_OPTIONS with options
    print("\n" + "=" * 60)
    print("TEST 3: SINGLE_OPTIONS custom field via engine")
    r = await engine.run({
        "action": "create_custom_field",
        "name": f"EngineTest OPT {ts}",
        "data_type": "SINGLE_OPTIONS",
        "options": ["A", "B", "C"],
    })
    print(f"  Success: {r.get('result', {}).get('success')}")
    print(f"  Error: {r.get('result', {}).get('error', 'none')}")
    print(f"  Response body: {r.get('result', {}).get('response_body', 'none')[:300]}")

    # Test 4: DATE field
    print("\n" + "=" * 60)
    print("TEST 4: DATE custom field via engine")
    r = await engine.run({
        "action": "create_custom_field",
        "name": f"EngineTest DATE {ts}",
        "data_type": "DATE",
    })
    print(f"  Success: {r.get('result', {}).get('success')}")
    print(f"  Error: {r.get('result', {}).get('error', 'none')}")
    print(f"  Response body: {r.get('result', {}).get('response_body', 'none')[:300]}")

    # Test 5: Custom Value
    print("\n" + "=" * 60)
    print("TEST 5: Custom Value via engine")
    r = await engine.run({
        "action": "create_custom_value",
        "name": f"engine.test.value.{ts}",
        "value": "Hello World",
    })
    print(f"  Success: {r.get('result', {}).get('success')}")
    print(f"  Error: {r.get('result', {}).get('error', 'none')}")
    print(f"  Response body: {r.get('result', {}).get('response_body', 'none')[:300]}")

    # Test 6: Check what valid AI agent modes are
    print("\n" + "=" * 60)
    print("TEST 6: List existing AI agents to see mode values")
    r = await engine.run({
        "action": "raw",
        "method": "GET",
        "endpoint": f"/conversation-ai/agents?locationId={engine.ghl.location_id}",
    })
    agents = r.get("result", {}).get("data", {})
    if isinstance(agents, list):
        for a in agents[:3]:
            print(f"  Agent: {a.get('name')} | mode={a.get('mode')} | type={a.get('type')}")
    elif isinstance(agents, dict):
        agent_list = agents.get("agents", agents.get("data", []))
        if isinstance(agent_list, list):
            for a in agent_list[:3]:
                print(f"  Agent: {a.get('name')} | mode={a.get('mode')} | type={a.get('type')}")
        else:
            print(f"  Raw response: {json.dumps(agents, indent=2)[:500]}")
    else:
        print(f"  Raw: {agents}")

    await engine.close()


asyncio.run(debug())
