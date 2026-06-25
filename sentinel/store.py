"""Single source of truth: a SQLite store holding every decision + its status.

status lifecycle:
  auto-approved   (verdict ALLOW)        -> done, no human needed
  pending         (verdict ESCALATE)     -> waiting for a human
  blocked         (verdict BLOCK)        -> hard-stopped
  approved/rejected                      -> a human acted on a pending item
"""
import sqlite3
import os
import json
import datetime
from collections import defaultdict

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sentinel.db")

STATUS_FROM_VERDICT = {
    "ALLOW": "auto-approved",
    "ESCALATE": "pending",
    "BLOCK": "blocked",
}


def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS decisions (
            action_id TEXT PRIMARY KEY,
            agent TEXT, kind TEXT, risk INTEGER,
            verdict TEXT, status TEXT, approver TEXT,
            reasons TEXT, ts TEXT)""")


def reset():
    with connect() as c:
        c.execute("DROP TABLE IF EXISTS decisions")
    init()


def save_decision(decision, kind="code_pr"):
    status = STATUS_FROM_VERDICT.get(decision.verdict, "pending")
    with connect() as c:
        c.execute("""INSERT OR REPLACE INTO decisions
            (action_id, agent, kind, risk, verdict, status, approver, reasons, ts)
            VALUES (?,?,?,?,?,?,?,?,?)""",
                  (decision.action_id, decision.agent, kind, decision.risk,
                   decision.verdict, status, None,
                   json.dumps(decision.reasons),
                   datetime.datetime.now().isoformat(timespec="seconds")))
    return status


def list_all():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM decisions ORDER BY ts")]


def list_pending():
    with connect() as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM decisions WHERE status='pending' ORDER BY ts")]


def set_status(action_id, status, approver="human"):
    with connect() as c:
        cur = c.execute("UPDATE decisions SET status=?, approver=? WHERE action_id=?",
                        (status, approver, action_id))
        return cur.rowcount > 0


def scorecard():
    rows = defaultdict(lambda: defaultdict(int))
    for d in list_all():
        s = rows[d["agent"]]
        s["total"] += 1
        s[d["status"]] += 1
    out = []
    for agent, s in sorted(rows.items()):
        flagged = s["pending"] + s["approved"] + s["rejected"] + s["blocked"]
        rate = flagged / s["total"] if s["total"] else 0
        out.append((agent, s["total"], s["auto-approved"], flagged, s["blocked"], rate))
    return out
