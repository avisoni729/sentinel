"""Optional LLM risk classifier. Falls back to None if no API key is set,
so the whole thing still runs offline on rules alone."""
import os
import re

PROMPT = """You are a risk classifier for AI-generated code changes.
Rate the risk that this change could cause harm if merged without human review.
Reply with ONE line exactly: RISK=<0-3> | REASON=<short reason>
0 = trivial, 1 = low, 2 = needs a human, 3 = dangerous.

DIFF:
{diff}
"""


def score_llm(diff):
    # Opt-in only: set SENTINEL_LLM=1 to enable the live classifier.
    # Keeps the demo fast, deterministic, and offline by default.
    if os.environ.get("SENTINEL_LLM") != "1":
        return None
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        out = model.generate_content(PROMPT.format(diff=diff[:6000])).text
        m = re.search(r"RISK\s*=\s*([0-3])", out)
        r = re.search(r"REASON\s*=\s*(.+)", out)
        if m:
            return int(m.group(1)), (r.group(1).strip() if r else "LLM assessment")
    except Exception:
        return None
    return None
