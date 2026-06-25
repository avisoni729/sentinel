"""Sentinel GitHub App — webhook server.

Receives pull_request events, scores the PR, and posts an inline review + a
commit status back. Run:  uvicorn app_server:APP --port 8000
Needs env: SENTINEL_APP_ID, SENTINEL_PRIVATE_KEY(_PATH), SENTINEL_WEBHOOK_SECRET.
"""
import json
import os

from fastapi import FastAPI, Header, HTTPException, Request

from sentinel.models import Action
from sentinel.gate import evaluate
from sentinel.analyze import find_findings
from sentinel import store, github_app
from sentinel.github_fetch import fetch_pr_diff

APP = FastAPI(title="Sentinel GitHub App")
SECRET = os.environ.get("SENTINEL_WEBHOOK_SECRET", "")
HANDLED = {"opened", "synchronize", "reopened"}


@APP.get("/")
def health():
    return {"service": "sentinel", "ok": True}


@APP.post("/webhook")
async def webhook(request: Request,
                  x_hub_signature_256: str = Header(None),
                  x_github_event: str = Header(None)):
    raw = await request.body()
    if not github_app.verify_signature(SECRET, raw, x_hub_signature_256):
        raise HTTPException(401, "invalid signature")
    if x_github_event != "pull_request":
        return {"skipped": x_github_event}

    event = json.loads(raw)
    if event.get("action") not in HANDLED:
        return {"skipped": event.get("action")}

    pr, repo = event["pull_request"], event["repository"]
    owner, name, number = repo["owner"]["login"], repo["name"], pr["number"]
    token = github_app.installation_token(event["installation"]["id"])

    diff = fetch_pr_diff(owner, name, number)
    agent = pr["user"]["login"]
    decision = evaluate(Action(f"{owner}/{name}#{number}", agent, "code_pr", diff))
    store.init()
    store.save_decision(decision)

    findings = find_findings(diff)
    github_app.post_review(owner, name, number, decision, findings, token,
                           commit_id=pr["head"]["sha"])
    github_app.set_status(owner, name, pr["head"]["sha"], decision, token)
    return {"verdict": decision.verdict, "inline_comments": len(findings)}
