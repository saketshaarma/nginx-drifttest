import uuid
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
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
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
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
}
"""

SSL_CONF = """ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
"""


def _unified(path, c1, c2, n1, n2):
    import difflib
    return "".join(difflib.unified_diff(
        c1.splitlines(keepends=True), c2.splitlines(keepends=True),
        fromfile=f"{n1}/{path}", tofile=f"{n2}/{path}", lineterm=""))


async def seed_demo(user_email: str):
    """Create a realistic demo business, node pair and comparison run with drift + incident."""
    existing = await db.businesses.find_one({"name": "Acme Corp (Demo)"})
    if existing:
        run = await db.runs.find_one({"business_id": existing["id"]})
        return {"business_id": existing["id"], "run_id": run["id"] if run else None, "already_seeded": True}
    business_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    await db.businesses.insert_one({
        "id": business_id,
        "name": "Acme Corp (Demo)",
        "description": "Production edge load-balancer fleet — sample data",
        "created_at": now,
        "created_by": user_email,
    })

    pair_id = str(uuid.uuid4())
    n1, n2 = "edge-lb-01.acme.io", "edge-lb-02.acme.io"
    pair = {
        "id": pair_id,
        "business_id": business_id,
        "business_name": "Acme Corp (Demo)",
        "name": "Edge Load Balancer Pair",
        "node1": n1, "node2": n2, "port1": 22, "port2": 22,
        "folder": "/etc/nginx",
        "ssh_username": "deploy",
        "ssh_password_enc": encrypt_secret("demo-not-used"),
        "schedule_enabled": True,
        "schedule_interval_minutes": 60,
        "last_run_at": now, "last_status": "drift", "last_summary": None,
        "created_at": now,
    }
    await db.node_pairs.insert_one({**pair})

    files = [
        {"path": "nginx.conf", "status": "different", "binary": False,
         "node1": {"size": 320, "sha256": "a1"}, "node2": {"size": 320, "sha256": "b2"},
         "diff": _unified("nginx.conf", NGINX_CONF_1, NGINX_CONF_2, n1, n2)},
        {"path": "sites-enabled/default", "status": "different", "binary": False,
         "node1": {"size": 410, "sha256": "c3"}, "node2": {"size": 410, "sha256": "d4"},
         "diff": _unified("sites-enabled/default", SITE_1, SITE_2, n1, n2)},
        {"path": "conf.d/ssl.conf", "status": "only-node1", "binary": False,
         "node1": {"size": 210, "sha256": "e5"}, "node2": None, "diff": None},
        {"path": "mime.types", "status": "identical", "binary": False,
         "node1": {"size": 5231, "sha256": "f6"}, "node2": {"size": 5231, "sha256": "f6"}, "diff": None},
        {"path": "conf.d/gzip.conf", "status": "identical", "binary": False,
         "node1": {"size": 180, "sha256": "a7"}, "node2": {"size": 180, "sha256": "a7"}, "diff": None},
    ]
    summary = {"total": 5, "identical": 2, "different": 2, "only_node1": 1, "only_node2": 0, "drift": 3}

    run_id = str(uuid.uuid4())
    run = {
        "id": run_id, "node_pair_id": pair_id, "node_pair_name": pair["name"],
        "business_id": business_id, "business_name": "Acme Corp (Demo)",
        "status": "drift", "triggered_by": "manual", "started_at": now, "completed_at": now,
        "error": None, "summary": summary, "files": files,
        "logs": [
            f"Connecting to {n1}:22", f"Connecting to {n2}:22",
            f"Scanning {n1}:/etc/nginx", f"{n1}: 5 files",
            f"Scanning {n2}:/etc/nginx", f"{n2}: 4 files",
            "Content diff: nginx.conf", "Content diff: sites-enabled/default",
            "Comparison complete",
        ],
        "incident_id": None,
    }

    incident_id = str(uuid.uuid4())
    ticket = f"FD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{incident_id[:6].upper()}"
    await db.incidents.insert_one({
        "id": incident_id, "run_id": run_id, "node_pair_id": pair_id, "business_id": business_id,
        "business_name": "Acme Corp (Demo)", "node_pair_name": pair["name"],
        "freshdesk_ticket_id": ticket,
        "freshdesk_url": f"https://demo.freshdesk.com/a/tickets/{ticket}",
        "subject": "[Config Drift] Edge Load Balancer Pair — 3 file(s) differ",
        "description": (
            "Nginx configuration drift detected between nodes.\n\n"
            "Business: Acme Corp (Demo)\nNode Pair: Edge Load Balancer Pair\n"
            f"Node 1: {n1}:22\nNode 2: {n2}:22\nFolder: /etc/nginx\n\n"
            "Summary: 2 different, 1 only on node1, 0 only on node2.\n\n"
            "Affected files:\n  - nginx.conf\n  - sites-enabled/default\n  - conf.d/ssl.conf"
        ),
        "priority": "high", "status": "open", "drift_count": 3, "mocked": True,
        "created_at": now,
    })
    run["incident_id"] = incident_id
    await db.runs.insert_one({**run})
    await db.node_pairs.update_one({"id": pair_id}, {"$set": {"last_summary": summary}})

    return {"business_id": business_id, "run_id": run_id, "incident_id": incident_id}
