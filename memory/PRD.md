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
- JWT auth (login/register/logout/me/refresh, brute-force lockout, seeded admin). [done]
- Business CRUD. [done]
- **Mapping** model = shared folder + SSH creds + list of **DC↔DR node pairs** (add/remove many); CRUD with encrypted SSH passwords. [done]
- Real paramiko SSH comparison engine (SHA256 + unified diff) comparing every DC↔DR pair; runs **async in background** (endpoint returns a 'running' run instantly, Run Detail polls to completion). [done]
- Scheduled comparisons (APScheduler, per-mapping interval). [done]
- Runs history + Run Detail with **per-pair selector**, diff viewer, file filters, execution log, aggregated summary. [done]
- Mocked Freshdesk incident: **one incident per mapping run** summarizing all drifted DC↔DR pairs; Incidents page with status management. [done]
- Dashboard stats + recent runs/incidents. [done]
- Demo seed (idempotent) — 2-pair mapping (1 drift, 1 identical) for instant AHA. [done]
- Stuck-run reaper on startup; stable React keys for pair rows. [done]
- **Production Docker setup**: backend Dockerfile, multi-stage frontend Dockerfile (nginx serving built SPA + /api proxy), docker-compose (mongo+backend+frontend), .env.example, DEPLOYMENT.md. [done]
- Tested: backend 8/8, all critical frontend flows.

## Backlog
- P1: Real Freshdesk API integration (domain + API key) replacing the mock.
- P1: CSV bulk import of node pairs (matches original script's CSV input).
- P2: Side-by-side diff view toggle; downloadable HTML report per run.
- P2: SSH host-key verification (currently AutoAddPolicy); SSH key-based auth option.
- P2: Email/Slack notification on drift; run trend charts over time.

## Test Credentials
admin@driftwatch.io / admin123
