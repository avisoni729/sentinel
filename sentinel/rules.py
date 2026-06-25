"""Deterministic risk signals. Fast, explainable, no LLM needed.

Three layers:
  1. secrets        - credentials committed in code (hard BLOCK)
  2. sensitive path - the change touches auth/payment/infra/... (real code only)
  3. dangerous code - risky constructs in the *added* lines (eval/shell/...)
plus deletions, blast radius, and missing tests.
"""
import re

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{16,}"), "OpenAI-style secret key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"""(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['"][^'"]{8,}['"]"""),
     "hardcoded credential"),
]

SENSITIVE = ["auth", "payment", "billing", "security", ".env", "secret",
             "deploy", "infra", "migration", "dockerfile", "k8s", "credential"]

DANGEROUS = [
    (re.compile(r"\beval\s*\("), "uses eval() (code injection risk)"),
    (re.compile(r"\bexec\s*\("), "uses exec() (code injection risk)"),
    (re.compile(r"shell\s*=\s*True"), "subprocess shell=True (injection risk)"),
    (re.compile(r"\bos\.system\s*\("), "os.system() (shell injection risk)"),
    (re.compile(r"pickle\.loads?\s*\("), "pickle load (unsafe deserialization)"),
    (re.compile(r"verify\s*=\s*False"), "TLS verification disabled"),
    (re.compile(r"(is_admin|is_superuser|is_staff)\s*=\s*True"), "privilege escalation"),
    (re.compile(r"\brm\s+-rf\b"), "rm -rf (destructive)"),
]


def changed_files(diff):
    return re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)


def added_lines(diff):
    return [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]


def _codeish(path):
    """Real code, not a doc or a test (those carry keywords harmlessly)."""
    p = path.lower()
    return not (p.endswith(".md") or p.startswith("docs/") or "test" in p)


def score_rules(diff):
    """Return (risk 0-3, reasons, block_for_secret)."""
    reasons = []
    risk = 0
    block = False

    # 1. secrets
    for pat, label in SECRET_PATTERNS:
        if pat.search(diff):
            reasons.append(f"Possible {label} committed in code")
            block = True

    files = changed_files(diff)

    # 2. sensitive path (real code only — a doc about security isn't a change to it)
    low = " ".join(f for f in files if _codeish(f)).lower()
    hits = sorted({s for s in SENSITIVE if s in low})
    if hits:
        risk = max(risk, 2)
        reasons.append(f"Touches sensitive area: {', '.join(hits)}")

    # 3. dangerous code in the added lines
    body = "\n".join(added_lines(diff))
    for pat, label in DANGEROUS:
        if pat.search(body):
            risk = max(risk, 2)
            reasons.append(f"Dangerous code: {label}")

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

    touches_src = any(f.endswith((".py", ".js", ".ts", ".go", ".java")) and _codeish(f)
                      for f in files)
    touches_test = any("test" in f.lower() for f in files)
    if touches_src and not touches_test:
        risk = max(risk, 1)
        reasons.append("Code changed but no tests touched")

    if not reasons:
        reasons.append("No risk signals found")
    return risk, reasons, block
