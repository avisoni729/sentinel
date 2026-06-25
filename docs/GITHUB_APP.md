# Running Sentinel as a GitHub App (inline PR comments)

The App listens for pull requests, scores them, and posts an **inline review**
(comments on the exact risky lines) plus a **commit status** that can block merge.

## What the code does
- `app_server.py` — FastAPI webhook (`POST /webhook`); verifies GitHub's
  signature, then handles `pull_request` events.
- `sentinel/analyze.py` — locates findings to file + line for inline comments.
- `sentinel/github_app.py` — App auth (JWT → installation token), posts the
  review and the commit status.

## One-time setup (needs your GitHub account)
1. **Register the App:** GitHub → Settings → Developer settings → GitHub Apps →
   *New GitHub App*.
   - Webhook URL: your server's public URL + `/webhook`.
   - Webhook secret: pick one (used by `SENTINEL_WEBHOOK_SECRET`).
   - Permissions: Pull requests **Read & write**, Commit statuses **Read & write**,
     Contents **Read**.
   - Subscribe to event: **Pull request**.
   - Generate and download a **private key** (.pem).
2. **Install** the App on your `sentinel` repo (or any repo).
3. **Run the server** (any host with a public URL, e.g. Railway / Render / a VM):
   ```bash
   pip install -r requirements.txt -r requirements-app.txt
   export SENTINEL_APP_ID=<id>
   export SENTINEL_PRIVATE_KEY_PATH=/path/to/key.pem
   export SENTINEL_WEBHOOK_SECRET=<your secret>
   uvicorn app_server:APP --host 0.0.0.0 --port 8000
   ```
4. Open a test PR → Sentinel comments inline and sets the `sentinel` status.

## Note on this build
The server code and auth are written and the signature check is unit-tested, but
the live webhook wasn't exercised here (no registered App + this machine's TLS
proxy). It's ready to run once the App is registered on a clean host.
