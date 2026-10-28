# Wiom UAF Communication Briefing Agent

Helps stakeholders define, validate, and document UAF communication requirements before submitting implementation tasks to Linear.

## Setup

```bash
cd wiom-briefing-agent
pip install -r requirements.txt
```

### Get an API key (pick one)

**Google Gemini (free, recommended):**
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key" (just needs a Google account)
3. Set it: `export GOOGLE_API_KEY='your-key'`

**Anthropic Claude (paid):**
1. Go to https://console.anthropic.com/settings/keys
2. Create a key
3. Set it: `export ANTHROPIC_API_KEY='your-key'`

## Usage

### Mode selector
```bash
python main.py
```

### Terminal (CLI)
```bash
python main.py cli                    # uses Gemini (default)
python cli.py --provider anthropic    # uses Claude
```

### Web browser (Streamlit)
```bash
python main.py web
# or
streamlit run app.py
```

## Share with stakeholders (no setup for them)

### Option 1: Streamlit Cloud (free)
1. Push this repo to GitHub
2. Go to https://share.streamlit.io
3. Connect the repo, set main file to `app.py`
4. Add secret: `GOOGLE_API_KEY = "your-key"` (or `ANTHROPIC_API_KEY`)
5. Share the URL - stakeholders just open it and chat

### Option 2: Any server
```bash
export GOOGLE_API_KEY='your-key'
streamlit run app.py --server.port 8501
```

## How the knowledge base works

Every completed brief is saved to `knowledge/completed_briefs/`.
Every correction is saved to `knowledge/corrections/`.

On future sessions, the agent loads past briefs as context and suggests
defaults from similar communications. It always confirms with the stakeholder
before applying suggestions.

## Project structure

```
wiom-briefing-agent/
├── main.py              # Entry point (mode selector)
├── app.py               # Streamlit web UI
├── cli.py               # Terminal CLI
├── agent.py             # Core agent (Gemini + Anthropic)
├── briefing_spec.py     # System prompt and requirement schema
├── knowledge_base.py    # Knowledge storage and retrieval
├── knowledge/
│   ├── completed_briefs/
│   └── corrections/
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── requirements.txt
└── README.md
```
