"""The agentic risk investigator.

A LangGraph ReAct agent (Gemini) that PLANS what to check, USES TOOLS to gather
evidence, OBSERVES the results, and DECIDES a verdict — instead of one blind call.
Returns a Decision plus a readable trace of every step (for the dashboard / audit).

Live model calls need SENTINEL_LLM=1 + GEMINI_API_KEY and a clean network. The
tools and the parsing are unit-tested offline; the loop runs on the model.
"""
import os
import re

from .models import Decision
from .agent_tools import make_tools

SYSTEM = """You are Sentinel's risk investigator for AI-generated code changes.
Your job: decide whether a change is safe to merge automatically, needs a human,
or must be blocked.

Investigate before you judge. Use the tools to:
- read the code being changed or called,
- search the repo to see where it is used (blast radius),
- check whether tests cover it,
- consult the fast deterministic rules.

Think about *meaning*, not just keywords: e.g. an authorization check replaced
with `if True`, weak crypto, or disabled security are dangerous even if the rules
miss them.

When done, end your final message with exactly one line:
VERDICT=<ALLOW|ESCALATE|BLOCK> | RISK=<0-3> | REASON=<one short sentence>
ALLOW = safe, ESCALATE = a human should review, BLOCK = must not merge."""


def _build_agent(model, repo, diff):
    from langgraph.prebuilt import create_react_agent
    return create_react_agent(model, make_tools(repo, diff))


def _default_model():
    # Uses the google-genai SDK over HTTPS (httpx), which truststore secures even
    # behind an intercepting proxy. 2.5-flash has free-tier quota; 2.0-flash did not.
    from langchain_google_genai import ChatGoogleGenerativeAI
    model = os.environ.get("SENTINEL_LLM_MODEL", "gemini-2.5-flash")
    return ChatGoogleGenerativeAI(model=model, temperature=0)


def investigate(action, repo, model=None):
    """Run the agent. `repo` is {path: file_contents} for the tools to explore."""
    if model is None:
        if os.environ.get("SENTINEL_LLM") != "1" or not os.environ.get("GEMINI_API_KEY"):
            raise RuntimeError("The agent needs SENTINEL_LLM=1 and GEMINI_API_KEY "
                               "(and a network without TLS interception).")
        model = _default_model()

    agent = _build_agent(model, repo, action.diff)
    result = agent.invoke({"messages": [("system", SYSTEM), ("user", action.diff)]})
    messages = result["messages"]
    decision = parse_decision(action, _text(messages[-1].content))
    return decision, build_trace(messages)


def _text(content):
    """Gemini may return content as a string or a list of blocks; flatten it."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, dict):
                out.append(c.get("text") or c.get("content") or "")
        return "\n".join(out)
    return str(content)


def parse_decision(action, text):
    v = re.search(r"VERDICT\s*=\s*(ALLOW|ESCALATE|BLOCK)", text)
    r = re.search(r"RISK\s*=\s*([0-3])", text)
    reason = re.search(r"REASON\s*=\s*(.+)", text)
    return Decision(
        action.id, action.agent,
        int(r.group(1)) if r else 2,
        v.group(1) if v else "ESCALATE",
        [reason.group(1).strip()] if reason else ["agent assessment"],
    )


def build_trace(messages):
    """Turn the agent's messages into a readable plan/act/observe trace."""
    steps = []
    for m in messages:
        calls = getattr(m, "tool_calls", None)
        if calls:
            for c in calls:
                steps.append(f"🔧 used {c['name']}({c.get('args', {})})")
        elif type(m).__name__ == "ToolMessage":
            out = _text(m.content).strip().replace("\n", " ")
            steps.append(f"👁️  saw: {out[:120]}")
        elif type(m).__name__ == "AIMessage" and _text(m.content).strip():
            steps.append(f"💭 {_text(m.content).strip()[:160]}")
    return steps
