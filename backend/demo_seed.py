import uuid
import difflib
from datetime import datetime, timezone

from db import db, encrypt_secret

NGINX_CONF_1 = """user www-data;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
"""

NGINX_CONF_2 = """user www-data;
worker_processes auto;
pid /run/nginx.pid;

events {
    worker_connections 4096;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    keepalive_timeout 30;
    gzip on;
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
"""

SITE_1 = """upstream api_backend {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name app.acme.io;

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
    }
}
"""

SITE_2 = """upstream api_backend {
    server 127.0.0.1:9002;
}

server {
    listen 80;
    server_name app.acme.io;

    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
    }
}
"""


def _diff(path, c1, c2, n1, n2):
    return "".join(difflib.unified_diff(
        c1.splitlines(keepends=True), c2.splitlines(keepends=True),
        fromfile=f"{n1}/{path}", tofile=f"{n2}/{path}", lineterm=""))


def _drift_files(dc, dr):
    return [
        {"path": "nginx.conf", "status": "different", "binary": False,
         "dc": {"size": 320, "sha256": "a1"}, "dr": {"size": 320, "sha256": "b2"},
         "diff": _diff("nginx.conf", NGINX_CONF_1, NGINX_CONF_2, dc, dr)},
        {"path": "sites-enabled/default", "status": "different", "binary": False,
         "dc": {"size": 210, "sha256": "c3"}, "dr": {"size": 210, "sha256": "d4"},
         "diff": _diff("sites-enabled/default", SITE_1, SITE_2, dc, dr)},
        {"path": "conf.d/ssl.conf", "status": "only-dc", "binary": False,
         "dc": {"size": 210, "sha256": "e5"}, "dr": None, "diff": None},
        {"path": "mime.types", "status": "identical", "binary": False,
         "dc": {"size": 5231, "sha256": "f6"}, "dr": {"size": 5231, "sha256": "f6"}, "diff": None},
    ]


def _identical_files():
    return [
        {"path": "nginx.conf", "status": "identical", "binary": False,
         "dc": {"size": 320, "sha256": "z9"}, "dr": {"size": 320, "sha256": "z9"}, "diff": None},
        {"path": "mime.types", "status": "identical", "binary": False,
         "dc": {"size": 5231, "sha256": "f6"}, "dr": {"size": 5231, "sha256": "f6"}, "diff": None},
    ]


def _summ(files):
    s = {"total": len(files), "identical": 0, "different": 0, "only_dc": 0, "only_dr": 0}
    for f in files:
        k = {"identical": "identical", "different": "different", "only-dc": "only_dc", "only-dr": "only_dr"}[f["status"]]
        s[k] += 1
    s["drift"] = s["different"] + s["only_dc"] + s["only_dr"]
    return s


async def seed_demo(user_email: str):
    """Create a realistic demo business, DC↔DR mapping and comparison run with drift + incident."""
    existing = await db.businesses.find_one({"name": "Acme Corp (Demo)"})
    if existing:
        run = await db.runs.find_one({"business_id": existing["id"]})
        return {"business_id": existing["id"], "run_id": run["id"] if run else None, "already_seeded": True}

    business_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.businesses.insert_one({
        "id": business_id, "name": "Acme Corp (Demo)",
        "description": "Production edge fleet — DC/DR nginx nodes (sample data)",
        "created_at": now, "created_by": user_email,
    })

    p1_id, p2_id = str(uuid.uuid4()), str(uuid.uuid4())
    dc1, dr1 = "dc-lb-01.acme.io", "dr-lb-01.acme.io"
    dc2, dr2 = "dc-lb-02.acme.io", "dr-lb-02.acme.io"
    mapping_id = str(uuid.uuid4())
    mapping = {
        "id": mapping_id, "business_id": business_id, "business_name": "Acme Corp (Demo)",
        "name": "Edge Load Balancer Fleet", "folder": "/etc/nginx",
        "ssh_username": "deploy", "ssh_password_enc": encrypt_secret("demo-not-used"),
        "pairs": [
            {"id": p1_id, "dc_node": dc1, "dr_node": dr1, "port_dc": 22, "port_dr": 22},
            {"id": p2_id, "dc_node": dc2, "dr_node": dr2, "port_dc": 22, "port_dr": 22},
        ],
        "schedule_enabled": True, "schedule_interval_minutes": 60,
        "last_run_at": now, "last_status": "drift", "last_summary": None,
        "created_at": now,
    }
    await db.node_pairs.insert_one({**mapping})

    pair1 = {"pair_id": p1_id, "dc_node": dc1, "dr_node": dr1, "port_dc": 22, "port_dr": 22,
             "status": "drift", "error": None, "files": _drift_files(dc1, dr1), "logs":
             [f"Connecting DC {dc1}:22", f"Connecting DR {dr1}:22", "Content diff: nginx.conf", "Comparison complete"]}
    pair1["summary"] = _summ(pair1["files"])
    pair2 = {"pair_id": p2_id, "dc_node": dc2, "dr_node": dr2, "port_dc": 22, "port_dr": 22,
             "status": "identical", "error": None, "files": _identical_files(), "logs":
             [f"Connecting DC {dc2}:22", f"Connecting DR {dr2}:22", "Comparison complete"]}
    pair2["summary"] = _summ(pair2["files"])

    agg = {"total": 0, "identical": 0, "different": 0, "only_dc": 0, "only_dr": 0, "drift": 0,
           "pairs_total": 2, "pairs_drifted": 1, "pairs_failed": 0, "pairs_synced": 1}
    for p in (pair1, pair2):
        for k in ("total", "identical", "different", "only_dc", "only_dr", "drift"):
            agg[k] += p["summary"][k]

    run_id = str(uuid.uuid4())
    run = {
        "id": run_id, "mapping_id": mapping_id, "mapping_name": mapping["name"],
        "business_id": business_id, "business_name": "Acme Corp (Demo)",
        "status": "drift", "triggered_by": "manual", "started_at": now, "completed_at": now,
        "error": None, "summary": agg, "pairs": [pair1, pair2], "incident_id": None,
    }

    incident_id = str(uuid.uuid4())
    ticket = f"FD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{incident_id[:6].upper()}"
    await db.incidents.insert_one({
        "id": incident_id, "run_id": run_id, "mapping_id": mapping_id, "business_id": business_id,
        "business_name": "Acme Corp (Demo)", "mapping_name": mapping["name"],
        "freshdesk_ticket_id": ticket,
        "freshdesk_url": f"https://demo.freshdesk.com/a/tickets/{ticket}",
        "subject": "[Config Drift] Edge Load Balancer Fleet — 1 DC↔DR pair(s) drifted",
        "description": (
            "Nginx configuration drift detected between DC and DR nodes.\n\n"
            "Business: Acme Corp (Demo)\nMapping: Edge Load Balancer Fleet\nConfig folder: /etc/nginx\n\n"
            "1 of 2 DC↔DR pair(s) drifted (2 different, 1 only on DC, 0 only on DR).\n\n"
            f"Drifted pairs:\n  • {dc1}  ↔  {dr1}  —  3 file(s) differ\n"
            "      - nginx.conf\n      - sites-enabled/default\n      - conf.d/ssl.conf"
        ),
        "priority": "high", "status": "open", "drift_count": agg["drift"], "mocked": True,
        "created_at": now,
    })
    run["incident_id"] = incident_id
    await db.runs.insert_one({**run})
    await db.node_pairs.update_one({"id": mapping_id}, {"$set": {"last_summary": agg}})

    return {"business_id": business_id, "run_id": run_id, "incident_id": incident_id}
