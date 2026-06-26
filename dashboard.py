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
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Spectral:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --paper:#EFE4CB; --canvas:#E6D9BE; --ink:#1F1A14; --muted:#6E5C40;
  --oxblood:#7E2B22; --ochre:#A8741C; --olive:#59663F; --line:#C3B189;
}
.stApp{
  background:
    radial-gradient(130% 90% at 50% -5%, rgba(255,251,238,.55), rgba(255,251,238,0) 55%),
    radial-gradient(55% 40% at 22% 18%, rgba(150,98,46,.11), rgba(150,98,46,0) 60%),
    radial-gradient(50% 45% at 82% 68%, rgba(120,66,28,.12), rgba(120,66,28,0) 60%),
    radial-gradient(45% 40% at 70% 12%, rgba(94,53,24,.08), rgba(94,53,24,0) 60%),
    radial-gradient(150% 130% at 50% 110%, rgba(50,32,16,.20), rgba(50,32,16,0) 60%),
    var(--canvas);
  color:var(--ink);
  font-family:'Spectral', Georgia, serif;
}
.block-container{ box-shadow: inset 0 0 160px rgba(60,40,20,.10); }
h1,h2,h3,h4{ font-family:'Oswald', 'Arial Narrow', sans-serif !important; color:var(--ink);
  font-weight:700; letter-spacing:.5px; }
h1{ text-transform:uppercase; font-size:2.5rem; letter-spacing:1px;
  border-bottom:3px solid var(--oxblood); padding-bottom:.12em; }
h2,h3{ text-transform:uppercase; letter-spacing:.6px; font-weight:600; }
a, a:visited{ color:var(--oxblood) !important; text-decoration:underline dotted; text-underline-offset:3px; }
p, li, label{ font-family:'Spectral', Georgia, serif; }
code, pre, .mono{ font-family:'JetBrains Mono', monospace; }
.muted{ color:var(--muted); }

.tagline{ color:#3a2f20; font-size:1.08rem; line-height:1.5; }

.verdict{ display:inline-block; padding:8px 24px; border-radius:3px;
  font-family:'Oswald', sans-serif; font-weight:700; font-size:1.7rem; text-transform:uppercase;
  color:#F2E8CF; letter-spacing:2px; box-shadow:0 3px 9px #0004, inset 0 1px 0 #ffffff20;
  border:1px solid #00000030; }
.v-pass{ background:linear-gradient(180deg,#67744b,#454f30);}
.v-hold{ background:linear-gradient(180deg,#bd8420,#875c12);}
.v-block{ background:linear-gradient(180deg,#8f352a,#5f1d15);}

.meter{ height:9px; border-radius:2px; background:#00000014; overflow:hidden; margin:11px 0 6px; max-width:300px; }
.meter > span{ display:block; height:100%; }

.reason{ padding:5px 0 5px 14px; border-left:3px solid var(--oxblood); margin:7px 0; }

.step{ background:var(--paper); border:1px dashed var(--line); border-radius:4px;
  padding:8px 12px; margin:7px 0; font-size:.95rem; }

.codeblock{ background:#231A10; color:#E7D9BB; border-radius:5px; padding:14px 12px;
  font-family:'JetBrains Mono', monospace; font-size:.84rem; line-height:1.55; overflow-x:auto;
  border:1px solid #00000040; box-shadow:inset 0 2px 12px #00000050; white-space:pre; }
.codeblock .ln{ color:#7c6843; }
.codeblock .flag{ background:#7E2B2255; border-left:3px solid #C7563F; display:block; padding-left:6px; }

.stButton>button{ background:var(--oxblood); color:#F2E8CF; border:1px solid #00000030;
  border-radius:3px; font-family:'Oswald', sans-serif; font-weight:600; letter-spacing:1px;
  text-transform:uppercase; padding:.45rem 1.2rem; box-shadow:0 2px 7px #0004; }
.stButton>button:hover{ background:#5f1f18; color:#fff; }
[data-testid="stSidebar"]{ background:#DECCA6; border-right:1px solid var(--line); }
[data-testid="stMetricValue"]{ font-family:'Oswald', sans-serif; }
.stTabs [data-baseweb="tab"]{ font-family:'Oswald', sans-serif; text-transform:uppercase; letter-spacing:.5px; }

/* --- lock down Streamlit chrome: no menu / source / fork / edit links --- */
#MainMenu{ visibility:hidden; }
header{ visibility:hidden; height:0; }
footer{ visibility:hidden; height:0; }
[data-testid="stToolbar"]{ display:none !important; }
[data-testid="stDecoration"]{ display:none !important; }
[data-testid="stStatusWidget"]{ display:none !important; }
.block-container{ padding-top:1.1rem !important; }

/* --- top app-bar / brand, weathers to a patina on hover --- */
.appbar{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
  border-bottom:3px solid var(--oxblood); padding-bottom:8px; margin:0 0 10px; }
.brand{ font-family:'Oswald', sans-serif; font-weight:700; font-size:2.6rem;
  text-transform:uppercase; letter-spacing:2px; color:var(--ink); cursor:default;
  transition:color .6s ease, letter-spacing .6s ease, text-shadow .6s ease; }
.brand:hover{ color:#6e4326; letter-spacing:2.6px;
  text-shadow:0 1px 0 #e7c79a66, 0 2px 3px #2a160bcc, -1px 0 1px #5a2e1c55; }
.brand-sub{ font-family:'Spectral', serif; font-style:italic; color:var(--muted); font-size:1.02rem; }

/* --- light, cheap animations --- */
.stButton>button{ transition:transform .15s ease, box-shadow .15s ease, background .15s ease; }
.stButton>button:hover{ transform:translateY(-1px); box-shadow:0 5px 12px #0005; }
.verdict{ animation:stampIn .35s ease-out; }
@keyframes stampIn{ from{ transform:scale(1.12) rotate(-1.5deg); opacity:0; } to{ transform:none; opacity:1; } }
.step{ animation:fadeUp .3s ease-out; }
@keyframes fadeUp{ from{ transform:translateY(4px); opacity:0; } to{ transform:none; opacity:1; } }
</style>
""", unsafe_allow_html=True)

VERDICT_UI = {
    "ALLOW":    ("v-pass",  "PASS",  "Looks safe — no human needed.",                            "#59663F"),
    "ESCALATE": ("v-hold",  "HOLD",  "Risky — a person should review this before it goes live.",  "#A8741C"),
    "BLOCK":    ("v-block", "BLOCK", "Stopped — this should not go through as-is.",               "#7E2B22"),
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
st.markdown(
    "<div class='appbar'><span class='brand'>🛡️ Sentinel</span>"
    "<span class='brand-sub'>a control plane for AI-generated code</span></div>",
    unsafe_allow_html=True)
st.markdown(
    "<p class='tagline'>AI now writes a lot of code on its own — and some of it is risky. "
    "Sentinel reads each AI-made change and decides <b>Pass</b>, <b>Hold</b> (ask a human), "
    "or <b>Block</b>, before it can do harm.</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Sentinel")
    st.markdown("<span class='muted'>A control plane for AI-generated code.</span>",
                unsafe_allow_html=True)
    st.markdown("**How it works**")
    st.markdown("1. Read the change\n2. Score the risk\n3. Pass / Hold / Block\n"
                "4. Log it\n5. Score each AI tool")
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

*Built by Avi Kishore Soni*
""")
