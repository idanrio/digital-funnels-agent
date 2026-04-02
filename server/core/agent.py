"""
PrimeFlow AI Core Agent

This is the central ReAct (Reason + Act) agent loop.
It receives user requests, plans actions, executes tools,
observes results, and verifies outcomes.
"""

import anthropic
import json
import os
from typing import Any


class PrimeFlowAgent:
    """
    The main AI agent that orchestrates all operations.
    Uses Claude as the reasoning engine with a tool registry pattern.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-sonnet-4-20250514"
        self.tools = self._register_tools()
        self.conversation_history: list[dict] = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """You are PrimeFlow AI, a Super Worker assistant that operates
the GoHighLevel (GHL) platform. You communicate in Hebrew and English.

Your capabilities:
1. Navigate and operate the GHL platform via browser automation
2. Make GHL API calls to create/read/update/delete any entity
3. Build complete digital funnels (pages, forms, workflows, emails, SMS)
4. Process files (PDF, DOCX, Excel, CSV, images, video)
5. Integrate with Make.com and n8n for cross-platform automation
6. Make HTTP requests to any external API

Your workflow for every task:
1. UNDERSTAND: Parse the user's request (Hebrew or English)
2. PLAN: Break the task into specific steps
3. EXECUTE: Perform each step using the appropriate tool
4. VERIFY: Check that each action succeeded (screenshot + API query)
5. REPORT: Summarize what was done in the user's language

Rules:
- Always verify your work after completing an action
- If something fails, retry up to 2 times before reporting the error
- Ask for clarification if the request is ambiguous
- Show progress updates for long-running tasks
- Default to Hebrew for all content created in GHL
"""

    def _register_tools(self) -> list[dict]:
        """Register all available tools for the agent."""
        return [
            {
                "name": "ghl_api_call",
                "description": "Make a GoHighLevel API call. Use this for creating/reading/updating/deleting contacts, opportunities, workflows, custom fields, pipelines, and all other GHL entities.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP method"
                        },
                        "endpoint": {
                            "type": "string",
                            "description": "GHL API endpoint path (e.g., /contacts/)"
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body for POST/PUT/PATCH"
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters"
                        }
                    },
                    "required": ["method", "endpoint"]
                }
            },
            {
                "name": "browser_navigate",
                "description": "Navigate to a URL in the GHL platform or any website.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to navigate to"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_click",
                "description": "Click an element on the current page using accessibility tree selectors.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Accessibility selector (role + name) or CSS selector"
                        },
                        "description": {
                            "type": "string",
                            "description": "Human-readable description of what is being clicked"
                        }
                    },
                    "required": ["selector"]
                }
            },
            {
                "name": "browser_type",
                "description": "Type text into an input field on the current page.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "selector": {
                            "type": "string",
                            "description": "Selector for the input field"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to type"
                        }
                    },
                    "required": ["selector", "text"]
                }
            },
            {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current page for verification.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "full_page": {
                            "type": "boolean",
                            "description": "Capture full page or just viewport",
                            "default": False
                        }
                    }
                }
            },
            {
                "name": "http_request",
                "description": "Make an HTTP request to any external API (Make.com, n8n, webhooks, etc.).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                        },
                        "url": {
                            "type": "string",
                            "description": "Full URL to request"
                        },
                        "headers": {
                            "type": "object",
                            "description": "Request headers"
                        },
                        "body": {
                            "type": "object",
                            "description": "Request body"
                        }
                    },
                    "required": ["method", "url"]
                }
            },
            {
                "name": "process_file",
                "description": "Process an uploaded file (PDF, DOCX, Excel, CSV, image, video).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["extract_text", "analyze", "summarize", "extract_data"],
                            "description": "What to do with the file"
                        }
                    },
                    "required": ["file_path", "action"]
                }
            },
            {
                "name": "verify_action",
                "description": "Verify that a previous action was successful by checking the current state.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action_description": {
                            "type": "string",
                            "description": "What action to verify"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["screenshot", "api_check", "url_check"],
                            "description": "How to verify"
                        },
                        "expected": {
                            "type": "string",
                            "description": "What the expected outcome should be"
                        }
                    },
                    "required": ["action_description", "method"]
                }
            }
        ]

    async def process_message(self, user_message: str) -> dict[str, Any]:
        """
        Process a user message through the ReAct agent loop.
        Returns the agent's response and any actions taken.
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        actions_taken = []
        max_iterations = 10

        for iteration in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=self.conversation_history
            )

            # Check if the agent wants to use a tool
            if response.stop_reason == "tool_use":
                # Extract tool calls
                for block in response.content:
                    if block.type == "tool_use":
                        tool_result = await self._execute_tool(
                            block.name, block.input
                        )
                        actions_taken.append({
                            "tool": block.name,
                            "input": block.input,
                            "result": tool_result
                        })

                        # Add assistant message and tool result to history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        self.conversation_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": json.dumps(tool_result)
                            }]
                        })
            else:
                # Agent is done — extract text response
                text_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text_response += block.text

                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                return {
                    "response": text_response,
                    "actions": actions_taken,
                    "iterations": iteration + 1
                }

        return {
            "response": "Reached maximum iterations. Partial results may be available.",
            "actions": actions_taken,
            "iterations": max_iterations
        }

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool and return the result.
        This is where the actual work happens — each tool connects to a real service.
        """
        # Tool execution will be implemented per-tool in their respective modules
        # For now, return a placeholder that shows the architecture works
        handlers = {
            "ghl_api_call": self._handle_ghl_api,
            "browser_navigate": self._handle_browser_navigate,
            "browser_click": self._handle_browser_click,
            "browser_type": self._handle_browser_type,
            "browser_screenshot": self._handle_browser_screenshot,
            "http_request": self._handle_http_request,
            "process_file": self._handle_process_file,
            "verify_action": self._handle_verify_action,
        }

        handler = handlers.get(tool_name)
        if handler:
            return await handler(tool_input)

        return {"error": f"Unknown tool: {tool_name}"}

    # --- Tool handlers (stubs to be implemented) ---

    async def _handle_ghl_api(self, params: dict) -> dict:
        """Execute a GHL API call."""
        # Will be implemented in server/integrations/ghl.py
        from server.integrations.ghl import GHLClient
        client = GHLClient()
        return await client.request(
            method=params["method"],
            endpoint=params["endpoint"],
            body=params.get("body"),
            query_params=params.get("params")
        )

    async def _handle_browser_navigate(self, params: dict) -> dict:
        """Navigate browser to URL."""
        # Will be implemented in server/browser/automation.py
        return {"status": "not_implemented", "url": params["url"]}

    async def _handle_browser_click(self, params: dict) -> dict:
        """Click an element."""
        return {"status": "not_implemented", "selector": params["selector"]}

    async def _handle_browser_type(self, params: dict) -> dict:
        """Type text into field."""
        return {"status": "not_implemented"}

    async def _handle_browser_screenshot(self, params: dict) -> dict:
        """Take screenshot."""
        return {"status": "not_implemented"}

    async def _handle_http_request(self, params: dict) -> dict:
        """Make HTTP request."""
        return {"status": "not_implemented", "url": params["url"]}

    async def _handle_process_file(self, params: dict) -> dict:
        """Process a file."""
        return {"status": "not_implemented", "file": params["file_path"]}

    async def _handle_verify_action(self, params: dict) -> dict:
        """Verify an action."""
        return {"status": "not_implemented"}
