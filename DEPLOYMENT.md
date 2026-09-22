# DriftWatch — Deployment Guide

Self-hostable, production-ready stack: **React (nginx) + FastAPI + MongoDB**, all via Docker Compose.

## Architecture

```
Browser ──▶ frontend (nginx :80)  ──/api/──▶ backend (uvicorn :8001) ──▶ mongo :27017
              serves built React SPA         FastAPI app                 database
```

The frontend nginx serves the built React app and reverse-proxies `/api/*` to the
backend, so the browser talks to a **single origin** (auth cookies "just work", no CORS issues).

## Prerequisites
- Docker + Docker Compose v2

## 1. Configure secrets

```bash
cp .env.example .env
```

Generate strong secrets and paste them into `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"          # -> JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # -> ENCRYPTION_KEY
```

Also set `ADMIN_EMAIL` / `ADMIN_PASSWORD` (the admin user is seeded on first boot) and
`FRONTEND_URL` (the public URL users hit, e.g. `https://drift.yourco.com`).

> `ENCRYPTION_KEY` encrypts stored SSH passwords at rest. **Do not change it** after
> data exists, or existing SSH credentials can no longer be decrypted.

## 2. Build & run

```bash
docker compose up -d --build
```

Open **http://localhost:8080** and log in with your `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

## 3. Common commands

```bash
docker compose logs -f backend      # tail backend logs
docker compose logs -f frontend
docker compose down                 # stop
docker compose down -v              # stop + wipe the Mongo volume
docker compose up -d --build        # rebuild after code changes
```

## Running behind HTTPS (recommended for production)
Put a TLS terminator (Caddy, Traefik, or a cloud LB) in front of the `frontend`
service and point it at port 80. Set `FRONTEND_URL` to your `https://` domain.
Auth cookies are `Secure` + `SameSite=None`, so real deployments must be served over HTTPS
(localhost is exempt as browsers treat it as a secure context).

## Hosting the backend on a separate domain (optional)
If you don't want the nginx proxy and prefer the frontend to call the backend directly:
1. Expose the backend (uncomment its `ports:` in `docker-compose.yml`).
2. Set `REACT_APP_BACKEND_URL=https://api.yourco.com` in `.env` and rebuild the frontend.
3. Set `FRONTEND_URL` to the frontend origin so backend CORS allows it.

## Notes
- **Freshdesk integration is currently MOCKED** in `backend/comparison.py`
  (`create_freshdesk_incident`). Swap that function for a real Freshdesk API call and
  supply `FRESHDESK_DOMAIN` / `FRESHDESK_API_KEY` to go live.
- Scheduled comparisons run inside the backend via APScheduler; keep the backend running.
