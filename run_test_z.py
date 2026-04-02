"""
Run Test Z — Full end-to-end digital funnel test.
Sends approval email, waits for admin to click APPROVE.
Server must be running: uvicorn server.main:app --host 0.0.0.0 --port 8000
"""
import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

from server.core.prompt_runner import PromptRunner


async def main():
    payload = json.loads(Path("templates/test_z.json").read_text(encoding="utf-8"))

    result = await PromptRunner.execute(
        payload,
        send_report=True,
        report_subject="Test Z - Full E2E Digital Funnel",
        source="api",
    )

    if result.validation_errors:
        print("\n  VALIDATION FAILED:")
        for err in result.validation_errors:
            print(f"    - {err}")
        sys.exit(1)

    orch = result.orchestrator_result
    if isinstance(orch, dict) and orch.get("approval_required"):
        print(f"\n  =============================================")
        print(f"  TEST Z — APPROVAL REQUIRED")
        print(f"  =============================================")
        print(f"  Email sent to: {orch.get('admin_email')}")
        print(f"  Pending ID:    {orch.get('pending_id')}")
        print(f"  Commands:      {orch.get('commands_count')}")
        print(f"  Summary:       {orch.get('summary')}")
        print(f"  =============================================")
        print(f"  Check your email and click APPROVE to execute.")
        print(f"  Server is running at http://localhost:8000")
        print(f"  =============================================")
        sys.exit(0)

    if result.success:
        print("\n  Test Z PASSED")
    else:
        print("\n  Test Z FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
