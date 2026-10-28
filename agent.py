"""
Core agent logic for the Wiom UAF Communication Briefing Agent.
Shared between CLI and Streamlit interfaces.
"""

from __future__ import annotations

import json
from typing import Optional

from anthropic import Anthropic
from briefing_spec import SYSTEM_PROMPT, get_fresh_schema
from knowledge_base import (
    get_knowledge_context,
    save_brief,
    save_correction,
    search_briefs,
)

# --- Tool definitions for Claude ---

TOOLS = [
    {
        "name": "update_brief",
        "description": (
            "Update one or more fields in the briefing document. "
            "Call this whenever the stakeholder provides information that fills a requirement."
        ),
        "input_schema": {
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
        "input_schema": {
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
        "input_schema": {
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
        "input_schema": {
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
        "input_schema": {
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
        "input_schema": {
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


class BriefingAgent:
    """
    Core agent that manages the briefing conversation.
    Interface-agnostic: works with both CLI and Streamlit.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.brief = get_fresh_schema()
        self.messages: list[dict] = []
        self.brief_title: Optional[str] = None

    def _build_system_prompt(self) -> str:
        """Build system prompt with knowledge context."""
        knowledge = get_knowledge_context()
        if knowledge:
            return f"{SYSTEM_PROMPT}\n\n# Knowledge from past briefs\n\n{knowledge}"
        return SYSTEM_PROMPT

    def _handle_tool_call(self, tool_name: str, tool_input: dict) -> str:
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
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _tool_update_brief(self, tool_input: dict) -> str:
        """Update fields in the brief."""
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
                applied.append(f"{section}.{field} -> {status}")
            else:
                errors.append(f"Unknown field: {section}.{field}")

        result = {"applied": applied}
        if errors:
            result["errors"] = errors
        return json.dumps(result)

    def _tool_get_brief_status(self) -> str:
        """Get current brief status summary."""
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
                    missing_mandatory.append(f"{section['label']}: {field['label']}")

            status[section_key] = {
                "label": section["label"],
                "fields": section_status,
            }

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

    def _tool_search_past_briefs(self, tool_input: dict) -> str:
        """Search past briefs for reference."""
        query = tool_input.get("query", "")
        results = search_briefs(query)
        if not results:
            return json.dumps({"results": [], "message": "No matching past briefs found."})
        return json.dumps({"results": results, "count": len(results)})

    def _tool_generate_linear_task(self, tool_input: dict) -> str:
        """Generate the final Linear-ready Markdown task."""
        title = tool_input.get("title", "UAF Communication Task")
        self.brief_title = title
        task = self._format_linear_task(title)
        return json.dumps({"task_markdown": task, "title": title})

    def _tool_save_completed_brief(self, tool_input: dict) -> str:
        """Save completed brief to knowledge base."""
        title = tool_input.get("title", self.brief_title or "Untitled")
        filepath = save_brief(self.brief, title)
        return json.dumps({"saved": True, "path": filepath})

    def _tool_save_feedback(self, tool_input: dict) -> str:
        """Save stakeholder feedback."""
        brief_title = tool_input.get("brief_title", "")
        feedback = tool_input.get("feedback", "")
        filepath = save_correction(brief_title, feedback)
        return json.dumps({"saved": True, "path": filepath})

    def _format_linear_task(self, title: str) -> str:
        """Format the brief as a Linear-ready Markdown task."""
        lines = [f"# {title}", ""]

        # Business context
        lines.append("## Business Context & Objective")
        biz = self.brief["A_business_objective"]["fields"]
        for field in biz.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Audience
        lines.append("## Audience & Eligibility")
        aud = self.brief["B_audience_eligibility"]["fields"]
        for field in aud.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Channels
        lines.append("## Channel Selection & Configuration")
        ch = self.brief["C_channel_selection"]["fields"]
        for field in ch.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Trigger
        lines.append("## Trigger & Scheduling")
        tr = self.brief["D_trigger_timing"]["fields"]
        for field in tr.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Frequency
        lines.append("## Frequency & Priority Rules")
        freq = self.brief["E_frequency_priority"]["fields"]
        for field in freq.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Content
        lines.append("## Content & Destination")
        cont = self.brief["F_content_destination"]["fields"]
        for field in cont.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Measurement
        lines.append("## Analytics & Success Criteria")
        meas = self.brief["G_measurement_ownership"]["fields"]
        for field in meas.values():
            val = field["value"] or f"[{field['status'].upper()}]"
            lines.append(f"- **{field['label']}:** {val}")
        lines.append("")

        # Acceptance criteria
        lines.append("## Acceptance Criteria")
        lines.append(self._generate_acceptance_criteria())
        lines.append("")

        # QA scenarios
        lines.append("## QA Scenarios")
        lines.append(self._generate_qa_scenarios())
        lines.append("")

        # Open questions
        open_questions = self._collect_open_items()
        if open_questions:
            lines.append("## Open Questions & Technical Dependencies")
            for q in open_questions:
                lines.append(f"- {q}")
            lines.append("")

        return "\n".join(lines)

    def _generate_acceptance_criteria(self) -> str:
        """Generate acceptance criteria from the brief."""
        criteria = []
        fields = self.brief

        # Trigger
        trigger = fields["D_trigger_timing"]["fields"]["trigger_event"]["value"]
        if trigger:
            criteria.append(f"- [ ] Communication is triggered when: {trigger}")

        # Audience
        audience = fields["B_audience_eligibility"]["fields"]["target_audience"]["value"]
        if audience:
            criteria.append(f"- [ ] Only shown to: {audience}")

        # Suppression
        suppression = fields["B_audience_eligibility"]["fields"]["suppression_after_completion"]["value"]
        if suppression:
            criteria.append(f"- [ ] Suppressed after completion: {suppression}")

        # Frequency
        lifetime = fields["E_frequency_priority"]["fields"]["lifetime_cap"]["value"]
        if lifetime:
            criteria.append(f"- [ ] Lifetime impression cap enforced: {lifetime}")

        daily = fields["E_frequency_priority"]["fields"]["daily_session_cap"]["value"]
        if daily:
            criteria.append(f"- [ ] Daily/session cap enforced: {daily}")

        # CTA
        cta = fields["F_content_destination"]["fields"]["cta_and_destination"]["value"]
        if cta:
            criteria.append(f"- [ ] CTA navigates to: {cta}")

        # Analytics
        events = fields["G_measurement_ownership"]["fields"]["analytics_events"]["value"]
        if events:
            criteria.append(f"- [ ] Analytics events fire correctly: {events}")

        # Channels
        channels = fields["C_channel_selection"]["fields"]["selected_channels"]["value"]
        if channels:
            criteria.append(f"- [ ] Displayed on correct channels: {channels}")

        return "\n".join(criteria) if criteria else "- [ ] [To be generated from completed brief]"

    def _generate_qa_scenarios(self) -> str:
        """Generate QA test scenarios from the brief."""
        scenarios = [
            "- [ ] Eligible user sees the communication on first trigger",
            "- [ ] Ineligible user never sees the communication",
            "- [ ] Communication is suppressed after user completes the action",
        ]

        lifetime = self.brief["E_frequency_priority"]["fields"]["lifetime_cap"]["value"]
        if lifetime:
            scenarios.append(f"- [ ] Communication stops after lifetime cap ({lifetime})")

        cooldown = self.brief["E_frequency_priority"]["fields"]["cooldown"]["value"]
        if cooldown:
            scenarios.append(f"- [ ] Cooldown of {cooldown} is respected between impressions")

        channels = self.brief["C_channel_selection"]["fields"]["selected_channels"]["value"]
        if channels and "," in str(channels):
            scenarios.append("- [ ] Cross-channel suppression works correctly")
            scenarios.append("- [ ] Channel sequence/timing is respected")

        scenarios.append("- [ ] Dismiss/close behavior works as specified")
        scenarios.append("- [ ] All analytics events fire with correct payloads")
        scenarios.append("- [ ] Communication renders correctly in all supported languages")

        return "\n".join(scenarios)

    def _collect_open_items(self) -> list[str]:
        """Collect all non-complete, non-missing items that need attention."""
        items = []
        for section in self.brief.values():
            for field in section["fields"].values():
                if field["status"] == "awaiting_technical_confirmation":
                    items.append(f"[TECH] {field['label']}: {field['value'] or 'Needs confirmation'}")
                elif field["status"] == "assumption_requiring_approval":
                    items.append(f"[ASSUMPTION] {field['label']}: {field['value'] or 'Needs approval'}")
                elif field["status"] == "conditional":
                    if field["value"]:
                        items.append(f"[CONDITIONAL] {field['label']}: {field['value']}")
        return items

    def send_message(self, user_message: str) -> tuple[str, list[dict]]:
        """
        Send a user message and get the agent's response.
        Returns (response_text, tool_calls_made).
        Handles the tool-use loop internally.
        """
        self.messages.append({"role": "user", "content": user_message})

        tool_calls_log = []

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=self._build_system_prompt(),
                tools=TOOLS,
                messages=self.messages,
            )

            # Collect assistant content
            assistant_content = response.content
            self.messages.append({"role": "assistant", "content": assistant_content})

            # Check if there are tool uses
            tool_uses = [block for block in assistant_content if block.type == "tool_use"]

            if not tool_uses:
                # No tool calls - extract text and return
                text_parts = [block.text for block in assistant_content if block.type == "text"]
                return "\n".join(text_parts), tool_calls_log

            # Handle tool calls
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
            # Loop continues to get the next response after tool results

    def get_progress(self) -> dict:
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
