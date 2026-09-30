# DriftWatch — Nginx Config Drift Tracker & ITSM Incident Center

## Original Problem Statement
User has a Python script (compare_nodes.py) that SSHes into pairs of nginx nodes and compares their config files (recursive SHA256 + unified diff, HTML report). They want a web app that keeps info for these nodes and tracks changes; if config files are not identical, raise an incident to their ITSM tool Freshdesk; dashboard with creation of different Business and Node-pair mappings.

## User Choices
- Connection: Real SSH via paramiko (on-demand + scheduled)
- Freshdesk: MOCKED for now (wire real API later)
- Comparisons: Both manual + scheduled
- Auth: JWT email/password
- Structure: Business -> multiple Node Pairs (node1 + node2 + folder + ports)

## Architecture
- Backend: FastAPI + MongoDB (motor). Modules: server.py (routers), auth.py (JWT httpOnly cookies + bcrypt), comparison.py (paramiko SSH compare adapted from user's script + mocked Freshdesk), scheduler.py (APScheduler AsyncIOScheduler), demo_seed.py, db.py (mongo + Fernet-encrypted SSH passwords).
- Frontend: React + Tailwind + shadcn/ui. Dark DevOps console theme. AuthContext, axios withCredentials.
- Collections: users, businesses, node_pairs, runs, incidents, login_attempts.

## User Personas
- SRE/DevOps engineer managing nginx load-balancer pairs across business units.

## Core Requirements (static)
- Auth-guarded dashboard.
- Businesses CRUD; Node Pair mappings CRUD under each business.
- Trigger SSH comparison (manual) + scheduled comparisons per node pair.
- Store run history with file-level status (identical/different/only-node1/only-node2) + unified diffs.
- Auto-raise (mocked) Freshdesk incident when drift detected.
- Incident management (status open/resolved/closed).

## Implemented (2026-06)
- JWT auth (login/register/logout/me/refresh, brute-force lockout, seeded admin); adaptive cookie flags (HTTPS→Secure/None, HTTP→Lax) for self-hosting; ENCRYPTION_KEY accepts any string (derives a valid Fernet key). [done]
- Business CRUD. [done]
- **Mapping** = shared folder + SSH creds + list of **DC↔DR node pairs** + **exclude_patterns**; CRUD with encrypted SSH passwords. [done]
- **File exclusions**: glob patterns (segment-aware, `*` does not cross `/`; slash-less matches basename at any depth; `dir/` and exact-path excludes). Skipped files reported as `excluded` per pair. [done]
- Real paramiko SSH comparison (SHA256 + unified diff) across every DC↔DR pair; async background run + polling. [done]
- Scheduled comparisons (APScheduler, per-mapping interval). [done]
- **Freshdesk**: real ticket creation via REST API v2 (`POST /api/v2/tickets`, Basic auth key:X, retries on 429/5xx) when FRESHDESK_DOMAIN+FRESHDESK_API_KEY are set; clearly-flagged mock fallback otherwise or on API error; incident stores real ticket id + `/a/tickets/{id}` URL. UI shows MOCKED tag only when mocked. [done]
- Runs history + Run Detail (per-pair selector, diff viewer, filters, logs, aggregated summary). One incident per drifted run. [done]
- Dashboard stats; idempotent demo seed; stuck-run reaper. [done]
- Production Docker (backend + nginx-served frontend + mongo compose, requirements.docker.txt, .env.example, DEPLOYMENT.md). [done]
- Tested: backend 31/31 (100%).

## Backlog
- P1: Real Freshdesk API integration (domain + API key) replacing the mock.
- P1: CSV bulk import of node pairs (matches original script's CSV input).
- P2: Side-by-side diff view toggle; downloadable HTML report per run.
- P2: SSH host-key verification (currently AutoAddPolicy); SSH key-based auth option.
- P2: Email/Slack notification on drift; run trend charts over time.

## Test Credentials
admin@driftwatch.io / admin123
