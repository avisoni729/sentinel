# Sentinel — Progress Log

A brief running log of decisions and build steps, so you can revisit and prep.
Newest entries at the bottom.

---

## Phase 0 — Idea & direction (decided)

**What we're building:** Sentinel — a human-in-the-loop control plane for AI
*actions*. Before a risky AI action runs, it risk-scores it, decides
allow / block / send-to-human, logs everything (audit), and scores each agent's
reliability over time (appraisal).

**Why this and not the others:** researched the frontier. Key findings —
- ~95% of GenAI pilots fail on governance/trust, not model quality.
- "Agent sprawl" is the new shadow IT; human judgment is the new bottleneck.
- The manager/governance layer for AI actions isn't built yet (open lane).

**Not a code reviewer:** a reviewer judges code *quality*; Sentinel makes a
*decision* (gate), keeps a *record* (audit), and *scores the agent* (appraise).

**MVP grounding:** start with Git/PRs (clear checkpoint, easy demo). Architecture
stays connector-based so email / DB / deploy plug in later.

**Status:** 70-75% convinced — building a working slice to judge on evidence.

---

## Phase 1 — MVP core (in progress)

Goal: a runnable demo that gates sample code changes and prints a scorecard.

Steps taken:
1. Created project `D:\claude\sentinel`.
2. Built the package:
   - `models.py` — Action + Decision data shapes.
   - `rules.py` — deterministic risk signals (secrets, sensitive paths,
     deletions, change size, missing tests).
   - `classifier.py` — optional Gemini risk score; falls back to offline.
   - `gate.py` — combine rules + LLM -> ALLOW / ESCALATE / BLOCK.
   - `audit.py` — append-only JSONL log, attributed per agent.
   - `appraise.py` — per-agent trust scorecard from the log.
3. Wrote 6 sample diffs (`samples/samples.json`): 3 safe, 2 risky, 1 secret.
4. `demo.py` — runs the gate over all samples, prints verdicts + scorecard.

Ran the demo: correctly PASSED 3 safe changes, HELD the payment + auth changes,
BLOCKED the hardcoded secret. Scorecard printed per agent. Core works.

---

## Phase 2 — Human approval + storage + dashboard (done)

- Replaced the flat JSONL log with a single SQLite store (`store.py`):
  every decision + its status (auto-approved / pending / blocked /
  approved / rejected). Deleted old `audit.py` + `appraise.py` (kept it neat).
- `review.py` — the human-in-the-loop CLI: list the pending queue, approve or
  reject an action; the decision persists.
- `dashboard.py` — Streamlit view (metrics, pending-approval buttons, scorecard,
  audit log) for the portfolio screen-recording.
- Added a project permission allowlist so routine commands stop prompting.

Verified end to end: 3 auto-passed, secret BLOCKED, payment change approved by a
human, auth bypass rejected by a human — all remembered in the DB.

### What still remains (the real build)
1. Wire the LLM risk classifier properly (newer `google-genai` lib + fix the
   local SSL cert issue) so fuzzy risk judgment works, not just rules.
2. Build a small eval set and measure the classifier (precision/recall on
   "risky") — this is the make-or-break credibility piece.
3. Connect to real GitHub PRs (GitHub App / webhook) instead of sample diffs.
4. Tests, README polish, a 2-min demo video, public repo.
5. Later: connectors beyond code (email / DB / deploy).

## How to run (quick reference for myself)
    cd D:\claude\sentinel
    python demo.py                       # score the samples, fill the DB
    python review.py                     # see pending, then:
    python review.py approve <id>
    python review.py reject  <id>
    streamlit run dashboard.py           # visual dashboard (needs: pip install streamlit)
