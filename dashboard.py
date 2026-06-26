"""Sentinel dashboard — the live, clickable demo.

Local:   streamlit run dashboard.py
Hosted:  Streamlit Community Cloud, entry file dashboard.py
"""
import html
import json
import os
import time

import streamlit as st

from sentinel.models import Action
from sentinel.gate import evaluate
from sentinel.analyze import find_findings
from sentinel.intake import as_diff
from sentinel import store, seed


# --------------------------------------------------------------- key / secrets
def _load_key():
    """Pull a Gemini key from Streamlit secrets (cloud) or a local .env."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
            os.environ.setdefault("SENTINEL_LLM", "1")
    except Exception:
        pass
    envf = os.path.join(os.path.dirname(__file__), ".env")
    try:
        if os.path.exists(envf):
            for line in open(envf, encoding="utf-8"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except Exception:
        pass


def _agent_ready():
    return os.environ.get("SENTINEL_LLM") == "1" and bool(os.environ.get("GEMINI_API_KEY"))


_load_key()
try:
    store.init()
    seed.seed_if_empty()
except Exception:
    pass   # the page still renders even if the demo data can't seed

st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide")

# --------------------------------------------------------------- look & feel
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;600;700&family=Spectral:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --paper:#F6EFDF; --canvas:#EDE4D1; --ink:#2C2117; --muted:#6F5E47;
  --saddle:#9E4A24; --indigo:#2B4257; --stitch:#C9B68F;
  --pass:#5E6B4F; --hold:#B07A1E; --block:#8A3324;
}
.stApp{
  background:
    radial-gradient(1200px 500px at 18% -8%, #F3EAD7 0%, rgba(243,234,215,0) 60%),
    var(--canvas);
  color:var(--ink);
  font-family:'Spectral', Georgia, serif;
}
h1,h2,h3,h4{ font-family:'Zilla Slab', Georgia, serif !important; color:var(--ink); letter-spacing:.3px; }
h1{ border-bottom:3px double var(--saddle); padding-bottom:.18em; }
a, a:visited{ color:var(--indigo) !important; text-decoration:underline dotted; text-underline-offset:3px; }
p, li, label, .markdown-text-container{ font-family:'Spectral', Georgia, serif; }
code, pre, .mono{ font-family:'JetBrains Mono', monospace; }
small, .muted{ color:var(--muted); }

.tagline{ color:var(--muted); font-size:1.05rem; }

.verdict{ display:inline-block; padding:9px 22px; border-radius:5px;
  font-family:'Zilla Slab', serif; font-weight:700; font-size:1.5rem;
  color:#F6EFDF; letter-spacing:1px; box-shadow:0 3px 8px #0003, inset 0 1px 0 #ffffff22; }
.v-pass{ background:var(--pass);} .v-hold{ background:var(--hold);} .v-block{ background:var(--block);}

.meter{ height:9px; border-radius:5px; background:#00000012; overflow:hidden; margin:10px 0 6px; max-width:280px; }
.meter > span{ display:block; height:100%; border-radius:5px; }

.reason{ padding:5px 0 5px 14px; border-left:3px solid var(--saddle); margin:7px 0; }

.step{ background:var(--paper); border:1px dashed var(--stitch); border-radius:6px;
  padding:8px 12px; margin:7px 0; font-size:.95rem; }

.codeblock{ background:#241B12; color:#E9DEC8; border-radius:8px; padding:14px 12px;
  font-family:'JetBrains Mono', monospace; font-size:.84rem; line-height:1.55; overflow-x:auto;
  border:1px solid #00000033; box-shadow:inset 0 2px 10px #00000040; white-space:pre; }
.codeblock .ln{ color:#7d6b4f; }
.codeblock .flag{ background:#8A332455; border-left:3px solid #E0795F; display:block; padding-left:6px; }

.stButton>button{ background:var(--saddle); color:#F6EFDF; border:1px solid #00000022;
  border-radius:6px; font-family:'Zilla Slab', serif; font-weight:600; letter-spacing:.4px;
  padding:.45rem 1.1rem; box-shadow:0 2px 6px #0003; }
.stButton>button:hover{ background:#86381a; color:#fff; border-color:#00000033; }
[data-testid="stSidebar"]{ background:#E7DBC2; border-right:1px solid var(--stitch); }
[data-testid="stMetricValue"]{ font-family:'Zilla Slab', serif; }
.stTabs [data-baseweb="tab"]{ font-family:'Zilla Slab', serif; }
</style>
""", unsafe_allow_html=True)

