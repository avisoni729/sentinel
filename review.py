"""Human approval tool. The 'human in the loop' for HOLD items.

Usage:
  python review.py                 list everything + pending queue
  python review.py approve PR-104  a human approves a pending action
  python review.py reject  PR-106  a human rejects a pending action
"""
import sys
from sentinel import store

ICON = {"auto-approved": "auto", "pending": "WAIT", "blocked": "BLOCK",
        "approved": "ok", "rejected": "NO"}


def show():
    print("\nALL ACTIONS")
    for d in store.list_all():
        print(f"  [{ICON.get(d['status'], d['status']):<5}] {d['action_id']:<22} "
              f"{d['agent']:<12} status={d['status']}")
    pend = store.list_pending()
    print(f"\nPENDING HUMAN APPROVAL ({len(pend)}):")
    if not pend:
        print("  (none)")
    for d in pend:
        print(f"  - {d['action_id']} by {d['agent']} (risk {d['risk']})")
    print("\n  approve with:  python review.py approve <action_id>")
    print("  reject  with:  python review.py reject  <action_id>\n")


def act(verb, action_id):
    status = "approved" if verb == "approve" else "rejected"
    if store.set_status(action_id, status):
        print(f"{action_id} -> {status} by human")
    else:
        print(f"No action found with id {action_id}")


if __name__ == "__main__":
    store.init()
    if len(sys.argv) == 1:
        show()
    elif len(sys.argv) == 3 and sys.argv[1] in ("approve", "reject"):
        act(sys.argv[1], sys.argv[2])
        show()
    else:
        print(__doc__)
