"""
Run Test X — Sends approval email, waits for admin to click APPROVE.

Requires the FastAPI server to be running:
    uvicorn server.main:app --host 0.0.0.0 --port 8000

Flow:
    1. Validates the JSON prompt
    2. Sends approval email to primeflow.ai@gmail.com
    3. Stores run as pending
    4. Admin clicks APPROVE in email → server executes the run
"""
import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

from server.core.prompt_runner import PromptRunner


async def main():
    payload = json.loads(Path("templates/test_x.json").read_text(encoding="utf-8"))

    result = await PromptRunner.execute(
        payload,
        send_report=True,
        source="api",
    )

    if result.validation_errors:
        print("\n  VALIDATION FAILED:")
        for err in result.validation_errors:
            print(f"    - {err}")
        sys.exit(1)

    # If approval was required, the run is pending
    orch = result.orchestrator_result
    if isinstance(orch, dict) and orch.get("approval_required"):
        print(f"\n  Approval email sent to {orch.get('admin_email')}")
        print(f"  Pending ID: {orch.get('pending_id')}")
        print(f"  Commands: {orch.get('commands_count')}")
        print(f"\n  Start the server and click APPROVE in the email to execute:")
        print(f"    cd ~/digital-funnels-agent && uvicorn server.main:app --host 0.0.0.0 --port 8000")
        sys.exit(0)

    if result.success:
        print("\n  Test X PASSED")
    else:
        print("\n  Test X FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
