"""Measure the gate against the labeled dataset: precision / recall / F1 +
an honest list of what it got wrong.

Run:  python eval/run_eval.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sentinel.models import Action
from sentinel.gate import evaluate

DATA = os.path.join(os.path.dirname(__file__), "dataset.json")


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    tp = fp = tn = fn = 0
    misses = []

    for e in data:
        d = evaluate(Action(e["id"], "eval", "code_pr", e["diff"]))
        pred = d.verdict in ("ESCALATE", "BLOCK")   # flagged?
        exp = e["expected_flag"]
        if pred and exp:
            tp += 1
        elif pred and not exp:
            fp += 1
            misses.append(("FALSE ALARM ", e, d))
        elif not pred and not exp:
            tn += 1
        else:
            fn += 1
            misses.append(("MISSED RISK ", e, d))

    n = len(data)
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    acc = (tp + tn) / n

    print("=" * 60)
    print(f"SENTINEL gate - evaluation on {n} labeled changes")
    print("=" * 60)
    print(f"  Precision : {prec:.2f}   (of those flagged, how many truly risky)")
    print(f"  Recall    : {rec:.2f}   (of truly risky, how many we caught)")
    print(f"  F1        : {f1:.2f}")
    print(f"  Accuracy  : {acc:.2f}")
    print(f"\n  confusion: TP={tp}  FP={fp}  TN={tn}  FN={fn}")

    print("\n  Where it was wrong (the honest part):")
    if not misses:
        print("    (none)")
    for kind, e, d in misses:
        print(f"    [{kind}] {e['id']:<22} got {d.verdict:<9} - {e['note']}")
    print("\n  Takeaway: rules catch explicit risk (secrets, sensitive paths,")
    print("  deletions) but miss *semantic* risk (eval/shell/privilege) and")
    print("  over-flag on filenames - which is exactly what the LLM classifier")
    print("  and policy tuning on the roadmap are for.\n")


if __name__ == "__main__":
    main()
