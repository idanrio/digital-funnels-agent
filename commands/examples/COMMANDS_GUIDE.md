# PrimeFlow Engine - Commands Guide / מדריך פקודות

## How to Run / איך להריץ

```bash
# Single command (inline):
python3 -m server.core.engine '{"action": "get_contacts"}'

# From JSON file:
python3 -m server.core.engine commands/examples/01_real_estate_funnel.json

# Batch (all files in directory):
python3 -m server.core.engine commands/examples/

# Interactive mode:
python3 -m server.core.engine

# List all 53 actions:
python3 -m server.core.engine --help
```

## Available Actions (53 total)

### Create
- `create_contact` / `create_contacts` (bulk)
- `create_user`
- `create_tag` / `create_tags`
- `create_custom_field` / `create_custom_fields`
- `create_custom_value`
- `create_opportunity`
- `create_template` (email/sms)
- `create_calendar`
- `create_appointment`
- `create_product`
- `create_blog_post`
- `create_note`
- `create_task`
- `create_business`
- `create_link`
- `create_social_post`
- `create_funnel` (full orchestrator)

### Read
- `get_contacts` / `search_contacts`
- `get_users`
- `get_tags`
- `get_custom_fields`
- `get_pipelines`
- `get_workflows`
- `get_funnels`
- `get_calendars`
- `get_products`
- `get_campaigns`
- `get_forms`
- `get_surveys`
- `get_businesses`
- `get_links`
- `get_conversations`
- `get_notes`
- `get_tasks`
- `get_social_accounts`
- `list_actions`

### Update
- `update_contact`
- `upsert_contact`

### Delete
- `delete_contact`
- `delete_tag`
- `delete_custom_field`
- `delete_opportunity`

### Workflow/Campaign
- `add_contact_to_workflow`
- `remove_contact_from_workflow`
- `add_contact_to_campaign`
- `add_contact_tags`

### Messaging
- `send_sms`
- `send_email`

### Raw
- `raw` (any GHL API endpoint)
