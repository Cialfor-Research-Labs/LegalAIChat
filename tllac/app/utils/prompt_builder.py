"""
Prompt loader for the TLLAC LLM-only chat flow.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAWYER_PROMPT_PATH = _REPO_ROOT / "Lawyer.md"
_FALLBACK_PROMPT = (
    "You are Lawyer AI, a senior Indian legal assistant. "
    "Answer in Indian legal context only, separate facts from assumptions, "
    "identify legal issues, evidence, forum, remedies, risks, and next steps."
)


@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    """Return the Lawyer AI system prompt loaded from Lawyer.md."""
    try:
        prompt = _LAWYER_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return _FALLBACK_PROMPT

    return prompt or _FALLBACK_PROMPT
