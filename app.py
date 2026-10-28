"""
Streamlit web interface for the Wiom UAF Communication Briefing Agent.
Run with: streamlit run app.py
"""

import os

import streamlit as st
from agent import BriefingAgent
from knowledge_base import get_brief_count, get_correction_count


def get_api_key():
    """
    Get API key from available sources, in order:
    1. Streamlit secrets (for cloud deployment - stakeholders never see this)
    2. Environment variable (for local/server deployment)
    3. None (will show input prompt as fallback)
    """
    # Streamlit Cloud secrets
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
        if key:
            return key
    except Exception:
        pass

    # Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    return None


def init_session():
    """Initialize session state on first load."""
    if "agent" not in st.session_state:
        st.session_state.agent = None
        st.session_state.chat_history = []
        st.session_state.initialized = False
        st.session_state.api_key_set = False


def try_auto_start():
    """Auto-start if API key is available from secrets or env. No prompt needed."""
    if st.session_state.api_key_set:
        return True

    api_key = get_api_key()
    if api_key:
        try:
            st.session_state.agent = BriefingAgent(api_key=api_key)
            st.session_state.api_key_set = True
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
            st.metric("Complete", f"{progress['complete']}/{progress['total']}")
            st.metric("Missing Mandatory", progress["missing_mandatory"])

            if progress["missing_mandatory"] == 0:
                st.success("All mandatory fields complete!")
            else:
                st.warning(f"{progress['missing_mandatory']} mandatory fields remaining")

            st.divider()

            # Section-by-section breakdown
            st.subheader("Sections")
            for section_key, section in st.session_state.agent.brief.items():
                section_complete = sum(
                    1 for f in section["fields"].values() if f["status"] == "complete"
                )
                section_total = len(section["fields"])
                icon = "done" if section_complete == section_total else "pending"
                st.text(f"[{icon}] {section['label']} ({section_complete}/{section_total})")

        st.divider()

        # Knowledge base stats
        st.subheader("Knowledge Base")
        briefs = get_brief_count()
        corrections = get_correction_count()
        st.text(f"Past briefs: {briefs}")
        st.text(f"Corrections: {corrections}")

        st.divider()

        if st.button("Start New Briefing", use_container_width=True):
            api_key = get_api_key()
            st.session_state.agent = BriefingAgent(api_key=api_key) if api_key else None
            st.session_state.chat_history = []
            st.session_state.initialized = False
            st.rerun()


def render_api_key_input():
    """Render API key input only when no key is configured server-side."""
    st.title("Wiom UAF Communication Briefing Agent")
    st.markdown(
        "Help stakeholders define and validate communication requirements "
        "before submitting to Linear."
    )

    st.divider()

    st.info(
        "No API key is configured on this server. "
        "Ask your admin to add ANTHROPIC_API_KEY to the deployment secrets, "
        "or enter one below to get started."
    )

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Your API key is only stored in the current session and never saved to disk.",
    )

    if st.button("Start Briefing", disabled=not api_key):
        try:
            agent = BriefingAgent(api_key=api_key)
            st.session_state.agent = agent
            st.session_state.api_key_set = True
            st.rerun()
        except Exception as e:
            st.error(f"Failed to initialize: {e}")


def render_chat():
    """Render the chat interface."""
    st.title("Wiom UAF Communication Briefing Agent")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Initialize with opening message
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

    # Chat input
    if user_input := st.chat_input("Describe your communication requirement..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response, tool_calls = st.session_state.agent.send_message(user_input)
                    st.markdown(response)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    st.error(f"Error: {e}")

        # Rerun to update sidebar progress
        st.rerun()


def main():
    st.set_page_config(
        page_title="Wiom UAF Briefing Agent",
        page_icon="clipboard",
        layout="wide",
    )

    init_session()

    if try_auto_start():
        # API key found in secrets/env - stakeholders land directly in chat
        render_sidebar()
        render_chat()
    else:
        # No key configured - show manual input as fallback
        render_api_key_input()


if __name__ == "__main__":
    main()
