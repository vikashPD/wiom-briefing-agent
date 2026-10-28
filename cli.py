"""
Terminal (CLI) interface for the Wiom UAF Communication Briefing Agent.
Run with: python cli.py
"""

import os
import sys

from agent import BriefingAgent
from knowledge_base import get_brief_count, get_correction_count


def print_header():
    print()
    print("=" * 64)
    print("  Wiom UAF Communication Briefing Agent")
    print("=" * 64)
    briefs = get_brief_count()
    corrections = get_correction_count()
    if briefs > 0 or corrections > 0:
        print(f"  Knowledge base: {briefs} past briefs, {corrections} corrections")
    print()
    print("  Commands:")
    print("    /status   - Show brief completion progress")
    print("    /brief    - Show current brief data")
    print("    /quit     - Exit the agent")
    print()
    print("-" * 64)
    print()


def print_progress(progress: dict):
    bar_width = 30
    filled = int(bar_width * progress["pct"] / 100)
    bar = "#" * filled + "-" * (bar_width - filled)
    print(f"\n  Progress: [{bar}] {progress['pct']}%")
    print(f"  Complete: {progress['complete']}/{progress['total']}")
    if progress["missing_mandatory"] > 0:
        print(f"  Missing mandatory: {progress['missing_mandatory']}")
    else:
        print("  All mandatory fields complete!")
    print()


def print_brief(brief: dict):
    print("\n" + "=" * 50)
    print("  Current Brief Status")
    print("=" * 50)
    for section_key, section in brief.items():
        print(f"\n  {section['label']}")
        print("  " + "-" * 40)
        for field in section["fields"].values():
            status_icon = {
                "complete": "[OK]",
                "missing": "[  ]",
                "conditional": "[??]",
                "awaiting_technical_confirmation": "[TK]",
                "assumption_requiring_approval": "[AS]",
            }.get(field["status"], "[??]")

            value = field["value"] or ""
            if len(value) > 50:
                value = value[:47] + "..."
            label = field["label"]
            mandatory = "*" if field["mandatory"] else " "
            print(f"  {status_icon}{mandatory} {label}: {value}")
    print()
    print("  Legend: [OK]=Complete [  ]=Missing [??]=Conditional")
    print("          [TK]=Awaiting tech [AS]=Assumption  *=Mandatory")
    print()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    print_header()

    agent = BriefingAgent(api_key=api_key)

    # Get opening message
    print("Agent: ", end="", flush=True)
    response, _ = agent.send_message(
        "Start the conversation with your opening message. This is a new briefing session."
    )
    print(response)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() == "/quit":
            print("\nSession ended.")
            break
        elif user_input.lower() == "/status":
            print_progress(agent.get_progress())
            continue
        elif user_input.lower() == "/brief":
            print_brief(agent.brief)
            continue

        print("\nAgent: ", end="", flush=True)
        try:
            response, tool_calls = agent.send_message(user_input)
            print(response)
            print()

            # Show progress after each exchange
            progress = agent.get_progress()
            if progress["complete"] > 0:
                filled = int(20 * progress["pct"] / 100)
                bar = "#" * filled + "-" * (20 - filled)
                print(f"  [{bar}] {progress['pct']}% complete")
                print()

        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.\n")


if __name__ == "__main__":
    main()
