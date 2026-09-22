import os
import asyncio
import hashlib
import posixpath
import stat
import difflib
import uuid
from datetime import datetime, timezone

import paramiko

from db import db, decrypt_secret

MAX_DIFF_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ============================================================
# SSH + FILE COMPARISON (adapted from compare_nodes.py)
# ============================================================

def _connect_ssh(host, username, password, port, timeout=20):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host, port=port, username=username, password=password,
        timeout=timeout, banner_timeout=timeout, auth_timeout=timeout,
        look_for_keys=False, allow_agent=False,
    )
    return client


def _sha256_remote_file(sftp, remote_path):
    sha = hashlib.sha256()
    with sftp.open(remote_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def _read_remote_file(sftp, remote_path, max_size):
    with sftp.open(remote_path, "rb") as f:
        data = f.read(max_size + 1)
    if len(data) > max_size:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _scan_remote_directory(sftp, base_folder):
    files = {}

    def walk(current_path):
        entries = sftp.listdir_attr(current_path)
        for entry in entries:
            full_path = posixpath.join(current_path, entry.filename)
            mode = entry.st_mode
            if stat.S_ISDIR(mode):
                walk(full_path)
            elif stat.S_ISREG(mode):
                relative_path = posixpath.relpath(full_path, base_folder)
                files[relative_path] = {
                    "size": entry.st_size,
                    "mtime": entry.st_mtime,
                    "sha256": _sha256_remote_file(sftp, full_path),
                    "remote_path": full_path,
                }

    walk(base_folder)
    return files


def _create_unified_diff(path, content1, content2, node1, node2):
    diff = difflib.unified_diff(
        content1.splitlines(keepends=True),
        content2.splitlines(keepends=True),
        fromfile=f"{node1}/{path}",
        tofile=f"{node2}/{path}",
        lineterm="",
    )
    return "".join(diff)


def _compare_pair_sync(pair):
    """Blocking SSH comparison. Returns a result dict."""
    node1 = pair["node1"]
    node2 = pair["node2"]
    port1 = int(pair.get("port1") or 22)
    port2 = int(pair.get("port2") or 22)
    folder = pair["folder"]
    username = pair["ssh_username"]
    password = decrypt_secret(pair.get("ssh_password_enc", ""))

    result = {"status": "success", "error": None, "files": [], "logs": []}
    client1 = client2 = sftp1 = sftp2 = None
    try:
        result["logs"].append(f"Connecting to {node1}:{port1}")
        client1 = _connect_ssh(node1, username, password, port1)
        sftp1 = client1.open_sftp()

        result["logs"].append(f"Connecting to {node2}:{port2}")
        client2 = _connect_ssh(node2, username, password, port2)
        sftp2 = client2.open_sftp()

        sftp1.stat(folder)
        sftp2.stat(folder)

        result["logs"].append(f"Scanning {node1}:{folder}")
        files1 = _scan_remote_directory(sftp1, folder)
        result["logs"].append(f"{node1}: {len(files1)} files")

        result["logs"].append(f"Scanning {node2}:{folder}")
        files2 = _scan_remote_directory(sftp2, folder)
        result["logs"].append(f"{node2}: {len(files2)} files")

        all_paths = sorted(set(files1.keys()) | set(files2.keys()))
        for path in all_paths:
            f1 = files1.get(path)
            f2 = files2.get(path)
            if f1 and not f2:
                result["files"].append({"path": path, "status": "only-node1",
                                        "node1": f1, "node2": None, "binary": False, "diff": None})
                continue
            if f2 and not f1:
                result["files"].append({"path": path, "status": "only-node2",
                                        "node1": None, "node2": f2, "binary": False, "diff": None})
                continue
            if f1["sha256"] == f2["sha256"]:
                result["files"].append({"path": path, "status": "identical",
                                        "node1": f1, "node2": f2, "binary": False, "diff": None})
                continue
            c1 = _read_remote_file(sftp1, f1["remote_path"], MAX_DIFF_FILE_SIZE)
            c2 = _read_remote_file(sftp2, f2["remote_path"], MAX_DIFF_FILE_SIZE)
            if c1 is None or c2 is None:
                result["files"].append({"path": path, "status": "different",
                                        "node1": f1, "node2": f2, "binary": True, "diff": None})
                continue
            diff = _create_unified_diff(path, c1, c2, node1, node2)
            result["files"].append({"path": path, "status": "different", "node1": f1,
                                    "node2": f2, "binary": False, "diff": diff,
                                    "content1": c1, "content2": c2})
        result["logs"].append("Comparison complete")
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["logs"].append(f"FAILED: {exc}")
    finally:
        for c in (sftp1, sftp2, client1, client2):
            if c:
                try:
                    c.close()
                except Exception:
                    pass
    return result


def _summarize(files):
    summary = {"total": len(files), "identical": 0, "different": 0,
               "only_node1": 0, "only_node2": 0}
    for f in files:
        if f["status"] == "identical":
            summary["identical"] += 1
        elif f["status"] == "different":
            summary["different"] += 1
        elif f["status"] == "only-node1":
            summary["only_node1"] += 1
        elif f["status"] == "only-node2":
            summary["only_node2"] += 1
    summary["drift"] = summary["different"] + summary["only_node1"] + summary["only_node2"]
    return summary


# ============================================================
# FRESHDESK INCIDENT (MOCKED)
# ============================================================

async def create_freshdesk_incident(node_pair, run, summary):
    """MOCKED Freshdesk ticket creation. Stores an incident record locally."""
    incident_id = str(uuid.uuid4())
    ticket_number = f"FD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{incident_id[:6].upper()}"
    drift_files = [f["path"] for f in run["files"] if f["status"] != "identical"]
    subject = f"[Config Drift] {node_pair['name']} — {summary['drift']} file(s) differ"
    description = (
        f"Nginx configuration drift detected between nodes.\n\n"
        f"Business: {node_pair.get('business_name', '')}\n"
        f"Node Pair: {node_pair['name']}\n"
        f"Node 1: {node_pair['node1']}:{node_pair.get('port1', 22)}\n"
        f"Node 2: {node_pair['node2']}:{node_pair.get('port2', 22)}\n"
        f"Folder: {node_pair['folder']}\n\n"
        f"Summary: {summary['different']} different, "
        f"{summary['only_node1']} only on node1, {summary['only_node2']} only on node2.\n\n"
        f"Affected files:\n" + "\n".join(f"  - {p}" for p in drift_files[:50])
    )
    doc = {
        "id": incident_id,
        "run_id": run["id"],
        "node_pair_id": node_pair["id"],
        "business_id": node_pair["business_id"],
        "business_name": node_pair.get("business_name", ""),
        "node_pair_name": node_pair["name"],
        "freshdesk_ticket_id": ticket_number,
        "freshdesk_url": f"https://{os.environ.get('FRESHDESK_DOMAIN', 'demo.freshdesk.com')}/a/tickets/{ticket_number}",
        "subject": subject,
        "description": description,
        "priority": "high",
        "status": "open",
        "drift_count": summary["drift"],
        "mocked": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.incidents.insert_one({**doc})
    return doc


# ============================================================
# RUN EXECUTOR
# ============================================================

async def execute_comparison(node_pair_id: str, triggered_by: str = "manual"):
    pair = await db.node_pairs.find_one({"id": node_pair_id})
    if not pair:
        return None
    business = await db.businesses.find_one({"id": pair["business_id"]})
    pair["business_name"] = business["name"] if business else ""

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    run_doc = {
        "id": run_id,
        "node_pair_id": node_pair_id,
        "node_pair_name": pair["name"],
        "business_id": pair["business_id"],
        "business_name": pair["business_name"],
        "status": "running",
        "triggered_by": triggered_by,
        "started_at": started_at,
        "completed_at": None,
        "error": None,
        "summary": None,
        "files": [],
        "logs": [],
        "incident_id": None,
    }
    await db.runs.insert_one({**run_doc})

    result = await asyncio.to_thread(_compare_pair_sync, pair)

    run_doc["files"] = result["files"]
    run_doc["logs"] = result["logs"]
    run_doc["completed_at"] = datetime.now(timezone.utc).isoformat()

    incident = None
    if result["status"] == "failed":
        run_doc["status"] = "failed"
        run_doc["error"] = result["error"]
        summary = None
    else:
        summary = _summarize(result["files"])
        run_doc["summary"] = summary
        run_doc["status"] = "drift" if summary["drift"] > 0 else "synced"
        if summary["drift"] > 0:
            incident = await create_freshdesk_incident(pair, run_doc, summary)
            run_doc["incident_id"] = incident["id"]

    await db.runs.update_one({"id": run_id}, {"$set": {
        "files": run_doc["files"],
        "logs": run_doc["logs"],
        "completed_at": run_doc["completed_at"],
        "status": run_doc["status"],
        "error": run_doc["error"],
        "summary": run_doc["summary"],
        "incident_id": run_doc["incident_id"],
    }})

    await db.node_pairs.update_one({"id": node_pair_id}, {"$set": {
        "last_run_at": run_doc["completed_at"],
        "last_status": run_doc["status"],
        "last_summary": summary,
    }})

    return run_doc
