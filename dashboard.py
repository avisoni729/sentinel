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
    pass

st.set_page_config(page_title="Sentinel", page_icon="🛡️", layout="wide")

# --------------------------------------------------------------- theme
st.session_state.setdefault("dark_mode", False)
DARK = st.session_state["dark_mode"]

LIGHT = dict(bg="#F4F7FB", card="#FFFFFF", border="#E2E8F0", ink="#0F172A", text="#334155",
             muted="#64748B", primary="#2563EB", primaryd="#1D4ED8", paneltint="#F8FAFC",
             codebg="#0F172A", codefg="#E2E8F0", pass_="#16A34A", hold="#D97706",
             block="#DC2626", inputbg="#FFFFFF")
DARKP = dict(bg="#0B1220", card="#172033", border="#2A3550", ink="#F1F5F9", text="#CBD5E1",
             muted="#94A3B8", primary="#3B82F6", primaryd="#2563EB", paneltint="#0F1A2E",
             codebg="#0B1120", codefg="#E2E8F0", pass_="#22C55E", hold="#F59E0B",
             block="#EF4444", inputbg="#0F1A2E")

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
.stApp{ background:%(bg)s; color:%(text)s; font-family:'Inter', system-ui, sans-serif; }
.block-container{ padding-top:1.1rem; }
h1,h2,h3,h4{ font-family:'Inter', sans-serif; color:%(ink)s; font-weight:700; letter-spacing:-.2px; }
p,li,label,span{ color:%(text)s; }
a,a:visited{ color:%(primary)s !important; text-decoration:none; }
a:hover{ text-decoration:underline; }
.muted{ color:%(muted)s !important; }

.appbar{ background:%(card)s; border:1px solid %(border)s; border-radius:14px;
  padding:16px 22px; box-shadow:0 1px 3px rgba(15,23,42,.06); }
.appbar .brand{ display:flex; align-items:center; gap:14px; }
.appbar .logo{ font-size:2rem; line-height:1; }
.appbar .name{ font-weight:800; font-size:2.1rem; letter-spacing:-1px; color:%(ink)s; line-height:1; }
.appbar .sub{ color:%(muted)s; margin-top:4px; font-size:1rem; }
.tagline{ color:%(text)s; font-size:1.08rem; line-height:1.55; }

