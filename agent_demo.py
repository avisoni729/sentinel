"""Demo: the agentic risk investigator on a change the plain rules MISS.

Put your key in a local .env file (SENTINEL_LLM=1 and GEMINI_API_KEY=...),
then:  python agent_demo.py
"""
import os
import pathlib

# Load a local .env (so the key never has to be typed into a terminal/chat).
_env = pathlib.Path(__file__).with_name(".env")
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from sentinel.models import Action
from sentinel.agent import investigate

# A small repo for the agent's tools to explore.
REPO = {
    "src/api/share.py": (
        "def can_edit(user, doc):\n"
        "    if user.id == doc.owner_id:\n"
        "        return True\n"
        "    return False\n\n"
        "def delete_doc(user, doc):\n"
        "    if can_edit(user, doc):\n"
        "        doc.delete()\n"
    ),
}

# The change: the ownership check is replaced with `return True` (allow everyone).
# The deterministic rules score this as ALLOW (no secret/keyword) — they miss it.
DIFF = (
    "+++ b/src/api/share.py\n"
    "@@ -1,3 +1,1 @@ def can_edit(user, doc):\n"
    "-    if user.id == doc.owner_id:\n"
    "-        return True\n"
    "-    return False\n"
    "+    return True  # allow all\n"
)


def main():
    action = Action("PR-authz-bypass", "cursor", "code_pr", DIFF)
    try:
        decision, trace = investigate(action, REPO)
    except RuntimeError as e:
        print("Agent did not run:", e)
        return

    print("AGENT TRACE (how it reasoned)")
    for step in trace:
        print("  ", step)
    print(f"\nDECISION: {decision.verdict}  (risk {decision.risk}/3)")
    for r in decision.reasons:
        print("  -", r)


if __name__ == "__main__":
    main()
