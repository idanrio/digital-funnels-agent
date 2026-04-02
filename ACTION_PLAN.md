# PrimeFlow AI - Prioritized Action Plan
## What to do NOW, NEXT, and LATER

---

## NOW (This Week) - Get the Foundation Running

### Step 1: Environment Setup
```bash
# 1. Navigate to the project
cd "Primeflow ai api project/primeflow-ai"

# 2. Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your actual API keys
```

### Step 2: Test GHL API Connection
- Put your GHL API key in `.env`
- Run a simple test: query your contacts list
- Verify you can create a test contact via API
- This proves the AI -> GHL API pipeline works

### Step 3: Test Claude Agent Loop
- Start the FastAPI server
- Send a simple message via the WebSocket
- Verify Claude receives it, reasons about it, and responds
- This proves the core agent loop works

---

## NEXT (Weeks 2-3) - First Real Capability

### Step 4: GHL Browser Automation
- Set up Playwright to log into your GHL account
- Implement navigation to key modules (Contacts, Workflows, Funnels)
- Take screenshots and verify the AI can "see" the platform
- Build the first automated action: create a contact via browser

### Step 5: First End-to-End Task
Pick ONE complete task the AI should be able to do, e.g.:
> "Create a contact named 'Test User' with phone 050-1234567 and add tag 'VIP'"

This task exercises:
- Hebrew input parsing
- Deciding whether to use API or browser
- Executing the action
- Verifying the result

### Step 6: Chat Widget (Basic Version)
- Build a minimal React widget
- Hebrew RTL text input
- Connect to WebSocket backend
- Show AI responses with streaming
- File upload button (processing comes later)

---

## LATER (Weeks 4-8) - Build Out Capabilities

### Step 7: Complete GHL Module Coverage
- Implement automation for ALL GHL modules (one by one)
- Build the knowledge base as you implement each module
- Priority order: Contacts -> Workflows -> Funnels -> Pipelines -> Calendars

### Step 8: File Processing
- Implement PDF, DOCX, Excel parsing
- Connect parsed data to the agent's context
- Enable: "Upload a CSV of contacts and import them all"

### Step 9: External Integrations
- Make.com API connection
- n8n API connection
- Generic webhook handling

### Step 10: Self-Verification System
- Screenshot-based verification after every action
- API query verification (did the contact actually get created?)
- Retry logic on failure

### Step 11: Hebrew Funnel Builder
- Build funnel templates in Hebrew
- Enable: "Build me a lead generation funnel for a real estate company"
- Complete with pages, forms, workflows, email sequences

---

## What You Need to Provide

| Item | Why It's Needed | Priority |
|------|----------------|----------|
| **GHL API Key** | To make API calls to your GHL account | NOW |
| **GHL Location ID** | To target the correct sub-account | NOW |
| **Anthropic API Key** | To power the Claude AI agent | NOW |
| **GHL Login Credentials** | For browser automation (stored securely) | NEXT |
| **Make.com API Key** | For Make.com integration | LATER |
| **n8n Instance URL + Key** | For n8n integration | LATER |
| **Sample Hebrew funnel content** | To train the AI on your preferred style | LATER |

---

## Project File Structure (Created)

```
Primeflow ai api project/
├── RESEARCH_SUMMARY.md          # Technology research (done)
├── ROADMAP.md                   # Full 7-phase roadmap (done)
├── ACTION_PLAN.md               # This file - what to do now
└── primeflow-ai/
    ├── .env.example             # Environment config template
    ├── requirements.txt         # Python dependencies
    ├── server/
    │   ├── main.py              # FastAPI server entry point
    │   ├── core/
    │   │   └── agent.py         # Claude AI ReAct agent
    │   ├── api/                 # REST API endpoints
    │   ├── browser/             # Playwright automation
    │   ├── integrations/
    │   │   └── ghl.py           # GHL API client
    │   ├── processors/          # File processing pipeline
    │   └── knowledge/           # Knowledge base loader
    ├── widget/                  # React chat widget (to be built)
    ├── knowledge-base/
    │   ├── modules/             # GHL module documentation
    │   ├── api-docs/            # GHL API endpoint docs
    │   └── workflow-templates/  # Reusable workflow JSON files
    └── tests/                   # Test suite
```
