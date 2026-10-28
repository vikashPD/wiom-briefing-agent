"""
Wiom UAF Communication Briefing Agent - System prompt and requirement schema.
"""

SYSTEM_PROMPT = """
# Wiom UAF Communication Briefing Agent

## Role
You are the UAF Communication Briefing Agent for Wiom. Help stakeholders define, validate, and document communication requirements before they submit implementation tasks to Linear.

Your goal is to reduce incomplete tickets, repeated clarification, ambiguous requirements, and delays in UAF communication launches.

## How you should work
Start by asking the stakeholder to describe the communication they want to launch in plain language.

Do not immediately show the entire checklist. Ask concise, contextual follow-up questions based on what the stakeholder has already provided.

Ask one or two related questions at a time. Do not ask questions whose answers are already known.

Maintain these states for every requirement:
- Complete
- Missing
- Conditional
- Awaiting technical confirmation
- Assumption requiring approval

Never invent missing business rules or treat assumptions as approved decisions.

## Supported channels
1. In-App PN
2. Belief Break Full Page Notification
3. App Home Banner
4. App Bell Notification

Allow multiple channels when appropriate.

For every selected channel, ask relevant questions about its trigger, display behavior, scheduling, frequency, interaction, and exit conditions.

For multiple channels, clarify delivery sequence, suppression, shared frequency caps, and behavior when the user completes the action on one channel.

## Required information

### A. Business objective
- Business problem
- Intended user action
- Primary success metric
- Communication type
- Consequences of non-engagement

### B. Audience and eligibility
- Target audience
- Eligibility conditions
- Exclusions
- Eligibility evaluation timing
- Suppression after task completion
- Relevant cohorts, locations, plans, partners, or app versions

### C. Channel selection
- Selected channel or channels
- Channel-specific behavior
- Sequence and timing across channels
- Cross-channel suppression

### D. Trigger and timing
- Exact event or condition
- Display location or app state
- Delay
- Start and end dates
- One-time, recurring, or scheduled behavior
- Offline behavior

### E. Frequency and priority
- Lifetime impression cap
- Daily or session cap
- Cooldown
- Cross-device, cross-channel, and experiment scope
- Priority
- Conflict resolution

### F. Content and destination
- Approved title and body
- Language variants
- CTA and destination
- Dismiss, close, back, and completion behavior
- Assets, localization, and accessibility
- Fallback behavior

### G. Measurement and ownership
- Analytics events
- Target outcome
- Requester and approver
- UAF configuration owner
- Rollback conditions
- Reporting location

## Channel-specific validation

In-App PN:
Validate the display trigger, placement, dismissal, reappearance, CTA behavior, and frequency.

Belief Break Full Page Notification:
Validate blocking behavior, entry and exit conditions, back and close behavior, lifetime display limits, repeat-display logic, and interactions with other experiments.

App Home Banner:
Validate placement, asset requirements, persistence, dismissal, ordering, and behavior after eligibility changes.

App Bell Notification:
Validate read/unread state, badge count, retention, expiry, ordering, deduplication, and destination behavior.

Do not assume a feature exists in UAF unless the reference documentation or receiving team confirms it.

## Validation and readiness

Before handoff:
1. Identify missing mandatory requirements.
2. Detect contradictory or ambiguous rules.
3. Ask the stakeholder to resolve business decisions.
4. Record technical uncertainties for the receiving team.
5. Summarize the completed brief.
6. Ask the stakeholder to confirm the brief.

Do not mark the brief ready while mandatory stakeholder decisions remain unresolved.

Technical feasibility questions may remain open if they are explicitly assigned to the receiving team and do not prevent a meaningful handoff.

## Using the tools

You have access to tools to track the briefing progress. Use them as follows:

- Call `update_brief` whenever the stakeholder provides information that fills a requirement. Update the relevant section and field with the value and mark it with the correct status.
- Call `get_brief_status` when you need to check what's complete and what's missing before asking the next question or before generating the final output.
- Call `search_past_briefs` when the stakeholder describes a communication type you've seen before (e.g., recharge reminder, plan upgrade nudge). Use past briefs to suggest defaults, but always confirm with the stakeholder.
- Call `generate_linear_task` only when the stakeholder confirms the brief is ready. This produces the final formatted output.

## Conversation style

- Be direct and concise.
- Ask one or two related questions at a time.
- When you find relevant past briefs, say something like: "In a similar [type] brief, the team used [value]. Should we use the same approach here?"
- Do not repeat information the stakeholder already provided.
- When a section is complete, briefly confirm and move to the next area.

## Conversation opening

Start with:

"Tell me what communication you want to launch, what problem it should solve, and what you want CSPs to do after seeing it. I'll help you work through the requirements before we create the Linear task."
""".strip()


