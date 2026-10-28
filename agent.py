"""
Core agent logic for the Wiom UAF Communication Briefing Agent.
Shared between CLI and Streamlit interfaces.
Supports Google Gemini (free, default) and Anthropic Claude.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from briefing_spec import SYSTEM_PROMPT, get_fresh_schema
from knowledge_base import (
    get_knowledge_context,
    save_brief,
    save_correction,
    search_briefs,
)

# --- Tool definitions (provider-agnostic) ---

TOOL_DEFS = [
    {
        "name": "update_brief",
        "description": (
            "Update one or more fields in the briefing document. "
            "Call this whenever the stakeholder provides information that fills a requirement."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "updates": {
                    "type": "array",
                    "description": "List of field updates to apply.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "section": {
                                "type": "string",
                                "description": "Section key, e.g. 'A_business_objective'",
                            },
                            "field": {
                                "type": "string",
                                "description": "Field key within the section, e.g. 'business_problem'",
                            },
                            "value": {
                                "type": "string",
                                "description": "The value provided by the stakeholder.",
                            },
                            "status": {
                                "type": "string",
                                "enum": [
                                    "complete",
                                    "missing",
                                    "conditional",
                                    "awaiting_technical_confirmation",
                                    "assumption_requiring_approval",
                                ],
                                "description": "Status of this requirement.",
                            },
                        },
                        "required": ["section", "field", "value", "status"],
                    },
                }
            },
            "required": ["updates"],
        },
    },
    {
        "name": "get_brief_status",
        "description": (
            "Get the current status of all requirements in the brief. "
            "Use this to check what's complete, missing, or needs attention."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_past_briefs",
        "description": (
            "Search the knowledge base for similar past briefs. "
            "Use this when the stakeholder describes a communication type you might have seen before."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - communication type, channel, or business problem keywords.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_linear_task",
        "description": (
            "Generate the final Linear-ready task document from the completed brief. "
            "Only call this after the stakeholder confirms the brief is ready."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Clear title for the Linear task.",
                }
            },
            "required": ["title"],
        },
    },
    {
        "name": "save_completed_brief",
        "description": (
            "Save the completed brief to the knowledge base so future sessions can learn from it. "
            "Call this after generating the Linear task and getting stakeholder confirmation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the brief.",
                }
            },
            "required": ["title"],
        },
    },
    {
        "name": "save_feedback",
        "description": (
            "Save stakeholder feedback or corrections about a brief. "
            "This helps the agent learn and improve over time."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "brief_title": {
                    "type": "string",
                    "description": "Title of the brief this feedback is about.",
                },
                "feedback": {
                    "type": "string",
                    "description": "The correction or feedback from the stakeholder.",
                },
            },
            "required": ["brief_title", "feedback"],
        },
    },
]


def _tools_for_anthropic():
    """Convert tool defs to Anthropic format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in TOOL_DEFS
    ]


