"""Offline tests for the agent's tools and verdict parsing (no model needed)."""
from sentinel.agent_tools import _read_code, _search_repo, _check_tests, _run_rules
from sentinel.agent import parse_decision
from sentinel.models import Action

REPO = {
    "src/api/share.py": "def can_edit(user, doc):\n    return user.id == doc.owner_id\n",
    "tests/test_share.py": "def test_can_edit(): assert can_edit\n",
}


def test_read_code_returns_file():
    assert "can_edit" in _read_code(REPO, "src/api/share.py")


def test_read_missing_file_is_graceful():
    assert "no file" in _read_code(REPO, "nope.py")


def test_search_finds_usage():
    assert "share.py" in _search_repo(REPO, "can_edit")


def test_check_tests_detects_coverage():
    assert "tests reference it" in _check_tests(REPO, "can_edit")


def test_run_rules_reports_risk():
    out = _run_rules('+++ b/x.py\n+API_KEY = "sk-abcd1234efgh5678ijkl"\n')
    assert "risk=" in out


def test_parse_decision_reads_verdict_line():
    a = Action("t", "you", "code_pr", "")
    d = parse_decision(a, "stuff\nVERDICT=BLOCK | RISK=3 | REASON=removed auth check")
    assert d.verdict == "BLOCK" and d.risk == 3
