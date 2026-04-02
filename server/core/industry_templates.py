"""
Industry Templates Engine
=========================

Loads pre-built industry template JSON files, fills in customer-specific
variables, and generates a standard commands list for PromptRunner.

NO AI. Pure code. Deterministic.

Usage:
    engine = IndustryTemplateEngine()
    result = engine.generate("car_dealer", {
        "business_name": "...",
        "owner_name": "...",
        "owner_email": "...",
        "owner_phone": "...",
    })
    # result.commands -> list[dict] ready for PromptRunner
"""

from __future__ import annotations

import json
import os
import re
import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "industries"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class TemplateVariable:
    """Definition of a template variable."""
    name: str
    description: str = ""
    required: bool = True
    default: str | None = None


@dataclass
class IndustryTemplate:
    """A loaded industry template."""
    id: str                                         # e.g. "car_dealer"
    name: str                                       # e.g. "Car Dealer / Leasing"
    name_he: str = ""                               # Hebrew name
    description: str = ""
    industries: list[str] = field(default_factory=list)  # e.g. ["automotive", "leasing"]
    variables: list[TemplateVariable] = field(default_factory=list)
    commands: list[dict] = field(default_factory=list)
    command_count: int = 0

    def get_required_variables(self) -> list[TemplateVariable]:
        return [v for v in self.variables if v.required]

    def get_optional_variables(self) -> list[TemplateVariable]:
        return [v for v in self.variables if not v.required]


@dataclass
class GenerateResult:
    """Result of template generation."""
    success: bool
    commands: list[dict] = field(default_factory=list)
    template_id: str = ""
    template_name: str = ""
    commands_count: int = 0
    variables_used: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.success and len(self.errors) == 0 and len(self.commands) > 0


# ---------------------------------------------------------------------------
# Template Engine
# ---------------------------------------------------------------------------

