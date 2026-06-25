"""The gate: combine rule signals + optional LLM, decide allow/escalate/block."""
from .models import Action, Decision
from .rules import score_rules
from .classifier import score_llm


def evaluate(action: Action, snippet=False) -> Decision:
    risk, reasons, block = score_rules(action.diff, snippet=snippet)

    llm = score_llm(action.diff)
    if llm:
        lrisk, lreason = llm
        risk = max(risk, lrisk)
        reasons.append(f"AI classifier: {lreason} (risk {lrisk})")

    if block:
        verdict = "BLOCK"
    elif risk >= 2:
        verdict = "ESCALATE"   # needs a human
    else:
        verdict = "ALLOW"

    return Decision(action.id, action.agent, risk, verdict, reasons)
