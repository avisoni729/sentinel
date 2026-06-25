"""Sentinel dashboard — the live, clickable demo.

Local:   streamlit run dashboard.py
Hosted:  deploy this repo on Streamlit Community Cloud (entry file: dashboard.py)
"""
import json

import streamlit as st

from sentinel.models import Action
from sentinel.gate import evaluate
from sentinel import store, seed

store.init()
seed.seed_if_empty()

st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide")

VERDICT_COLOR = {"ALLOW": "green", "ESCALATE": "orange", "BLOCK": "red"}
VERDICT_WORD = {"ALLOW": "PASS — auto-approved",
                "ESCALATE": "HOLD — needs a human",
                "BLOCK": "BLOCK — stopped"}

st.title("🛡️ Sentinel")
st.markdown(
    "**A control plane for AI-generated actions.** Before a risky change from an "
    "AI tool (Copilot, Cursor, Claude Code…) is let through, Sentinel "
    "**risk-scores it, decides pass / hold / block, logs it, and scores each "
    "agent's reliability over time.** It doesn't judge code *quality* — it judges "
    "*risk and trust*. [How it works ↓](#how-it-works)"
)

tab_try, tab_board, tab_about = st.tabs(["▶ Try it", "📊 Live board", "ℹ️ How it works"])

# ---------------------------------------------------------------- Try it
with tab_try:
    st.subheader("Paste an AI-generated change and let Sentinel judge it")
    samples = {s["id"]: s for s in seed.load_samples()}
    pick = st.selectbox("Start from a sample (or edit it):", list(samples.keys()))
    chosen = samples[pick]

    col_l, col_r = st.columns(2)
    with col_l:
        agent = st.text_input("AI tool / agent name", chosen["agent"])
        action_id = st.text_input("Change id", "TRY-" + pick)
    diff = st.text_area("Diff", chosen["diff"], height=240)

    if st.button("Run Sentinel", type="primary"):
        d = evaluate(Action(action_id, agent, "code_pr", diff))
        store.save_decision(d)
        st.markdown(f"### :{VERDICT_COLOR[d.verdict]}[{VERDICT_WORD[d.verdict]}]  "
                    f"·  risk {d.risk}/3")
        for r in d.reasons:
            st.write("•", r)
        st.caption("Saved to the audit log — see the Live board tab.")

# ---------------------------------------------------------------- Board
with tab_board:
    rows = store.list_all()
    total = len(rows)
    auto = sum(1 for r in rows if r["status"] == "auto-approved")
    pending = sum(1 for r in rows if r["status"] == "pending")
    blocked = sum(1 for r in rows if r["status"] == "blocked")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total actions", total)
    c2.metric("Auto-approved", auto)
    c3.metric("Waiting on human", pending)
    c4.metric("Blocked", blocked)

    st.subheader("Pending human approval")
    pend = store.list_pending()
    if not pend:
        st.success("Nothing waiting.")
    for d in pend:
        with st.container(border=True):
            st.markdown(f"**{d['action_id']}** · by `{d['agent']}` · risk {d['risk']}")
            st.write(", ".join(json.loads(d["reasons"])) if d["reasons"] else "")
            a, b, _ = st.columns([1, 1, 6])
            if a.button("✅ Approve", key="a" + d["action_id"]):
                store.set_status(d["action_id"], "approved"); st.rerun()
            if b.button("❌ Reject", key="r" + d["action_id"]):
                store.set_status(d["action_id"], "rejected"); st.rerun()

    st.subheader("Agent scorecard (appraisal)")
    st.table([
        {"agent": a, "total": t, "auto-approved": au, "flagged": f,
         "blocked": bl, "flag %": f"{r*100:.0f}%"}
        for a, t, au, f, bl, r in store.scorecard()
    ])

    st.subheader("Audit log")
    st.dataframe(
        [{"time": r["ts"], "action": r["action_id"], "agent": r["agent"],
          "verdict": r["verdict"], "status": r["status"]} for r in rows],
        use_container_width=True,
    )
    if st.button("↺ Reset demo data"):
        seed.seed(reset=True); st.rerun()

# ---------------------------------------------------------------- About
with tab_about:
    st.markdown("""
#### How it works
1. **Intercept** — an AI tool's change (a pull request) reaches the gate.
2. **Score risk** — deterministic rules (secrets, sensitive files, deletions,
   missing tests, blast radius) plus an optional LLM classifier.
3. **Decide** — `ALLOW` (auto-approve) · `ESCALATE` (hold for a human) ·
   `BLOCK` (stop, e.g. a leaked secret).
4. **Audit** — every decision is logged and attributed to the agent that made it.
5. **Appraise** — decisions roll up into a per-agent trust scorecard over time.

#### Why it matters
As AI tools move from *suggesting* to *acting*, the bottleneck becomes trust and
accountability, not generation. ~95% of enterprise GenAI pilots stall on
governance, not model quality. Sentinel is the missing control point.

#### Not a code reviewer
A reviewer asks *"is this code good?"*. Sentinel asks *"is this AI change safe to
let through without a human, and which tools can we trust?"* — gate + audit +
appraise.
""")
