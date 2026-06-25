"""Sentinel dashboard — the live, clickable demo (built to be clear to non-coders).

Local:   streamlit run dashboard.py
Hosted:  Streamlit Community Cloud, entry file dashboard.py
"""
import json
import os
import time

import streamlit as st

from sentinel.models import Action
from sentinel.gate import evaluate
from sentinel.analyze import find_findings
from sentinel.intake import as_diff
from sentinel import store, seed


def _load_key():
    """Pull a Gemini key from Streamlit secrets (cloud) or a local .env."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
            os.environ.setdefault("SENTINEL_LLM", "1")
    except Exception:
        pass
    envf = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(envf):
        for line in open(envf, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()


def _agent_ready():
    return os.environ.get("SENTINEL_LLM") == "1" and bool(os.environ.get("GEMINI_API_KEY"))


_load_key()
store.init()
seed.seed_if_empty()

st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide")

# Plain-English verdict, for non-coders
RESULT = {
    "ALLOW":    ("green",  "✅ PASS",  "Looks safe — no human needed."),
    "ESCALATE": ("orange", "🟠 HOLD",  "Risky — a person should review this before it goes live."),
    "BLOCK":    ("red",    "🛑 BLOCK", "Stopped — this should not be allowed through as-is."),
}

# Four copy-paste examples (3 risky + 1 safe). The user never sees diff syntax.
EXAMPLES = [
    ("A bank function with a password written right in the code",
     'def connect():\n    API_KEY = "sk-abcd1234efgh5678ijklmnop"\n    return Database(API_KEY)'),
    ("A function that runs whatever text a user sends it",
     'def handle(request):\n    return eval(request.data)'),
    ("A function that runs a system command built from user input",
     'import subprocess\ndef run(user_cmd):\n    subprocess.run(user_cmd, shell=True)'),
    ("A simple, harmless function that adds two numbers",
     'def add(a, b):\n    return a + b'),
]

# A prebuilt scenario for the AI agent: an authorization check quietly removed.
AGENT_REPO = {
    "src/api/share.py": (
        "def can_edit(user, doc):\n"
        "    if user.id == doc.owner_id:\n"
        "        return True\n"
        "    return False\n\n"
        "def delete_doc(user, doc):\n"
        "    if can_edit(user, doc):\n"
        "        doc.delete()\n"
    ),
}
AGENT_DIFF = (
    "+++ b/src/api/share.py\n"
    "@@ -1,3 +1,1 @@ def can_edit(user, doc):\n"
    "-    if user.id == doc.owner_id:\n"
    "-        return True\n"
    "-    return False\n"
    "+    return True  # allow all\n"
)

st.title("🛡️ Sentinel")
st.markdown(
    "**AI tools now write a lot of code on their own — and some of it is risky** "
    "(a leaked password, a dangerous command). Sentinel is an automatic safety "
    "check that reads each AI-made change and decides **Pass**, **Hold** (ask a "
    "human), or **Block** — *before* it can cause harm. Try it below 👇"
)

tab_try, tab_agent, tab_board, tab_about = st.tabs(
    ["▶ Try it", "🤖 AI agent", "📊 Live board", "ℹ️ What is this?"])

# ---------------------------------------------------------------- Try it
with tab_try:
    st.subheader("Try it — no coding needed")
    st.markdown(
        "1. Pick an example below and click the **copy icon** (top-right of the box).\n"
        "2. **Paste** it into the box at the bottom.\n"
        "3. Press **Check this code** and see the result.\n\n"
        "*Or paste any code of your own.*"
    )

    for label, code in EXAMPLES:
        st.markdown(f"**{label}**")
        st.code(code, language="python")

    st.divider()
    pasted = st.text_area("Paste code here", height=170, placeholder="Paste one of the examples above…")
    if st.button("Check this code", type="primary"):
        if not pasted.strip():
            st.warning("Paste some code first.")
        else:
            action = Action(f"TRY-{int(time.time())}", "you", "code_pr", as_diff(pasted))
            d = evaluate(action, snippet=True)
            store.save_decision(d)
            color, head, meaning = RESULT[d.verdict]
            st.markdown(f"## :{color}[{head}]")
            st.markdown(f"**{meaning}**")
            st.markdown("**Why:**")
            for r in d.reasons:
                st.write("•", r)
            findings = find_findings(as_diff(pasted))
            if findings:
                st.caption("Flagged lines:")
                for f in findings:
                    st.write(f"  line {f.line}: {f.message}")

# ---------------------------------------------------------------- AI agent
with tab_agent:
    st.subheader("🤖 The AI agent — it investigates, then judges")
    st.markdown(
        "The checks on the *Try it* tab use fixed rules. **This is a real AI agent:** "
        "it plans what to look at, uses tools to read the code and see where it's "
        "used, then decides — catching risks the fixed rules miss."
    )
    st.markdown("**The change it will inspect** — an access check quietly removed:")
    st.code("- if user.id == doc.owner_id:   # only the owner could edit\n"
            "+ return True                    # now ANYONE can edit", language="python")
    st.caption("The fixed rules rate this low-risk and would let it pass. Watch the agent.")

    if not _agent_ready():
        st.info("The live agent needs a Gemini API key — add it as a Streamlit "
                "**secret** `GEMINI_API_KEY` (or a local `.env`). The rules demo "
                "on the other tabs works without it.")
    elif st.button("🔍 Run the AI agent", type="primary"):
        decision, trace = None, None
        with st.spinner("The agent is investigating…"):
            try:
                from sentinel.agent import investigate
                action = Action("DEMO-authz", "ai-agent", "code_pr", AGENT_DIFF)
                decision, trace = investigate(action, AGENT_REPO)
                store.save_decision(decision)
            except Exception as e:
                st.error("The agent couldn't finish — usually the free-tier rate "
                         "limit. Try again in a minute.")
                st.caption(str(e)[:200])
        if decision:
            st.markdown("**How the agent reasoned:**")
            for step in trace:
                st.write(step)
            color, head, _ = RESULT[decision.verdict]
            st.markdown(f"### :{color}[{head}]  ·  risk {decision.risk}/3")
            for r in decision.reasons:
                st.write("•", r)
            st.success("The fixed rules missed this — the agent caught it by investigating.")

# ---------------------------------------------------------------- Board
with tab_board:
    st.caption("Every check is recorded here, and each AI tool gets a trust score over time.")
    rows = store.list_all()
    total = len(rows)
    auto = sum(1 for r in rows if r["status"] == "auto-approved")
    pending = sum(1 for r in rows if r["status"] == "pending")
    blocked = sum(1 for r in rows if r["status"] == "blocked")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total checks", total)
    c2.metric("Passed", auto)
    c3.metric("Waiting on human", pending)
    c4.metric("Blocked", blocked)

    st.subheader("Waiting for a human")
    pend = store.list_pending()
    if not pend:
        st.success("Nothing waiting.")
    for d in pend:
        with st.container(border=True):
            st.markdown(f"**{d['action_id']}** · from `{d['agent']}` · risk {d['risk']}/3")
            st.write(", ".join(json.loads(d["reasons"])) if d["reasons"] else "")
            a, b, _ = st.columns([1, 1, 6])
            if a.button("✅ Approve", key="a" + d["action_id"]):
                store.set_status(d["action_id"], "approved"); st.rerun()
            if b.button("❌ Reject", key="r" + d["action_id"]):
                store.set_status(d["action_id"], "rejected"); st.rerun()

    st.subheader("Trust scorecard (per AI tool)")
    st.table([
        {"AI tool": a, "checks": t, "passed": au, "flagged": f,
         "blocked": bl, "flag %": f"{r*100:.0f}%"}
        for a, t, au, f, bl, r in store.scorecard()
    ])

    st.subheader("Full log")
    st.dataframe(
        [{"time": r["ts"], "change": r["action_id"], "from": r["agent"],
          "result": r["verdict"], "status": r["status"]} for r in rows],
        use_container_width=True,
    )
    if st.button("↺ Reset demo data"):
        seed.seed(reset=True); st.rerun()

# ---------------------------------------------------------------- About
with tab_about:
    st.markdown("""
#### The problem, in one line
AI now writes code faster than people can safely check it. The bottleneck is no
longer *writing* — it's *trust*.

#### What Sentinel does
It sits between the AI and your systems and, for every AI-made change:
1. **Reads** it and scores how risky it is.
2. **Decides** — Pass (safe), Hold (ask a human), or Block (stop, e.g. a leaked password).
3. **Records** it, so there's always a clear trail of what the AI did.
4. **Scores** each AI tool over time, so you know which ones to trust.

#### Why it matters
About 95% of company AI projects stall — not because the AI is dumb, but because
no one can safely review and trust what it produces. Sentinel is the missing
safety check.

*Built by Avi Kishore Soni · [GitHub](https://github.com/avisoni729/sentinel)*
""")
