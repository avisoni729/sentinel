"""Optional LLM risk classifier (Google Gemini, modern google-genai SDK).

Disabled unless SENTINEL_LLM=1, so the gate stays fast/deterministic/offline by
default. Any failure returns None and the gate falls back to rules alone.
"""
import os
import re

PROMPT = """You are a risk classifier for AI-generated code changes.
Rate the risk that this change could cause harm if merged without human review.
Reply with ONE line exactly: RISK=<0-3> | REASON=<short reason>
0 = trivial, 1 = low, 2 = needs a human, 3 = dangerous.

DIFF:
{diff}
"""

MODEL = os.environ.get("SENTINEL_LLM_MODEL", "gemini-2.0-flash")


def score_llm(diff):
    if os.environ.get("SENTINEL_LLM") != "1":
        return None
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=MODEL, contents=PROMPT.format(diff=diff[:6000]))
        out = resp.text or ""
        m = re.search(r"RISK\s*=\s*([0-3])", out)
        r = re.search(r"REASON\s*=\s*(.+)", out)
        if m:
            return int(m.group(1)), (r.group(1).strip() if r else "LLM assessment")
    except Exception:
        return None
    return None
