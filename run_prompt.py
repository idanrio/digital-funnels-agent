"""
PrimeFlow Prompt Runner — CLI Entry Point

Execute a structured JSON prompt file through the PrimeFlow engine.
The JSON is validated, commands are run through the Orchestrator,
and a full report (PDF + HTML + Text) is auto-generated and emailed.

Usage:
    python run_prompt.py <prompt_file.json>
    python run_prompt.py --validate <prompt_file.json>
    python run_prompt.py --no-report <prompt_file.json>

Examples:
    python run_prompt.py templates/example_prompt.json
    python run_prompt.py --validate templates/example_prompt.json
"""
from __future__ import annotations
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from server.core.prompt_runner import PromptRunner

# Load .env
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


async def main():
    args = sys.argv[1:]

    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    # Parse flags
    validate_only = "--validate" in args
    no_report = "--no-report" in args

    # Remove flags to get the file path
    file_path = None
    for arg in args:
        if not arg.startswith("--"):
            file_path = arg
            break

    if not file_path:
        print("Error: No prompt file specified.")
        print("Usage: python run_prompt.py <prompt_file.json>")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    if validate_only:
        # Dry-run: validate without executing
        print("\n  Mode: VALIDATE ONLY (dry-run)\n")
        text = Path(file_path).read_text(encoding="utf-8")
        result = PromptRunner.validate(text)

        print(f"  Valid:      {'YES' if result.is_valid else 'NO'}")
        print(f"  Location:   {result.location_id or 'N/A'}")
        print(f"  API Key:    {result.api_key[:12] + '...' if result.api_key else 'N/A'}")
        print(f"  Commands:   {result.commands_count}")
        if result.commands_summary:
            print(f"  Summary:    {result.summary_text}")
        if result.validation_errors:
            print(f"\n  ERRORS ({len(result.validation_errors)}):")
            for err in result.validation_errors:
                print(f"    ✗ {err}")
        if result.validation_warnings:
            print(f"\n  WARNINGS ({len(result.validation_warnings)}):")
            for warn in result.validation_warnings:
                print(f"    ⚠ {warn}")
        if result.is_valid:
            print("\n  ✅ Prompt is valid and ready to execute.")
        else:
            print("\n  ❌ Prompt has errors. Fix them before executing.")
        print()
    else:
        # Full execution
        send_report = not no_report
        result = await PromptRunner.execute_from_file(
            file_path,
            send_report=send_report,
            source="cli",
        )

        if result.validation_errors:
            print("\n  ❌ VALIDATION FAILED:\n")
            for err in result.validation_errors:
                print(f"    ✗ {err}")
            print()
            sys.exit(1)

        if result.success:
            sys.exit(0)
        else:
            print("\n  ❌ Execution failed.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
