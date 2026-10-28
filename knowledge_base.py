"""
Knowledge base for storing and retrieving past briefs and corrections.
Evolves over time as more briefs are completed.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
BRIEFS_DIR = KNOWLEDGE_DIR / "completed_briefs"
CORRECTIONS_DIR = KNOWLEDGE_DIR / "corrections"


def _ensure_dirs():
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_brief(brief_data: dict, title: str) -> str:
    """Save a completed brief to the knowledge base. Returns the file path."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = title.lower().replace(" ", "_")[:50]
    filename = f"{timestamp}_{slug}.json"
    filepath = BRIEFS_DIR / filename

    record = {
        "title": title,
        "created_at": datetime.now().isoformat(),
        "brief": brief_data,
    }

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)

    return str(filepath)


def save_correction(brief_title: str, feedback: str) -> str:
    """Save stakeholder feedback/correction for a brief."""
    _ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_correction.json"
    filepath = CORRECTIONS_DIR / filename

    record = {
        "brief_title": brief_title,
        "created_at": datetime.now().isoformat(),
        "feedback": feedback,
    }

    with open(filepath, "w") as f:
        json.dump(record, f, indent=2)

    return str(filepath)


def search_briefs(query: str, max_results: int = 3) -> List[dict]:
    """
    Search past briefs by keyword matching against title, business problem,
    communication type, and channel selection.
    Returns the most relevant past briefs.
    """
    _ensure_dirs()
    results = []
    query_lower = query.lower()
    keywords = query_lower.split()

    for filepath in sorted(BRIEFS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath) as f:
                record = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        searchable = json.dumps(record).lower()
        score = sum(1 for kw in keywords if kw in searchable)

        if score > 0:
            results.append({"score": score, "record": record, "file": filepath.name})

    results.sort(key=lambda x: x["score"], reverse=True)
    return [r["record"] for r in results[:max_results]]


def get_all_corrections() -> List[dict]:
    """Load all corrections to use as learning context."""
    _ensure_dirs()
    corrections = []
    for filepath in sorted(CORRECTIONS_DIR.glob("*.json"), reverse=True):
        try:
            with open(filepath) as f:
                corrections.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            continue
    return corrections


def get_knowledge_context() -> str:
    """
    Build a context string from past briefs and corrections
    to inject into the system prompt for learning.
    """
    briefs = []
    for filepath in sorted(BRIEFS_DIR.glob("*.json"), reverse=True)[:10]:
        try:
            with open(filepath) as f:
                briefs.append(json.load(f))
        except (json.JSONDecodeError, IOError):
            continue

    corrections = get_all_corrections()

    if not briefs and not corrections:
        return ""

    parts = []

    if briefs:
        parts.append("## Past briefs (use as reference for suggestions, always confirm with stakeholder)")
        for b in briefs:
            title = b.get("title", "Untitled")
            brief = b.get("brief", {})
            # Extract key fields for context
            biz = brief.get("A_business_objective", {}).get("fields", {})
            channels = brief.get("C_channel_selection", {}).get("fields", {})
            freq = brief.get("E_frequency_priority", {}).get("fields", {})

            summary_parts = [f"- **{title}**"]
            if problem := biz.get("business_problem", {}).get("value"):
                summary_parts.append(f"  Problem: {problem}")
            if comm_type := biz.get("communication_type", {}).get("value"):
                summary_parts.append(f"  Type: {comm_type}")
            if ch := channels.get("selected_channels", {}).get("value"):
                summary_parts.append(f"  Channels: {ch}")
            if lc := freq.get("lifetime_cap", {}).get("value"):
                summary_parts.append(f"  Lifetime cap: {lc}")

            parts.append("\n".join(summary_parts))

    if corrections:
        parts.append("\n## Lessons from past corrections (apply these proactively)")
        for c in corrections[:10]:
            parts.append(f"- Brief \"{c.get('brief_title', '?')}\": {c.get('feedback', '')}")

    return "\n\n".join(parts)


def get_brief_count() -> int:
    """Return the number of completed briefs in the knowledge base."""
    _ensure_dirs()
    return len(list(BRIEFS_DIR.glob("*.json")))


def get_correction_count() -> int:
    """Return the number of corrections in the knowledge base."""
    _ensure_dirs()
    return len(list(CORRECTIONS_DIR.glob("*.json")))
