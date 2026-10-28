"""
Entry point for the Wiom UAF Communication Briefing Agent.

Usage:
    python main.py          # Interactive mode selector
    python main.py cli      # Launch CLI (default: Gemini)
    python main.py web      # Launch Streamlit web UI
"""

import subprocess
import sys


def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print()
        print("Wiom UAF Communication Briefing Agent")
        print("=" * 40)
        print()
        print("  1. Terminal (CLI)")
        print("  2. Web browser (Streamlit)")
        print()

        try:
            choice = input("Select mode [1/2]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)

        mode = "cli" if choice == "1" else "web" if choice == "2" else ""

    if mode == "cli":
        # Pass remaining args to cli.py
        from cli import main as cli_main
        cli_main()
    elif mode in ("web", "streamlit"):
        print("Starting Streamlit server...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    else:
        print("Invalid selection. Use: python main.py [cli|web]")
        sys.exit(1)


if __name__ == "__main__":
    main()
