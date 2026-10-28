"""
Streamlit web interface for the Wiom UAF Communication Briefing Agent.
Run with: streamlit run app.py
"""

import os

import streamlit as st
from agent import BriefingAgent
from knowledge_base import get_brief_count, get_correction_count


def get_configured_key(provider):
    """
    Get API key from secrets or env for the given provider.
    Returns the key or None.
    """
    if provider == "gemini":
        env_keys = ["GOOGLE_API_KEY", "GEMINI_API_KEY"]
    else:
        env_keys = ["ANTHROPIC_API_KEY"]

    # Check Streamlit secrets first
    try:
        for k in env_keys:
            val = st.secrets.get(k)
            if val:
                return val
    except Exception:
        pass

    # Check environment
    for k in env_keys:
        val = os.environ.get(k)
        if val:
            return val

    return None


def init_session():
    """Initialize session state on first load."""
    if "agent" not in st.session_state:
        st.session_state.agent = None
        st.session_state.chat_history = []
        st.session_state.initialized = False
        st.session_state.started = False


def try_auto_start(provider):
    """Auto-start if API key is available from secrets/env."""
    key = get_configured_key(provider)
    if key:
        try:
            st.session_state.agent = BriefingAgent(provider=provider, api_key=key)
            st.session_state.started = True
            return True
        except Exception:
            return False
    return False


def render_sidebar():
    """Render the sidebar with progress and controls."""
    with st.sidebar:
        st.title("Briefing Progress")

        if st.session_state.agent:
            progress = st.session_state.agent.get_progress()
            st.progress(progress["pct"] / 100)
            st.metric("Complete", "{}/{}".format(progress["complete"], progress["total"]))
            st.metric("Missing Mandatory", progress["missing_mandatory"])

            if progress["missing_mandatory"] == 0:
                st.success("All mandatory fields complete!")
            else:
                st.warning("{} mandatory fields remaining".format(progress["missing_mandatory"]))

            st.divider()

            st.subheader("Sections")
            for section_key, section in st.session_state.agent.brief.items():
                section_complete = sum(
                    1 for f in section["fields"].values() if f["status"] == "complete"
                )
                section_total = len(section["fields"])
                icon = "done" if section_complete == section_total else "pending"
                st.text("[{}] {} ({}/{})".format(icon, section["label"], section_complete, section_total))

        st.divider()

        st.subheader("Knowledge Base")
        briefs = get_brief_count()
        corrections = get_correction_count()
        st.text("Past briefs: {}".format(briefs))
        st.text("Corrections: {}".format(corrections))

        st.divider()

        if st.button("Start New Briefing", use_container_width=True):
            provider = st.session_state.agent.provider if st.session_state.agent else "gemini"
            key = get_configured_key(provider)
            st.session_state.agent = BriefingAgent(provider=provider, api_key=key) if key else None
            st.session_state.chat_history = []
            st.session_state.initialized = False
            st.rerun()


def render_setup():
    """Render the setup screen for API key entry."""
    st.title("Wiom UAF Communication Briefing Agent")
    st.markdown(
        "Help stakeholders define and validate communication requirements "
        "before submitting to Linear."
    )
    st.divider()

    provider = st.radio(
        "Choose AI provider",
        ["gemini", "anthropic"],
        format_func=lambda x: "Google Gemini (free)" if x == "gemini" else "Anthropic Claude",
        index=0,
    )

    if provider == "gemini":
        st.info("Get a free API key from https://aistudio.google.com/apikey (just needs a Google account)")
        api_key = st.text_input(
            "Google API Key",
            type="password",
            placeholder="AIza...",
        )
    else:
        st.info("Get an API key from https://console.anthropic.com/settings/keys")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
        )

    if st.button("Start Briefing", disabled=not api_key, use_container_width=True):
        try:
            agent = BriefingAgent(provider=provider, api_key=api_key)
            st.session_state.agent = agent
            st.session_state.started = True
            st.rerun()
        except Exception as e:
            st.error("Failed to initialize: {}".format(e))


def render_chat():
    """Render the chat interface."""
    st.title("Wiom UAF Communication Briefing Agent")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not st.session_state.initialized:
        st.session_state.initialized = True
        with st.chat_message("assistant"):
            with st.spinner("Starting briefing session..."):
                response, _ = st.session_state.agent.send_message(
                    "Start the conversation with your opening message. This is a new briefing session."
                )
                st.markdown(response)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response}
                )

    if user_input := st.chat_input("Describe your communication requirement..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response, tool_calls = st.session_state.agent.send_message(user_input)
                    st.markdown(response)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    st.error("Error: {}".format(e))

        st.rerun()


def main():
    st.set_page_config(
        page_title="Wiom UAF Briefing Agent",
        layout="wide",
    )

    init_session()

    if st.session_state.started and st.session_state.agent:
        render_sidebar()
        render_chat()
    else:
        # Try auto-start from server secrets/env
        for provider in ["gemini", "anthropic"]:
            if try_auto_start(provider):
                st.rerun()
                return

        # No key found anywhere - show setup screen
        render_setup()


if __name__ == "__main__":
    main()
