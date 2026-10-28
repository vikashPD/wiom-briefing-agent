# Wiom UAF Communication Briefing Agent

Helps stakeholders define, validate, and document UAF communication requirements before submitting implementation tasks to Linear.

## Setup

```bash
cd wiom-briefing-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY='your-key-here'
```

## Usage

### Option 1: Mode selector
```bash
python main.py
```
Prompts you to choose between terminal and web.

### Option 2: Terminal (CLI) directly
```bash
python main.py cli
# or
python cli.py
```

CLI commands during a session:
- `/status` - Show brief completion progress
- `/brief` - Show all current brief data
- `/quit` - Exit

### Option 3: Web browser (Streamlit) directly
```bash
python main.py web
# or
streamlit run app.py
```

Opens a chat UI in your browser with a sidebar showing real-time progress.

## Sharing with stakeholders

**For web access (recommended):**

Deploy to Streamlit Cloud:
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect the repo and set `ANTHROPIC_API_KEY` as a secret
4. Share the URL with stakeholders — they just open the link and chat

Or deploy anywhere that runs Python (Heroku, Railway, a VM).

**For terminal access:**
Stakeholders need Python 3.10+, the dependencies, and the API key.

## Knowledge base

The agent learns from every completed brief:

- `knowledge/completed_briefs/` - Past briefs saved as JSON
- `knowledge/corrections/` - Stakeholder feedback and corrections

Past briefs are used as reference context in future sessions. The agent suggests defaults from similar past communications but always confirms with the stakeholder.

## Project structure

```
wiom-briefing-agent/
├── main.py              # Entry point (mode selector)
├── app.py               # Streamlit web UI
├── cli.py               # Terminal CLI
├── agent.py             # Core agent logic (shared)
├── briefing_spec.py     # System prompt and requirement schema
├── knowledge_base.py    # Knowledge storage and retrieval
├── knowledge/
│   ├── completed_briefs/
│   └── corrections/
├── requirements.txt
└── README.md
```