def _tools_for_gemini():
    """Convert tool defs to Gemini function declarations."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for t in TOOL_DEFS
    ]


class BriefingAgent:
    """
    Core agent that manages the briefing conversation.
    Interface-agnostic: works with both CLI and Streamlit.
    Supports 'gemini' (default, free) and 'anthropic' providers.
    """

    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        self.provider = provider
        self.brief = get_fresh_schema()
        self.brief_title = None  # type: Optional[str]

        if provider == "gemini":
            import google.generativeai as genai

            key = api_key or os.environ.get("GOOGLE_API_KEY")
            if not key:
                raise ValueError("Google API key is required. Set GOOGLE_API_KEY or pass api_key.")
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel(
                "gemini-2.0-flash",
                system_instruction=self._build_system_prompt(),
                tools=[{"function_declarations": _tools_for_gemini()}],
            )
            self.chat = self.model.start_chat()

        elif provider == "anthropic":
            from anthropic import Anthropic

            self.client = Anthropic(api_key=api_key)
            self.messages = []  # type: list

        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'anthropic'.")

    def _build_system_prompt(self) -> str:
        """Build system prompt with knowledge context."""
        knowledge = get_knowledge_context()
        if knowledge:
            return "{}\n\n# Knowledge from past briefs\n\n{}".format(SYSTEM_PROMPT, knowledge)
        return SYSTEM_PROMPT

    # --- Tool execution (provider-agnostic) ---

    def _handle_tool_call(self, tool_name, tool_input):
        """Execute a tool call and return the result as a string."""
        if tool_name == "update_brief":
            return self._tool_update_brief(tool_input)
        elif tool_name == "get_brief_status":
            return self._tool_get_brief_status()
        elif tool_name == "search_past_briefs":
            return self._tool_search_past_briefs(tool_input)
        elif tool_name == "generate_linear_task":
            return self._tool_generate_linear_task(tool_input)
        elif tool_name == "save_completed_brief":
            return self._tool_save_completed_brief(tool_input)
        elif tool_name == "save_feedback":
            return self._tool_save_feedback(tool_input)
        else:
            return json.dumps({"error": "Unknown tool: {}".format(tool_name)})

    def _tool_update_brief(self, tool_input):
        updates = tool_input.get("updates", [])
        applied = []
        errors = []
        for update in updates:
            section = update["section"]
            field = update["field"]
            value = update["value"]
            status = update["status"]
            if section in self.brief and field in self.brief[section]["fields"]:
                self.brief[section]["fields"][field]["value"] = value
                self.brief[section]["fields"][field]["status"] = status
                applied.append("{}.{} -> {}".format(section, field, status))
            else:
                errors.append("Unknown field: {}.{}".format(section, field))
        result = {"applied": applied}
        if errors:
            result["errors"] = errors
        return json.dumps(result)

    def _tool_get_brief_status(self):
        status = {}
        total = 0
        complete = 0
        missing_mandatory = []
        for section_key, section in self.brief.items():
            section_status = {}
            for field_key, field in section["fields"].items():
                section_status[field_key] = {
                    "label": field["label"],
                    "status": field["status"],
                    "mandatory": field["mandatory"],
                    "has_value": field["value"] is not None,
                }
                total += 1
                if field["status"] == "complete":
                    complete += 1
                elif field["mandatory"] and field["status"] == "missing":
                    missing_mandatory.append("{}: {}".format(section["label"], field["label"]))
            status[section_key] = {"label": section["label"], "fields": section_status}
        return json.dumps({
            "sections": status,
            "summary": {
                "total_fields": total,
                "complete": complete,
                "progress_pct": round(complete / total * 100) if total > 0 else 0,
                "missing_mandatory": missing_mandatory,
                "ready_for_handoff": len(missing_mandatory) == 0,
            },
        })

    def _tool_search_past_briefs(self, tool_input):
        query = tool_input.get("query", "")
        results = search_briefs(query)
        if not results:
            return json.dumps({"results": [], "message": "No matching past briefs found."})
        return json.dumps({"results": results, "count": len(results)})

    def _tool_generate_linear_task(self, tool_input):
        title = tool_input.get("title", "UAF Communication Task")
        self.brief_title = title
        task = self._format_linear_task(title)
        return json.dumps({"task_markdown": task, "title": title})

    def _tool_save_completed_brief(self, tool_input):
        title = tool_input.get("title", self.brief_title or "Untitled")
        filepath = save_brief(self.brief, title)
        return json.dumps({"saved": True, "path": filepath})

    def _tool_save_feedback(self, tool_input):
        brief_title = tool_input.get("brief_title", "")
        feedback = tool_input.get("feedback", "")
        filepath = save_correction(brief_title, feedback)
        return json.dumps({"saved": True, "path": filepath})

    # --- Provider-specific send logic ---

    def send_message(self, user_message):
        """
        Send a user message and get the agent's response.
        Returns (response_text, tool_calls_made).
        """
        if self.provider == "gemini":
            return self._send_gemini(user_message)
        else:
            return self._send_anthropic(user_message)

    def _send_gemini(self, user_message):
        """Gemini conversation with tool-use loop."""
        import google.generativeai as genai

        tool_calls_log = []
        response = self.chat.send_message(user_message)

        while True:
            # Check for function calls in response
            function_calls = []
            for part in response.candidates[0].content.parts:
                if part.function_call and part.function_call.name:
                    function_calls.append(part)

            if not function_calls:
                break

            # Handle each function call
            response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                tool_input = dict(fc.args) if fc.args else {}
                result_str = self._handle_tool_call(fc.name, tool_input)
                tool_calls_log.append({
                    "tool": fc.name,
                    "input": tool_input,
                    "result": result_str,
                })
                response_parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": json.loads(result_str)},
                        )
                    )
                )

            response = self.chat.send_message(response_parts)

        # Extract text from final response
        text_parts = []
        for part in response.candidates[0].content.parts:
            if part.text:
                text_parts.append(part.text)

        return "\n".join(text_parts), tool_calls_log

    def _send_anthropic(self, user_message):
        """Anthropic conversation with tool-use loop."""
        self.messages.append({"role": "user", "content": user_message})
        tool_calls_log = []

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=self._build_system_prompt(),
                tools=_tools_for_anthropic(),
                messages=self.messages,
            )

            assistant_content = response.content
            self.messages.append({"role": "assistant", "content": assistant_content})

            tool_uses = [b for b in assistant_content if b.type == "tool_use"]
            if not tool_uses:
                text_parts = [b.text for b in assistant_content if b.type == "text"]
                return "\n".join(text_parts), tool_calls_log

            tool_results = []
            for tool_use in tool_uses:
                result = self._handle_tool_call(tool_use.name, tool_use.input)
                tool_calls_log.append({
                    "tool": tool_use.name,
                    "input": tool_use.input,
                    "result": result,
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })

            self.messages.append({"role": "user", "content": tool_results})

    # --- Linear task formatting ---

    def _format_linear_task(self, title):
        lines = ["# {}".format(title), ""]

        section_map = [
            ("A_business_objective", "Business Context & Objective"),
            ("B_audience_eligibility", "Audience & Eligibility"),
            ("C_channel_selection", "Channel Selection & Configuration"),
            ("D_trigger_timing", "Trigger & Scheduling"),
            ("E_frequency_priority", "Frequency & Priority Rules"),
            ("F_content_destination", "Content & Destination"),
            ("G_measurement_ownership", "Analytics & Success Criteria"),
        ]

        for key, heading in section_map:
            lines.append("## {}".format(heading))
            for field in self.brief[key]["fields"].values():
                val = field["value"] or "[{}]".format(field["status"].upper())
                lines.append("- **{}:** {}".format(field["label"], val))
            lines.append("")

        lines.append("## Acceptance Criteria")
        lines.append(self._generate_acceptance_criteria())
        lines.append("")

        lines.append("## QA Scenarios")
        lines.append(self._generate_qa_scenarios())
        lines.append("")

        open_questions = self._collect_open_items()
        if open_questions:
            lines.append("## Open Questions & Technical Dependencies")
            for q in open_questions:
                lines.append("- {}".format(q))
            lines.append("")

        return "\n".join(lines)

    def _generate_acceptance_criteria(self):
        criteria = []
        b = self.brief

        checks = [
            ("D_trigger_timing", "trigger_event", "Communication is triggered when"),
            ("B_audience_eligibility", "target_audience", "Only shown to"),
            ("B_audience_eligibility", "suppression_after_completion", "Suppressed after completion"),
            ("E_frequency_priority", "lifetime_cap", "Lifetime impression cap enforced"),
            ("E_frequency_priority", "daily_session_cap", "Daily/session cap enforced"),
            ("F_content_destination", "cta_and_destination", "CTA navigates to"),
            ("G_measurement_ownership", "analytics_events", "Analytics events fire correctly"),
            ("C_channel_selection", "selected_channels", "Displayed on correct channels"),
        ]

        for section, field, label in checks:
            val = b[section]["fields"][field]["value"]
            if val:
                criteria.append("- [ ] {}: {}".format(label, val))

        return "\n".join(criteria) if criteria else "- [ ] [To be generated from completed brief]"

    def _generate_qa_scenarios(self):
        scenarios = [
            "- [ ] Eligible user sees the communication on first trigger",
            "- [ ] Ineligible user never sees the communication",
            "- [ ] Communication is suppressed after user completes the action",
        ]

        lifetime = self.brief["E_frequency_priority"]["fields"]["lifetime_cap"]["value"]
        if lifetime:
            scenarios.append("- [ ] Communication stops after lifetime cap ({})".format(lifetime))

        cooldown = self.brief["E_frequency_priority"]["fields"]["cooldown"]["value"]
        if cooldown:
            scenarios.append("- [ ] Cooldown of {} is respected between impressions".format(cooldown))

        channels = self.brief["C_channel_selection"]["fields"]["selected_channels"]["value"]
        if channels and "," in str(channels):
            scenarios.append("- [ ] Cross-channel suppression works correctly")
            scenarios.append("- [ ] Channel sequence/timing is respected")

        scenarios.append("- [ ] Dismiss/close behavior works as specified")
        scenarios.append("- [ ] All analytics events fire with correct payloads")
        scenarios.append("- [ ] Communication renders correctly in all supported languages")
        return "\n".join(scenarios)

    def _collect_open_items(self):
        items = []
        for section in self.brief.values():
            for field in section["fields"].values():
                if field["status"] == "awaiting_technical_confirmation":
                    items.append("[TECH] {}: {}".format(field["label"], field["value"] or "Needs confirmation"))
                elif field["status"] == "assumption_requiring_approval":
                    items.append("[ASSUMPTION] {}: {}".format(field["label"], field["value"] or "Needs approval"))
                elif field["status"] == "conditional" and field["value"]:
                    items.append("[CONDITIONAL] {}: {}".format(field["label"], field["value"]))
        return items

    def get_progress(self):
        """Get a summary of brief completion progress."""
        total = 0
        complete = 0
        missing_mandatory = 0
        for section in self.brief.values():
            for field in section["fields"].values():
                total += 1
                if field["status"] == "complete":
                    complete += 1
                elif field["mandatory"] and field["status"] == "missing":
                    missing_mandatory += 1
        return {
            "total": total,
            "complete": complete,
            "missing_mandatory": missing_mandatory,
            "pct": round(complete / total * 100) if total > 0 else 0,
        }
