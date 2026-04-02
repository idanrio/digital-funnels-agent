# PrimeFlow Digital Funnels Engine

## What This Is
A code-based engine that automatically builds complete digital marketing funnels inside GoHighLevel (GHL) via their API. NO AI in the execution loop — pure deterministic code. Commands in, API calls out.

## Architecture

```
JSON Payload → PromptRunner → Orchestrator (dedup + audit) → Engine → GHL API Client → Report
```

### Core Files
- `server/integrations/ghl.py` — Complete GHL v2 API client (all 36 categories)
- `server/core/engine.py` — Command parser + executor (53 actions)
- `server/core/orchestrator.py` — Smart dedup layer (preflight audit, skip/update existing)
- `server/core/prompt_runner.py` — Entry point, validates JSON, runs orchestrator, generates report
- `server/core/industry_templates.py` — Loads industry JSON templates, fills variables
- `server/core/workflow_engine.py` — GHL workflow knowledge base
- `server/core/agent.py` — Claude ReAct agent (WebSocket chat interface)
- `server/reports/report.py` — HTML/PDF/Text report generator
- `server/utils/error_handler.py` — Error classification + smart retry
- `server/main.py` — FastAPI server (WebSocket + REST + webhooks)
- `server/webhooks/prompt_webhook.py` — External webhook receiver

### Templates
- `templates/industries/` — 6 pre-built Hebrew industry templates (car dealer, dental, gym, law, real estate, restaurant)
- `templates/ai_system_prompt.md` — System prompt for landing page AI (Hebrew)
- `commands/examples/` — Example command JSON files

## Running
```bash
# Execute a prompt:
python run_prompt.py templates/example_prompt.json

# Validate only:
python run_prompt.py --validate templates/example_prompt.json

# Start server:
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

## Command Order
1. custom_fields → 2. tags → 3. users → 4. calendars → 5. contacts → 6. ai_agents → 7. knowledge_bases → 8. faq → 9. templates → 10. custom_values → 11. opportunities

## Key Rules
- `fieldKey` is MANDATORY for create_custom_field (format: `contact.english_name`)
- Money data_type = `MONETORY` (GHL's spelling)
- Phone format: `+972XXXXXXXXX`
- All JSON keys in English, values can be Hebrew
- Tags must be created before contacts that reference them
