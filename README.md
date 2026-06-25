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

## Scan a real GitHub pull request

```bash
python scan_pr.py pallets flask          # scores the latest PR
python scan_pr.py <owner> <repo> <num>   # a specific PR
```

Public repos need no auth. Example output:

```
[PASS] pallets/flask#6066  (risk 1/3)
   - Medium-size change (42 added lines)
```

## Evaluation (does the scorer actually work?)

Measured against a labeled set of 25 changes (`eval/dataset.json`):

| metric | score |
|---|---|
| Precision | 0.93 |
| Recall | 0.87 |
| F1 | 0.90 |
| Accuracy | 0.88 |

```bash
python eval/run_eval.py
```

**Driven by the eval.** The first version scored P=0.83 / R=0.77. The eval
showed it was missing *semantic* risk (`eval()`, `shell=True`, privilege
escalation) and over-flagging docs/test files by filename. Adding a content-rule
layer and refining the path rules moved it to **P=0.93 / R=0.87** — measured, not
guessed.

**Remaining (honest) errors:** two semantic risks with no signature (an authz
check replaced with `if True`, a password hashed with MD5) and one deliberately
conservative size flag. Those residuals are exactly what the optional LLM
classifier on the roadmap is for.

## Continuous integration

Two GitHub Actions workflows ship with the repo:

- **`ci.yml`** — runs the tests and the evaluation on every push / PR.
- **`sentinel.yml`** — Sentinel gates *itself*: it scans each incoming PR and
  fails the check on `ESCALATE` (needs a human) or `BLOCK` (stop), via exit codes.

Enable the LLM classifier by setting `SENTINEL_LLM=1` and a `GEMINI_API_KEY`
(uses the `google-genai` SDK; rules-only is the default).

## What's next (roadmap)

- [x] Evaluation harness — measure the risk scorer (precision / recall)
- [x] Scan real GitHub pull requests (CLI + CI workflow)
- [x] CI: tests + eval on every push, Sentinel gating its own PRs
- [ ] LLM classifier verified end-to-end (code ready; needs key + connectivity)
- [ ] GitHub App with inline PR comments (richer than the CI check)
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
  github_fetch.py fetch a real PR diff from GitHub
demo.py          run the gate over samples (CLI)
review.py        human approval queue (CLI)
scan_pr.py       scan a real GitHub pull request (CLI)
dashboard.py     Streamlit dashboard (the live demo)
eval/            labeled dataset + precision/recall harness
tests/           behaviour tests
```

_MIT licensed._
