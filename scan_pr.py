"""Run Sentinel on a real GitHub pull request.

Usage:
  python scan_pr.py <owner> <repo> <pr_number> [agent]
  python scan_pr.py <owner> <repo>             # uses the latest PR
"""
import sys

from sentinel.models import Action
from sentinel.gate import evaluate
from sentinel import store
from sentinel.github_fetch import fetch_pr_diff, latest_pr

ICON = {"ALLOW": "PASS", "ESCALATE": "HOLD", "BLOCK": "BLOCK"}
EXIT = {"ALLOW": 0, "ESCALATE": 1, "BLOCK": 2}   # non-zero fails CI


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    owner, repo = sys.argv[1], sys.argv[2]
    number = sys.argv[3] if len(sys.argv) > 3 else latest_pr(owner, repo)
    agent = sys.argv[4] if len(sys.argv) > 4 else "github-pr"

    if number is None:
        print("No pull requests found.")
        return

    diff = fetch_pr_diff(owner, repo, number)
    action_id = f"{owner}/{repo}#{number}"
    d = evaluate(Action(action_id, agent, "code_pr", diff))
    store.init()
    store.save_decision(d)

    print(f"\n[{ICON[d.verdict]}] {action_id}  (risk {d.risk}/3)")
    for r in d.reasons:
        print("   -", r)
    print()
    return EXIT[d.verdict]


if __name__ == "__main__":
    sys.exit(main() or 0)
