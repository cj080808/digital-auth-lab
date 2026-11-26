# Backend

FastAPI implementation of the REST and WebSocket API described in the repository README.

## Run locally

Use Python 3.11 or newer:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:COOKIE_SECURE = "false"
$env:JWT_SECRET_KEY = "replace-with-a-long-random-secret"
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; OpenAPI docs are at `/docs`.
Set `DATABASE_URL` to select the database. SQLite is used by default. For HTTPS
deployment, configure a trusted TLS certificate at the reverse proxy and keep
`COOKIE_SECURE=true` (the default). Set a stable, private `JWT_SECRET_KEY` in
every deployed environment; without it, a process-random key is used and tokens
will not remain valid after restart.

## Tests

```powershell
python -m pytest
```

REST errors use the `success: false` envelope. Certificate-backed client
identity and message signatures are not enabled in this baseline; certificate
status and message signature status are reported as `notConfigured` and
`unverified`, respectively.