VERDICT_UI = {
    "ALLOW":    ("v-pass",  "PASS",  "Looks safe — no human needed.",                       "#5E6B4F"),
    "ESCALATE": ("v-hold",  "HOLD",  "Risky — a person should review this before it goes live.", "#B07A1E"),
    "BLOCK":    ("v-block", "BLOCK", "Stopped — this should not go through as-is.",          "#8A3324"),
}

EXAMPLES = [
    ("A database function with a password written right in the code",
     'def connect():\n    API_KEY = "sk-abcd1234efgh5678ijklmnop"\n    return Database(API_KEY)'),
    ("A function that runs whatever text a user sends it",
     'def handle(request):\n    return eval(request.data)'),
    ("A function that runs a system command built from user input",
     'import subprocess\ndef run(user_cmd):\n    subprocess.run(user_cmd, shell=True)'),
    ("A database query that pastes user input straight into SQL",
     'def get_user(uid):\n    cursor.execute(f"SELECT * FROM users WHERE id = {uid}")'),
    ("A simple, harmless function that adds two numbers",
     'def add(a, b):\n    return a + b'),
]

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


# --------------------------------------------------------------- render helpers
def show_verdict(d):
    cls, word, meaning, color = VERDICT_UI[d.verdict]
    pct = max(int(d.risk / 3 * 100), 8)
    st.markdown(f"<div class='verdict {cls}'>{word}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='meter'><span style='width:{pct}%;background:{color}'></span></div>",
                unsafe_allow_html=True)
    st.markdown(f"**{meaning}** &nbsp;&nbsp; <span class='muted'>risk {d.risk}/3</span>",
                unsafe_allow_html=True)
    st.markdown("**Why:**")
    for r in d.reasons:
        st.markdown(f"<div class='reason'>{html.escape(r)}</div>", unsafe_allow_html=True)


def show_code_with_flags(code, findings):
    flagged = {f.line for f in findings}
    lines = code.splitlines() or [code]
    rows = []
    for i, ln in enumerate(lines, 1):
        safe = html.escape(ln) if ln.strip() else "&nbsp;"
        cls = "flag" if i in flagged else ""
        rows.append(f"<span class='{cls}'><span class='ln'>{i:>2}</span>  {safe}</span>")
    st.markdown("<div class='codeblock'>" + "\n".join(rows) + "</div>", unsafe_allow_html=True)


def agent_error_message(e):
    """Map any agent failure to a plain-English message."""
    m = str(e).lower()
    if isinstance(e, RuntimeError) and "needs" in m:
        return ("The AI agent isn't switched on here — it needs a Gemini API key. "
                "The rule checks on the other tabs work without it.")
    if any(w in m for w in ["quota", "rate", "429", "resource_exhausted", "exhausted"]):
        return "The AI agent has hit its free usage limit for the moment. Please try again in a minute."
    if any(w in m for w in ["api key", "api_key", "invalid", "401", "403", "permission"]):
        return "The AI agent's API key looks invalid. (If this is your app, check the GEMINI_API_KEY secret.)"
    if any(w in m for w in ["timed out", "timeout", "connection", "network", "resolve", "ssl"]):
        return "Couldn't reach the AI service just now — likely a network hiccup. Please try again."
    return "Something went wrong running the AI agent. Please try again in a moment."


# --------------------------------------------------------------- header
st.title("🛡️ Sentinel")
st.markdown(
    "<span class='tagline'>AI now writes a lot of code on its own — and some of it is risky. "
    "Sentinel reads each AI-made change and decides <b>Pass</b>, <b>Hold</b> (ask a human), "
    "or <b>Block</b>, before it can do harm.</span>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Sentinel")
    st.markdown("<span class='muted'>A control plane for AI-generated code.</span>",
                unsafe_allow_html=True)
    st.markdown("**How it works**")
    st.markdown("1. Read the change\n2. Score the risk\n3. Pass / Hold / Block\n"
                "4. Log it\n5. Score each AI tool")
    st.markdown("---")
    st.markdown("[Source code on GitHub](https://github.com/avisoni729/sentinel)")
    st.markdown("<span class='muted'>Built by Avi Kishore Soni</span>", unsafe_allow_html=True)

tab_try, tab_agent, tab_board, tab_about = st.tabs(
    ["▶ Try it", "🤖 AI agent", "📊 Live board", "ℹ️ What is this?"])

