"""Tests for the content-rule layer and the over-flag refinements."""
from sentinel.models import Action
from sentinel.gate import evaluate


def run(diff):
    return evaluate(Action("t", "test", "code_pr", diff))


def test_eval_call_is_flagged():
    assert run("+++ b/src/p.py\n+    return eval(x)\n").verdict == "ESCALATE"


def test_shell_true_is_flagged():
    assert run("+++ b/src/r.py\n+    run(cmd, shell=True)\n").verdict == "ESCALATE"


def test_privilege_escalation_is_flagged():
    assert run("+++ b/src/a.py\n+    user.is_admin = True\n").verdict == "ESCALATE"


def test_model_evaluate_is_not_eval():
    # model.evaluate( must NOT trip the eval() rule
    assert run("+++ b/src/ml.py\n+    s = model.evaluate(x)\n").verdict == "ALLOW"


def test_security_doc_is_not_sensitive():
    assert run("+++ b/docs/security.md\n+notes\n").verdict == "ALLOW"


def test_payment_named_test_file_is_not_sensitive():
    assert run("+++ b/tests/test_payment.py\n+def test_x(): pass\n").verdict == "ALLOW"


def test_sql_fstring_is_flagged():
    diff = '+++ b/db.py\n+    cursor.execute(f"SELECT * FROM users WHERE id = {uid}")\n'
    assert run(diff).verdict == "ESCALATE"