class IndustryTemplateEngine:
    """
    Loads, validates, and generates commands from industry templates.

    Templates are JSON files in templates/industries/ with this structure:
    {
        "id": "car_dealer",
        "name": "Car Dealer / Leasing",
        "name_he": "סוכנות רכב / ליסינג",
        "description": "Full CRM setup for car dealerships...",
        "industries": ["automotive", "car_dealer", "leasing"],
        "variables": {
            "business_name": {"description": "Business name", "required": true},
            "owner_name": {"description": "Owner full name", "required": true},
            "owner_email": {"description": "Owner email", "required": true},
            "owner_phone": {"description": "Owner phone", "required": true},
            "working_hours_start": {"description": "Start time", "required": false, "default": "09:00"},
            "working_hours_end": {"description": "End time", "required": false, "default": "19:00"}
        },
        "commands": [
            {"action": "create_tag", "name": "ליד חדש"},
            {"action": "create_template", "name": "ברוכים הבאים",
             "body": "שלום, תודה שפנית ל{{business_name}}!"},
            {"action": "create_user", "first_name": "{{owner_first_name}}",
             "last_name": "{{owner_last_name}}", "email": "{{owner_email}}"}
        ]
    }
    """

    def __init__(self, templates_dir: str | Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self._templates: dict[str, IndustryTemplate] = {}
        self._load_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_templates(self) -> list[dict]:
        """List all available industry templates with metadata."""
        result = []
        for tid, tmpl in sorted(self._templates.items()):
            result.append({
                "id": tmpl.id,
                "name": tmpl.name,
                "name_he": tmpl.name_he,
                "description": tmpl.description,
                "industries": tmpl.industries,
                "command_count": tmpl.command_count,
                "required_variables": [
                    {"name": v.name, "description": v.description}
                    for v in tmpl.get_required_variables()
                ],
                "optional_variables": [
                    {"name": v.name, "description": v.description, "default": v.default}
                    for v in tmpl.get_optional_variables()
                ],
            })
        return result

    def get_template(self, template_id: str) -> IndustryTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def search_templates(self, query: str) -> list[dict]:
        """Search templates by name, industry, or description."""
        query_lower = query.lower().strip()
        results = []
        for tid, tmpl in self._templates.items():
            # Match against id, name, name_he, industries, description
            searchable = " ".join([
                tmpl.id, tmpl.name.lower(), tmpl.name_he,
                tmpl.description.lower(),
                " ".join(tmpl.industries),
            ])
            if query_lower in searchable:
                results.append({
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "name_he": tmpl.name_he,
                    "command_count": tmpl.command_count,
                })
        return results

    def generate(
        self,
        template_id: str,
        variables: dict[str, str],
    ) -> GenerateResult:
        """
        Generate commands from a template with customer-specific variables.

        Args:
            template_id: The template to use (e.g. "car_dealer")
            variables: Customer variables (e.g. {"business_name": "...", "owner_email": "..."})

        Returns:
            GenerateResult with commands list ready for PromptRunner
        """
        result = GenerateResult(success=False, template_id=template_id)

        # 1. Find template
        template = self._templates.get(template_id)
        if not template:
            result.errors.append(f"Template '{template_id}' not found. "
                                 f"Available: {', '.join(sorted(self._templates.keys()))}")
            return result

        result.template_name = template.name

        # 2. Validate required variables
        missing = []
        for var in template.get_required_variables():
            if var.name not in variables or not variables[var.name].strip():
                missing.append(var.name)

        if missing:
            result.errors.append(
                f"Missing required variables: {', '.join(missing)}. "
                f"Required: {', '.join(v.name for v in template.get_required_variables())}"
            )
            return result

        # 3. Build full variable map (with defaults for optional vars)
        var_map: dict[str, str] = {}
        for var in template.variables:
            if var.name in variables and variables[var.name].strip():
                var_map[var.name] = variables[var.name].strip()
            elif var.default is not None:
                var_map[var.name] = var.default
                result.warnings.append(
                    f"Using default for '{var.name}': '{var.default}'"
                )

        # 4. Auto-derive computed variables
        var_map = self._compute_derived_variables(var_map)

        # 5. Deep copy commands and substitute variables
        commands = copy.deepcopy(template.commands)
        commands = self._substitute_variables(commands, var_map)

        result.success = True
        result.commands = commands
        result.commands_count = len(commands)
        result.variables_used = var_map

        return result

    # ------------------------------------------------------------------
    # Private Methods
    # ------------------------------------------------------------------

    def _load_all(self):
        """Load all .json template files from the templates directory."""
        if not self.templates_dir.exists():
            return

        for f in sorted(self.templates_dir.glob("*.json")):
            try:
                tmpl = self._load_template(f)
                if tmpl:
                    self._templates[tmpl.id] = tmpl
            except Exception as e:
                print(f"  [WARNING] Failed to load template {f.name}: {e}")

    def _load_template(self, path: Path) -> IndustryTemplate | None:
        """Load and validate a single template file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "id" not in data or "commands" not in data:
            return None

        # Parse variables
        variables = []
        for var_name, var_def in data.get("variables", {}).items():
            if isinstance(var_def, dict):
                variables.append(TemplateVariable(
                    name=var_name,
                    description=var_def.get("description", ""),
                    required=var_def.get("required", True),
                    default=var_def.get("default"),
                ))
            elif isinstance(var_def, str):
                # Simple format: "REQUIRED" or a default value
                variables.append(TemplateVariable(
                    name=var_name,
                    required=(var_def.upper() == "REQUIRED"),
                    default=None if var_def.upper() == "REQUIRED" else var_def,
                ))

        return IndustryTemplate(
            id=data["id"],
            name=data.get("name", data["id"]),
            name_he=data.get("name_he", ""),
            description=data.get("description", ""),
            industries=data.get("industries", []),
            variables=variables,
            commands=data.get("commands", []),
            command_count=len(data.get("commands", [])),
        )

    @staticmethod
    def _compute_derived_variables(var_map: dict[str, str]) -> dict[str, str]:
        """
        Auto-compute derived variables from the provided ones.

        If 'owner_name' is provided, derive 'owner_first_name' and 'owner_last_name'.
        Same for 'second_user_name'.
        """
        result = dict(var_map)

        # Helper to split "First Last" into first/last
        def _split_name(full_name: str) -> tuple[str, str]:
            name = full_name.strip()
            if not name:
                return ("", "")
            parts = name.split(None, 1)
            return (parts[0], parts[1] if len(parts) > 1 else "")

        # owner_name → owner_first_name + owner_last_name
        if "owner_name" in result and "owner_first_name" not in result:
            first, last = _split_name(result["owner_name"])
            result["owner_first_name"] = first
            result["owner_last_name"] = last

        # second_user_name → second_user_first_name + second_user_last_name
        if "second_user_name" in result and "second_user_first_name" not in result:
            first, last = _split_name(result["second_user_name"])
            result["second_user_first_name"] = first
            result["second_user_last_name"] = last

        # third_user_name → third_user_first_name + third_user_last_name
        if "third_user_name" in result and "third_user_first_name" not in result:
            first, last = _split_name(result["third_user_name"])
            result["third_user_first_name"] = first
            result["third_user_last_name"] = last

        # Normalize phone numbers (Israeli format)
        for key in list(result.keys()):
            if "phone" in key.lower():
                result[key] = _normalize_phone(result[key])

        # Derive hour/minute integers from time strings (for calendar openHours)
        for key in list(result.keys()):
            if key.endswith("_start") or key.endswith("_end"):
                time_val = result[key]
                if ":" in time_val:
                    parts = time_val.split(":")
                    result[f"{key}_h"] = parts[0]
                    result[f"{key}_m"] = parts[1] if len(parts) > 1 else "0"

        # Also handle the specific working_hours keys
        if "working_hours_start" in result:
            ts = result["working_hours_start"]
            if ":" in ts:
                h, m = ts.split(":", 1)
                result["working_hours_start_h"] = h
                result["working_hours_start_m"] = m
        if "working_hours_end" in result:
            te = result["working_hours_end"]
            if ":" in te:
                h, m = te.split(":", 1)
                result["working_hours_end_h"] = h
                result["working_hours_end_m"] = m

        return result

    @staticmethod
    def _substitute_variables(
        commands: list[dict], var_map: dict[str, str]
    ) -> list[dict]:
        """
        Recursively substitute {{variable}} placeholders in all string values.
        Uses double-brace syntax: {{business_name}}, {{owner_email}}, etc.
        Does NOT touch GHL contact variables like {{contact.first_name}}.

        If a value is ENTIRELY a {{var}} placeholder and the resolved value is
        a pure integer string, it's converted to int (for openHours, slotDuration, etc.).
        """
        def _substitute_value(value: Any) -> Any:
            if isinstance(value, str):
                # Check if the entire value is a single placeholder
                single_match = re.fullmatch(r"\{\{(.+?)\}\}", value.strip())
                if single_match:
                    var_name = single_match.group(1).strip()
                    if "." in var_name:
                        return value  # GHL system variable
                    resolved = var_map.get(var_name, value)
                    # Convert to int if it's a pure number (for JSON integer fields)
                    if isinstance(resolved, str) and resolved.isdigit():
                        return int(resolved)
                    return resolved

                # Multi-placeholder or mixed text
                def _replace(match):
                    var_name = match.group(1).strip()
                    if "." in var_name:
                        return match.group(0)
                    return var_map.get(var_name, match.group(0))
                return re.sub(r"\{\{(.+?)\}\}", _replace, value)
            elif isinstance(value, list):
                return [_substitute_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: _substitute_value(v) for k, v in value.items()}
            return value

        # First pass: substitute
        result = [_substitute_value(cmd) for cmd in commands]

        # Second pass: process special fields and filter
        filtered = []
        for cmd in result:
            action = cmd.get("action", "")

            # Skip user commands with empty email (optional user not provided)
            if action == "create_user" and not cmd.get("email", "").strip():
                continue
            # Skip calendar commands whose name still has unresolved {{}}
            if action == "create_calendar" and "{{" in cmd.get("name", ""):
                continue

            # Convert _availability shorthand to openHours
            if "_availability" in cmd:
                avail = cmd.pop("_availability")
                start = avail.get("start", "09:00")
                end = avail.get("end", "19:00")
                days_str = avail.get("days", "sun-thu")
                cmd["openHours"] = _build_open_hours(start, end, days_str)

            filtered.append(cmd)

        return filtered


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _normalize_phone(phone: str) -> str:
    """Normalize Israeli phone numbers to +972 format."""
    phone = re.sub(r"[\s\-\(\)]", "", phone)
    if phone.startswith("0") and len(phone) == 10:
        phone = "+972" + phone[1:]
    elif phone.startswith("972") and not phone.startswith("+"):
        phone = "+" + phone
    return phone


# Day range mapping
_DAY_RANGES: dict[str, list[int]] = {
    "sun-thu": [0, 1, 2, 3, 4],
    "sun-fri": [0, 1, 2, 3, 4, 5],
    "mon-fri": [1, 2, 3, 4, 5],
    "mon-sat": [1, 2, 3, 4, 5, 6],
    "sun-sat": [0, 1, 2, 3, 4, 5, 6],
}


def _build_open_hours(start: str, end: str, days: str) -> list[dict]:
    """
    Build GHL openHours array from shorthand.

    Args:
        start: "09:00"
        end: "19:00"
        days: "sun-thu" or "0,1,2,3,4"

    Returns:
        [{"daysOfTheWeek": [0], "hours": [{"openHour": 9, ...}]}, ...]
    """
    # Parse hours
    start_parts = start.split(":")
    open_h = int(start_parts[0])
    open_m = int(start_parts[1]) if len(start_parts) > 1 else 0

    end_parts = end.split(":")
    close_h = int(end_parts[0])
    close_m = int(end_parts[1]) if len(end_parts) > 1 else 0

    # Parse days
    days_lower = days.lower().strip()
    if days_lower in _DAY_RANGES:
        day_list = _DAY_RANGES[days_lower]
    elif "," in days:
        day_list = [int(d.strip()) for d in days.split(",") if d.strip().isdigit()]
    else:
        day_list = [0, 1, 2, 3, 4]  # default: Sun-Thu

    hours_block = {
        "openHour": open_h,
        "openMinute": open_m,
        "closeHour": close_h,
        "closeMinute": close_m,
    }

    return [
        {"daysOfTheWeek": [day], "hours": [hours_block.copy()]}
        for day in day_list
    ]