# --------------------------------------------------------------- Try it
with tab_try:
    st.subheader("Try it — no coding needed")
    st.markdown(
        "1. Pick an example below and click the **copy icon** (top-right of the box).\n"
        "2. **Paste** it into the box at the bottom.\n"
        "3. Press **Check this code** and see the result.\n\n*Or paste any code of your own.*")

    for label, code in EXAMPLES:
        st.markdown(f"**{label}**")
        st.code(code, language="python")

    st.divider()
    pasted = st.text_area("Paste code here", height=170,
                          placeholder="Paste one of the examples above…")
    if st.button("Check this code", type="primary"):
        if not pasted.strip():
            st.warning("Please paste some code first.")
        else:
            try:
                action = Action(f"TRY-{int(time.time())}", "you", "code_pr", as_diff(pasted))
                d = evaluate(action, snippet=True)
                findings = find_findings(as_diff(pasted))
                try:
                    store.save_decision(d)
                except Exception:
                    pass   # saving to the board is best-effort; the result still shows
            except Exception as e:
                st.error("Sorry — something went wrong while checking that. "
                         "Make sure it's plain code, then try again.")
                st.caption(f"Technical detail: {type(e).__name__}")
            else:
                show_verdict(d)
                if findings:
                    st.caption("Flagged line(s):")
                    show_code_with_flags(pasted, findings)

# --------------------------------------------------------------- AI agent
with tab_agent:
    st.subheader("🤖 The AI agent — it investigates, then judges")
    st.markdown(
        "The checks on the *Try it* tab use fixed rules. **This is a real AI agent:** it plans "
        "what to look at, uses tools to read the code and see where it's used, then decides — "
        "catching risks the fixed rules miss.")
    st.markdown("**The change it will inspect** — an access check quietly removed:")
    st.code("- if user.id == doc.owner_id:   # only the owner could edit\n"
            "+ return True                    # now ANYONE can edit", language="python")
    st.caption("The fixed rules rate this low-risk and would let it pass. Watch the agent.")

    if not _agent_ready():
        st.info("The live agent needs a Gemini API key — add it as a Streamlit **secret** "
                "`GEMINI_API_KEY` (or a local `.env`). The rule demo on the other tabs works without it.")
    elif st.button("🔍 Run the AI agent", type="primary"):
        decision, trace, err = None, None, None
        with st.spinner("The agent is investigating…"):
            try:
                from sentinel.agent import investigate
                action = Action("DEMO-authz", "ai-agent", "code_pr", AGENT_DIFF)
                decision, trace = investigate(action, AGENT_REPO)
                try:
                    store.save_decision(decision)
                except Exception:
                    pass
            except Exception as e:
                err = agent_error_message(e)
        if err:
            st.error(err)
        elif decision:
            st.markdown("**How the agent reasoned:**")
            for step in (trace or []):
                st.markdown(f"<div class='step'>{html.escape(step)}</div>", unsafe_allow_html=True)
            show_verdict(decision)
            st.success("The fixed rules missed this — the agent caught it by investigating.")

# --------------------------------------------------------------- Board
with tab_board:
    st.caption("Every check is recorded here, and each AI tool gets a trust score over time.")
    try:
        rows = store.list_all()
    except Exception:
        rows = []
        st.warning("Couldn't load the activity log right now.")
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
    try:
        pend = store.list_pending()
    except Exception:
        pend = []
    if not pend:
        st.success("Nothing waiting.")
    for d in pend:
        with st.container(border=True):
            st.markdown(f"**{d['action_id']}** · from `{d['agent']}` · risk {d['risk']}/3")
            try:
                st.write(", ".join(json.loads(d["reasons"])) if d["reasons"] else "")
            except Exception:
                pass
            a, b, _ = st.columns([1, 1, 6])
            if a.button("✅ Approve", key="a" + d["action_id"]):
                store.set_status(d["action_id"], "approved"); st.rerun()
            if b.button("❌ Reject", key="r" + d["action_id"]):
                store.set_status(d["action_id"], "rejected"); st.rerun()

    st.subheader("Trust scorecard (per AI tool)")
    try:
        st.table([
            {"AI tool": a, "checks": t, "passed": au, "flagged": f, "blocked": bl,
             "flag %": f"{r*100:.0f}%"}
            for a, t, au, f, bl, r in store.scorecard()
        ])
    except Exception:
        st.caption("No scorecard data yet.")

    if st.button("↺ Reset demo data"):
        try:
            seed.seed(reset=True)
        except Exception:
            pass
        st.rerun()

# --------------------------------------------------------------- About
with tab_about:
    st.markdown("""
#### The problem, in one line
AI now writes code faster than people can safely check it. The bottleneck is no longer
*writing* — it's *trust*.

#### What Sentinel does
For every AI-made change it **reads** it, scores the risk, **decides** Pass / Hold / Block,
**records** it for a clear trail, and **scores** each AI tool over time so you know which to trust.

#### Why it matters
About 95% of company AI projects stall — not because the AI is weak, but because no one can
safely review and trust what it produces. Sentinel is the missing safety check.

*Built by Avi Kishore Soni · [GitHub](https://github.com/avisoni729/sentinel)*
""")