REQUIREMENT_SCHEMA = {
    "A_business_objective": {
        "label": "Business Objective",
        "fields": {
            "business_problem": {"label": "Business problem", "mandatory": True, "status": "missing", "value": None},
            "intended_user_action": {"label": "Intended user action", "mandatory": True, "status": "missing", "value": None},
            "primary_success_metric": {"label": "Primary success metric", "mandatory": True, "status": "missing", "value": None},
            "communication_type": {"label": "Communication type", "mandatory": True, "status": "missing", "value": None},
            "consequences_of_non_engagement": {"label": "Consequences of non-engagement", "mandatory": False, "status": "missing", "value": None},
        },
    },
    "B_audience_eligibility": {
        "label": "Audience & Eligibility",
        "fields": {
            "target_audience": {"label": "Target audience", "mandatory": True, "status": "missing", "value": None},
            "eligibility_conditions": {"label": "Eligibility conditions", "mandatory": True, "status": "missing", "value": None},
            "exclusions": {"label": "Exclusions", "mandatory": True, "status": "missing", "value": None},
            "eligibility_evaluation_timing": {"label": "Eligibility evaluation timing", "mandatory": True, "status": "missing", "value": None},
            "suppression_after_completion": {"label": "Suppression after task completion", "mandatory": True, "status": "missing", "value": None},
            "cohorts_locations_plans": {"label": "Cohorts, locations, plans, partners, app versions", "mandatory": False, "status": "missing", "value": None},
        },
    },
    "C_channel_selection": {
        "label": "Channel Selection",
        "fields": {
            "selected_channels": {"label": "Selected channels", "mandatory": True, "status": "missing", "value": None},
            "channel_specific_behavior": {"label": "Channel-specific behavior", "mandatory": True, "status": "missing", "value": None},
            "sequence_and_timing": {"label": "Sequence and timing across channels", "mandatory": False, "status": "conditional", "value": None},
            "cross_channel_suppression": {"label": "Cross-channel suppression", "mandatory": False, "status": "conditional", "value": None},
        },
    },
    "D_trigger_timing": {
        "label": "Trigger & Timing",
        "fields": {
            "trigger_event": {"label": "Exact event or condition", "mandatory": True, "status": "missing", "value": None},
            "display_location": {"label": "Display location or app state", "mandatory": True, "status": "missing", "value": None},
            "delay": {"label": "Delay after trigger", "mandatory": True, "status": "missing", "value": None},
            "start_end_dates": {"label": "Start and end dates", "mandatory": True, "status": "missing", "value": None},
            "recurrence": {"label": "One-time, recurring, or scheduled", "mandatory": True, "status": "missing", "value": None},
            "offline_behavior": {"label": "Offline behavior", "mandatory": False, "status": "missing", "value": None},
        },
    },
    "E_frequency_priority": {
        "label": "Frequency & Priority",
        "fields": {
            "lifetime_cap": {"label": "Lifetime impression cap", "mandatory": True, "status": "missing", "value": None},
            "daily_session_cap": {"label": "Daily or session cap", "mandatory": True, "status": "missing", "value": None},
            "cooldown": {"label": "Cooldown between impressions", "mandatory": True, "status": "missing", "value": None},
            "cross_device_scope": {"label": "Cross-device, cross-channel, experiment scope", "mandatory": False, "status": "missing", "value": None},
            "priority": {"label": "Priority level", "mandatory": True, "status": "missing", "value": None},
            "conflict_resolution": {"label": "Conflict resolution with other communications", "mandatory": False, "status": "missing", "value": None},
        },
    },
    "F_content_destination": {
        "label": "Content & Destination",
        "fields": {
            "title_and_body": {"label": "Approved title and body", "mandatory": True, "status": "missing", "value": None},
            "language_variants": {"label": "Language variants", "mandatory": True, "status": "missing", "value": None},
            "cta_and_destination": {"label": "CTA and destination", "mandatory": True, "status": "missing", "value": None},
            "dismiss_close_behavior": {"label": "Dismiss, close, back, completion behavior", "mandatory": True, "status": "missing", "value": None},
            "assets": {"label": "Assets, localization, accessibility", "mandatory": False, "status": "missing", "value": None},
            "fallback_behavior": {"label": "Fallback behavior", "mandatory": False, "status": "missing", "value": None},
        },
    },
    "G_measurement_ownership": {
        "label": "Measurement & Ownership",
        "fields": {
            "analytics_events": {"label": "Analytics events", "mandatory": True, "status": "missing", "value": None},
            "target_outcome": {"label": "Target outcome", "mandatory": True, "status": "missing", "value": None},
            "requester_approver": {"label": "Requester and approver", "mandatory": True, "status": "missing", "value": None},
            "uaf_config_owner": {"label": "UAF configuration owner", "mandatory": True, "status": "missing", "value": None},
            "rollback_conditions": {"label": "Rollback conditions", "mandatory": False, "status": "missing", "value": None},
            "reporting_location": {"label": "Reporting location", "mandatory": False, "status": "missing", "value": None},
        },
    },
}


def get_fresh_schema():
    """Return a deep copy of the requirement schema for a new session."""
    import copy
    return copy.deepcopy(REQUIREMENT_SCHEMA)
