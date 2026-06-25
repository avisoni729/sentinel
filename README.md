# 🛡️ Sentinel — a control plane for AI-generated actions

> Before a risky change from an AI tool (Copilot, Cursor, Claude Code…) is let
> through, Sentinel **risk-scores it, decides pass / hold / block, logs it, and
> scores each AI tool's reliability over time.**

**▶ Live demo:** _add your Streamlit Cloud link here_
&nbsp;·&nbsp; **Author:** Avi Kishore Soni

---

## The problem

AI tools are shifting from *suggesting* to *acting* — they merge code, run
migrations, hit APIs. The new bottleneck isn't generating work; it's **trust and
accountability**. Teams have no checkpoint between an AI agent and the systems it
touches, no record of what it did, and no way to know which tools to trust.
Industry reports put ~95% of enterprise GenAI pilots failing on governance and
trust — not model quality.

**Sentinel is the missing checkpoint.**

## It is *not* a code reviewer

A code reviewer asks *"is this code good?"*. Sentinel asks
*"is this AI-made change safe to let through without a human, and which tools can
we trust?"* — three jobs a reviewer never does:

| | |
|---|---|
| **Gate** | decide `ALLOW` / `ESCALATE` (hold for a human) / `BLOCK` |
| **Audit** | append-only log of every decision, attributed to the agent |
| **Appraise** | a per-agent trust scorecard built from the history |

## How it works

```
AI tool's change ──▶  RISK SCORE  ──▶  DECISION  ──▶  AUDIT LOG  ──▶  SCORECARD
(pull request)        rules + LLM      pass/hold/block   (who did what)   (trust per agent)
                                          │
                                     hold ▼
                                   HUMAN approves / rejects
```

- **Rules** (fast, explainable): leaked secrets, sensitive paths (auth/payment/
  infra), file deletions, change size, missing tests.
- **LLM classifier** (optional): a fuzzy risk score from Gemini, opt-in via
  `SENTINEL_LLM=1`. The gate works fully without it.
- **Human in the loop**: `ESCALATE` items wait in a queue until a person
  approves or rejects them; the decision is persisted.

## Run it locally

```bash
pip install -r requirements.txt

python demo.py            # score the sample changes, fill the database
python review.py          # see the pending queue …
python review.py approve PR-104-charge-tweak
python review.py reject  PR-106-auth-bypass

streamlit run dashboard.py   # the visual, clickable dashboard
python -m pytest -q          # tests
```

## What's next (roadmap)

- [ ] Connect to real GitHub pull requests (GitHub App / webhook)
- [ ] Evaluation harness — measure the risk classifier (precision / recall)
- [ ] Connectors beyond code: email, database, deploy actions
- [ ] Policy as config (per-team rules)

## Project layout

```
sentinel/
  models.py      Action + Decision shapes
  rules.py       deterministic risk signals
  classifier.py  optional LLM risk score
  gate.py        combine signals -> decision
  store.py       SQLite: decisions + status + scorecard
  seed.py        load sample data
demo.py          run the gate over samples (CLI)
review.py        human approval queue (CLI)
dashboard.py     Streamlit dashboard (the live demo)
tests/           behaviour tests
```

_MIT licensed._
