"""
Terminal (CLI) interface for the Wiom UAF Communication Briefing Agent.
Run with: python cli.py [--provider gemini|anthropic]
"""

import argparse
import os
import sys

from agent import BriefingAgent
from knowledge_base import get_brief_count, get_correction_count


def print_header(provider):
    print()
    print("=" * 64)
    print("  Wiom UAF Communication Briefing Agent")
    print("  Provider: {}".format(provider))
    print("=" * 64)
    briefs = get_brief_count()
    corrections = get_correction_count()
    if briefs > 0 or corrections > 0:
        print("  Knowledge base: {} past briefs, {} corrections".format(briefs, corrections))
    print()
    print("  Commands:")
    print("    /status   - Show brief completion progress")
    print("    /brief    - Show current brief data")
    print("    /quit     - Exit the agent")
    print()
    print("-" * 64)
    print()


def print_progress(progress):
    bar_width = 30
    filled = int(bar_width * progress["pct"] / 100)
    bar = "#" * filled + "-" * (bar_width - filled)
    print("\n  Progress: [{}] {}%".format(bar, progress["pct"]))
    print("  Complete: {}/{}".format(progress["complete"], progress["total"]))
    if progress["missing_mandatory"] > 0:
        print("  Missing mandatory: {}".format(progress["missing_mandatory"]))
    else:
        print("  All mandatory fields complete!")
    print()


def print_brief(brief):
    print("\n" + "=" * 50)
    print("  Current Brief Status")
    print("=" * 50)
    for section_key, section in brief.items():
        print("\n  {}".format(section["label"]))
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
            mandatory = "*" if field["mandatory"] else " "
            print("  {}{} {}: {}".format(status_icon, mandatory, field["label"], value))
    print()
    print("  Legend: [OK]=Complete [  ]=Missing [??]=Conditional")
    print("          [TK]=Awaiting tech [AS]=Assumption  *=Mandatory")
    print()


def main():
    parser = argparse.ArgumentParser(description="Wiom UAF Communication Briefing Agent")
    parser.add_argument(
        "--provider",
        choices=["gemini", "anthropic"],
        default="gemini",
        help="AI provider to use (default: gemini)",
    )
    args = parser.parse_args()

    # Check for API key
    if args.provider == "gemini":
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Error: No Google API key found.")
            print("Set it with: export GOOGLE_API_KEY='your-key-here'")
            print("Get a free key at: https://aistudio.google.com/apikey")
            sys.exit(1)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Error: No Anthropic API key found.")
            print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
            sys.exit(1)

    print_header(args.provider)

    agent = BriefingAgent(provider=args.provider, api_key=api_key)

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

            progress = agent.get_progress()
            if progress["complete"] > 0:
                filled = int(20 * progress["pct"] / 100)
                bar = "#" * filled + "-" * (20 - filled)
                print("  [{}] {}% complete".format(bar, progress["pct"]))
                print()

        except Exception as e:
            print("\nError: {}".format(e))
            print("Please try again.\n")


if __name__ == "__main__":
    main()
