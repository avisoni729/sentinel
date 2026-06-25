"""Fetch a real pull request's diff from GitHub (public repos, no auth needed).

TLS notes:
- Normally uses proper certificate verification (system store, then certifi).
- On a machine behind a TLS-intercepting proxy/antivirus where verification is
  broken, set SENTINEL_INSECURE=1 to skip verification for LOCAL testing only.
"""
import json
import os
import ssl
import urllib.request

API = "https://api.github.com"


def _verified_context():
    try:
        return ssl.create_default_context()
    except Exception:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())


def _get(url, accept):
    req = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": "sentinel",
    })
    insecure = os.environ.get("SENTINEL_INSECURE") == "1"
    ctx = ssl._create_unverified_context() if insecure else _verified_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        if not insecure:
            # retry once with certifi in case the system store was the problem
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
                with urllib.request.urlopen(req, context=ctx, timeout=25) as r:
                    return r.read().decode("utf-8", "replace")
            except Exception:
                pass
        raise RuntimeError(
            f"Could not reach GitHub ({e}). If this machine uses a TLS-"
            f"intercepting proxy, set SENTINEL_INSECURE=1 for local testing."
        )


def fetch_pr_diff(owner, repo, number):
    return _get(f"{API}/repos/{owner}/{repo}/pulls/{number}",
                "application/vnd.github.v3.diff")


def latest_pr(owner, repo):
    data = _get(f"{API}/repos/{owner}/{repo}/pulls?state=all&per_page=1",
                "application/vnd.github+json")
    arr = json.loads(data)
    return arr[0]["number"] if arr else None
