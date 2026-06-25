"""Run Sentinel over the sample changes, persist decisions, print the board."""
import json
import os

from sentinel.models import Action
from sentinel.gate import evaluate
from sentinel import store

HERE = os.path.dirname(__file__)
ICON = {"ALLOW": "PASS ", "ESCALATE": "HOLD ", "BLOCK": "BLOCK"}


def main():
    store.reset()   # fresh run

    path = os.path.join(HERE, "samples", "samples.json")
    samples = json.load(open(path, encoding="utf-8"))

    print("=" * 72)
    print("SENTINEL  -  gate for AI-generated actions  (MVP demo)")
    print("=" * 72)

    for s in samples:
        action = Action(s["id"], s["agent"], "code_pr", s["diff"])
        d = evaluate(action)
        store.save_decision(d)
        print(f"\n[{ICON[d.verdict]}] {d.action_id:<22} by {d.agent:<12} risk={d.risk}")
        for r in d.reasons:
            print(f"          - {r}")

    pend = store.list_pending()
    print("\n" + "=" * 72)
    print("AGENT SCORECARD  (appraisal)")
    print("=" * 72)
    print(f"{'agent':<14}{'total':>6}{'auto':>6}{'flagged':>9}{'blocked':>9}{'flag%':>8}")
    for agent, total, auto, flagged, blk, rate in store.scorecard():
        print(f"{agent:<14}{total:>6}{auto:>6}{flagged:>9}{blk:>9}{rate*100:>7.0f}%")

    print(f"\n{len(pend)} action(s) waiting for a human. Review them with:")
    print("    python review.py\n")


if __name__ == "__main__":
    main()
