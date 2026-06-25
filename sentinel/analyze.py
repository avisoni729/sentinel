"""Locate risky findings to a specific file + line, so the GitHub App can post
*inline* review comments (not just one summary).

Walks the unified diff, tracking new-file line numbers through the hunks, and
applies the secret + dangerous-code patterns to each added line.
"""
import re
from dataclasses import dataclass

from .rules import SECRET_PATTERNS, DANGEROUS

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
FILE = re.compile(r"^\+\+\+ b/(.+)$")


@dataclass
class Finding:
    path: str
    line: int          # line number in the new file (RIGHT side)
    severity: str      # "block" | "warn"
    message: str


def find_findings(diff):
    findings = []
    path = None
    new_line = 0

    for raw in diff.splitlines():
        mf = FILE.match(raw)
        if mf:
            path = mf.group(1)
            continue
        mh = HUNK.match(raw)
        if mh:
            new_line = int(mh.group(1))
            continue
        if path is None:
            continue

        if raw.startswith("+") and not raw.startswith("+++"):
            text = raw[1:]
            for pat, label in SECRET_PATTERNS:
                if pat.search(text):
                    findings.append(Finding(path, new_line, "block",
                                            f"🔒 Possible {label} — do not commit secrets."))
            for pat, label in DANGEROUS:
                if pat.search(text):
                    findings.append(Finding(path, new_line, "warn",
                                            f"⚠️ {label}"))
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue  # removed line: no new-file number
        else:
            new_line += 1  # context line

    return findings
