"""GitHub App glue: webhook auth, app/installation tokens, and posting an
inline review + commit status back to a pull request.

Network calls need a registered App (APP_ID + private key) and connectivity, so
they aren't exercised in local tests; verify_signature() is fully testable.
"""
import hashlib
import hmac
import json
import os
import ssl
import time
import urllib.request

API = "https://api.github.com"

REVIEW_EVENT = {"ALLOW": "APPROVE", "ESCALATE": "REQUEST_CHANGES",
                "BLOCK": "REQUEST_CHANGES"}
STATE = {"ALLOW": "success", "ESCALATE": "failure", "BLOCK": "failure"}


# ----------------------------------------------------------------- webhook auth
def verify_signature(secret, payload_bytes, header_sig):
    """Validate the X-Hub-Signature-256 header GitHub sends with each webhook."""
    if not secret or not header_sig or not header_sig.startswith("sha256="):
        return False
    mac = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + mac, header_sig)


# ----------------------------------------------------------------- app identity
def app_jwt(app_id=None, private_key=None):
    import jwt  # PyJWT
    app_id = app_id or os.environ["SENTINEL_APP_ID"]
    private_key = private_key or _read_key()
    now = int(time.time())
    return jwt.encode({"iat": now - 60, "exp": now + 540, "iss": str(app_id)},
                      private_key, algorithm="RS256")


def _read_key():
    pem = os.environ.get("SENTINEL_PRIVATE_KEY")
    if pem:
        return pem
    path = os.environ["SENTINEL_PRIVATE_KEY_PATH"]
    with open(path, encoding="utf-8") as f:
        return f.read()


def installation_token(installation_id):
    out = _api("POST", f"/app/installations/{installation_id}/access_tokens",
               bearer=app_jwt())
    return json.loads(out)["token"]


# ----------------------------------------------------------------- post results
def post_review(owner, repo, number, decision, findings, token, commit_id=None):
    comments = [{"path": f.path, "line": f.line, "side": "RIGHT", "body": f.message}
                for f in findings]
    head = {"ALLOW": "✅ Sentinel: auto-approved",
            "ESCALATE": "🟠 Sentinel: needs a human",
            "BLOCK": "🛑 Sentinel: blocked"}[decision.verdict]
    body = head + f"  (risk {decision.risk}/3)\n\n" + \
        "\n".join(f"- {r}" for r in decision.reasons)
    payload = {"event": REVIEW_EVENT[decision.verdict], "body": body,
               "comments": comments}
    if commit_id:
        payload["commit_id"] = commit_id
    return _api("POST", f"/repos/{owner}/{repo}/pulls/{number}/reviews",
                token=token, data=payload)


def set_status(owner, repo, sha, decision, token):
    payload = {"state": STATE[decision.verdict], "context": "sentinel",
               "description": f"{decision.verdict} (risk {decision.risk}/3)"}
    return _api("POST", f"/repos/{owner}/{repo}/statuses/{sha}",
                token=token, data=payload)


# ----------------------------------------------------------------- http helper
def _ctx():
    if os.environ.get("SENTINEL_INSECURE") == "1":
        return ssl._create_unverified_context()
    try:
        return ssl.create_default_context()
    except Exception:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())


def _api(method, path, token=None, bearer=None, data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sentinel"}
    if token:
        headers["Authorization"] = f"token {token}"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    body = json.dumps(data).encode() if data is not None else None
    if body:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=_ctx(), timeout=25) as r:
        return r.read().decode("utf-8", "replace")
