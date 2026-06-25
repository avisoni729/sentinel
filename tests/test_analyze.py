"""Tests for line-accurate findings used by the inline-comment App."""
from sentinel.analyze import find_findings

DIFF = """diff --git a/src/p.py b/src/p.py
--- a/src/p.py
+++ b/src/p.py
@@ -10,3 +10,5 @@ def handler(req):
     x = 1
+    return eval(req.data)
+    API_KEY = "sk-abcd1234efgh5678ijklmnop"
     y = 2
"""


def test_finds_eval_on_correct_line():
    fs = find_findings(DIFF)
    evals = [f for f in fs if "eval()" in f.message]
    assert evals and evals[0].path == "src/p.py"
    assert evals[0].line == 11   # first added line in the +10 hunk


def test_finds_secret_with_block_severity():
    fs = find_findings(DIFF)
    secrets = [f for f in fs if f.severity == "block"]
    assert secrets and secrets[0].line == 12


def test_clean_diff_has_no_findings():
    clean = ("+++ b/README.md\n@@ -1 +1,2 @@\n docs\n+more docs\n")
    assert find_findings(clean) == []
