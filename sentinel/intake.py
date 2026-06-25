"""Turn whatever a person pastes into something the gate can read.

If they paste a real diff, use it as-is. If they paste plain code (the common
case for a non-coder trying the demo), wrap it as a brand-new file so the same
rules apply — no diff syntax required from the user.
"""


def looks_like_diff(text):
    return "+++ b/" in text or any(l.startswith("@@") for l in text.splitlines())


def as_diff(text, path="snippet.py"):
    if looks_like_diff(text):
        return text
    lines = text.splitlines() or [""]
    body = "\n".join("+" + l for l in lines)
    return f"+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n{body}\n"
