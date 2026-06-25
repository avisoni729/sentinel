"""Deterministic risk signals. Fast, explainable, no LLM needed."""
import re

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "OpenAI-style secret key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"""(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['"][^'"]{8,}['"]"""),
     "hardcoded credential"),
]

SENSITIVE = ["auth", "payment", "billing", "security", ".env", "secret",
             "deploy", "infra", "migration", "dockerfile", "k8s", "credential"]


def changed_files(diff):
    return re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)


def added_lines(diff):
    return [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]


def score_rules(diff):
    """Return (risk 0-3, reasons, block_for_secret)."""
    reasons = []
    risk = 0
    block = False

    for pat, label in SECRET_PATTERNS:
        if pat.search(diff):
            reasons.append(f"Possible {label} committed in code")
            block = True

    files = changed_files(diff)
    low = " ".join(files).lower()
    hits = sorted({s for s in SENSITIVE if s in low})
    if hits:
        risk = max(risk, 2)
        reasons.append(f"Touches sensitive area: {', '.join(hits)}")

    if "deleted file mode" in diff:
        risk = max(risk, 2)
        reasons.append("Deletes one or more files")

    adds = len(added_lines(diff))
    if adds > 80:
        risk = max(risk, 2)
        reasons.append(f"Large change ({adds} added lines)")
    elif adds > 25:
        risk = max(risk, 1)
        reasons.append(f"Medium-size change ({adds} added lines)")

    touches_src = any(f.endswith((".py", ".js", ".ts", ".go", ".java")) for f in files)
    touches_test = any("test" in f.lower() for f in files)
    if touches_src and not touches_test:
        risk = max(risk, 1)
        reasons.append("Code changed but no tests touched")

    if not reasons:
        reasons.append("No risk signals found")
    return risk, reasons, block
