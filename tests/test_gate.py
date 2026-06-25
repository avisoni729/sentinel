"""Behaviour tests for the gate. Run: python -m pytest -q"""
from sentinel.models import Action
from sentinel.gate import evaluate


def run(diff, agent="test"):
    return evaluate(Action("t", agent, "code_pr", diff))


def test_leaked_secret_is_blocked():
    diff = '+++ b/config.py\n+API_KEY = "sk-abcd1234efgh5678ijklmnop"\n'
    assert run(diff).verdict == "BLOCK"


def test_plain_docs_change_is_allowed():
    diff = "+++ b/README.md\n+Just documentation.\n"
    assert run(diff).verdict == "ALLOW"


def test_auth_change_is_escalated():
    diff = "+++ b/src/auth/login.py\n+def verify(t):\n+    return True\n"
    assert run(diff).verdict == "ESCALATE"


def test_file_deletion_is_escalated():
    diff = "+++ b/src/thing.py\ndeleted file mode 100644\n-old code\n"
    assert run(diff).verdict == "ESCALATE"


def test_decision_is_attributed_to_agent():
    d = run("+++ b/README.md\n+hi\n", agent="cursor")
    assert d.agent == "cursor"