.verdict{ display:inline-block; padding:8px 24px; border-radius:10px; font-weight:800;
  font-size:1.35rem; letter-spacing:.4px; color:#fff; }
.v-pass{ background:%(pass_)s; } .v-hold{ background:%(hold)s; } .v-block{ background:%(block)s; }
.meter{ height:9px; border-radius:6px; background:%(border)s; overflow:hidden; margin:10px 0 6px; max-width:300px; }
.meter>span{ display:block; height:100%%; }
.reason{ padding:6px 0 6px 14px; border-left:3px solid %(primary)s; margin:7px 0; color:%(text)s; }
.step{ background:%(paneltint)s; border:1px solid %(border)s; border-radius:8px; padding:8px 12px; margin:7px 0; color:%(text)s; }

.codeblock{ background:%(codebg)s; color:%(codefg)s; border-radius:10px; padding:14px;
  font-family:'JetBrains Mono', monospace; font-size:.85rem; line-height:1.55; overflow-x:auto;
  white-space:pre; border:1px solid %(border)s; }
.codeblock .ln{ color:#64748B; }
.codeblock .flag{ background:rgba(220,38,38,.22); border-left:3px solid %(block)s; display:block; padding-left:6px; }

.stButton>button{ background:%(primary)s; color:#fff; border:none; border-radius:10px;
  font-weight:700; letter-spacing:.2px; padding:.55rem 1.2rem;
  box-shadow:0 1px 3px rgba(37,99,235,.35); transition:all .15s ease; }
.stButton>button:hover{ background:%(primaryd)s; transform:translateY(-1px); }
.stTextArea textarea{ background:%(inputbg)s; color:%(ink)s; border:1px solid %(border)s; border-radius:10px; }

.stTabs [data-baseweb="tab"]{ font-family:'Inter'; font-weight:600; color:%(muted)s; }
.stTabs [aria-selected="true"]{ color:%(primary)s !important; }
[data-testid="stSidebar"]{ background:%(card)s; border-right:1px solid %(border)s; }
[data-testid="stMetricValue"]{ color:%(ink)s; font-weight:800; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *{ color:%(muted)s !important; }

.feat{ background:%(card)s; border:1px solid %(border)s; border-radius:12px; padding:14px 16px; height:100%%; }
.feat .ic{ font-size:1.3rem; } .feat .t{ font-weight:700; color:%(ink)s; } .feat .d{ color:%(muted)s; font-size:.9rem; }

#MainMenu{visibility:hidden;} header{visibility:hidden; height:0;} footer{visibility:hidden; height:0;}
[data-testid="stToolbar"]{display:none !important;} [data-testid="stDecoration"]{display:none !important;}
[data-testid="stStatusWidget"]{display:none !important;}
</style>"""

st.markdown(CSS % (DARKP if DARK else LIGHT), unsafe_allow_html=True)

VERDICT_UI = {
    "ALLOW":    ("v-pass",  "PASS",  "Looks safe — no human needed."),
    "ESCALATE": ("v-hold",  "HOLD",  "Risky — a person should review this before it goes live."),
    "BLOCK":    ("v-block", "BLOCK", "Stopped — this should not go through as-is."),
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
        "def can_edit(user, doc):\n    if user.id == doc.owner_id:\n        return True\n"
        "    return False\n\ndef delete_doc(user, doc):\n    if can_edit(user, doc):\n        doc.delete()\n"),
}
AGENT_DIFF = (
    "+++ b/src/api/share.py\n@@ -1,3 +1,1 @@ def can_edit(user, doc):\n"
    "-    if user.id == doc.owner_id:\n-        return True\n-    return False\n"
    "+    return True  # allow all\n")


# --------------------------------------------------------------- render helpers
def show_verdict(d):
    cls, word, meaning = VERDICT_UI[d.verdict]
    pct = max(int(d.risk / 3 * 100), 8)
    st.markdown(f"<span class='verdict {cls}'>{word}</span>", unsafe_allow_html=True)
    st.markdown(f"<div class='meter'><span class='{cls}' style='width:{pct}%'></span></div>",
                unsafe_allow_html=True)
    st.markdown(f"**{meaning}** &nbsp;&nbsp; <span class='muted'>risk {d.risk}/3</span>",
                unsafe_allow_html=True)
    st.markdown("**Why:**")
    for r in d.reasons:
        st.markdown(f"<div class='reason'>{html.escape(r)}</div>", unsafe_allow_html=True)


def show_code_with_flags(code, findings):
    flagged = {f.line for f in findings}
    rows = []
    for i, ln in enumerate(code.splitlines() or [code], 1):
        safe = html.escape(ln) if ln.strip() else "&nbsp;"
        cls = "flag" if i in flagged else ""
        rows.append(f"<span class='{cls}'><span class='ln'>{i:>2}</span>  {safe}</span>")
    st.markdown("<div class='codeblock'>" + "\n".join(rows) + "</div>", unsafe_allow_html=True)


def agent_error_message(e):
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
hc1, hc2 = st.columns([6, 1])
with hc1:
    st.markdown(
        "<div class='appbar'><div class='brand'><span class='logo'>🛡️</span>"
        "<div><div class='name'>Sentinel</div>"
        "<div class='sub'>Control plane for AI-generated code</div></div></div></div>",
        unsafe_allow_html=True)
with hc2:
    st.write("")
    st.toggle("☀️ Light" if DARK else "🌙 Dark", key="dark_mode")

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
st.markdown(
    "<p class='tagline'>AI now writes a lot of code on its own — and some of it is risky. "
    "Sentinel reads each AI-made change and decides <b>Pass</b>, <b>Hold</b> (ask a human), "
    "or <b>Block</b>, before it can do harm.</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Sentinel")
    st.markdown("<span class='muted'>A control plane for AI-generated code.</span>", unsafe_allow_html=True)
    st.markdown("**How it works**")
    st.markdown("1. Read the change\n2. Score the risk\n3. Pass / Hold / Block\n4. Log it\n5. Score each AI tool")
    st.markdown("---")
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
    pasted = st.text_area("Paste code here", height=170, placeholder="Paste one of the examples above…")
    if st.button("🛡️  Check this code", type="primary"):
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
                    pass
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
    st.subheader("The AI agent — it investigates, then judges")
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
    elif st.button("🔍  Run the AI agent", type="primary"):
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total checks", len(rows))
    c2.metric("Passed", sum(1 for r in rows if r["status"] == "auto-approved"))
    c3.metric("Waiting on human", sum(1 for r in rows if r["status"] == "pending"))
    c4.metric("Blocked", sum(1 for r in rows if r["status"] == "blocked"))

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
        st.table([{"AI tool": a, "checks": t, "passed": au, "flagged": f, "blocked": bl,
                   "flag %": f"{r*100:.0f}%"} for a, t, au, f, bl, r in store.scorecard()])
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

*Built by Avi Kishore Soni*
""")

# --------------------------------------------------------------- feature strip
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
_feats = [("🛡️", "Smart protection", "Detects risky patterns"),
          ("🧑‍⚖️", "Human in the loop", "Holds risky changes for review"),
          ("⟨⟩", "Language-agnostic", "Pattern checks on any diff"),
          ("⚡", "Fast &amp; reliable", "Instant, deterministic feedback")]
for col, (ic, t, dsc) in zip(st.columns(4), _feats):
    col.markdown(f"<div class='feat'><div class='ic'>{ic}</div>"
                 f"<div class='t'>{t}</div><div class='d'>{dsc}</div></div>", unsafe_allow_html=True)
