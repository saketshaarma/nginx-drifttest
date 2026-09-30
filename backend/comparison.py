import os
import asyncio
import hashlib
import posixpath
import stat
import difflib
import uuid
from pathlib import PurePosixPath
from datetime import datetime, timezone

import paramiko

import freshdesk
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


def _unified_diff(path, content1, content2, node1, node2):
    diff = difflib.unified_diff(
        content1.splitlines(keepends=True),
        content2.splitlines(keepends=True),
        fromfile=f"{node1}/{path}",
        tofile=f"{node2}/{path}",
        lineterm="",
    )
    return "".join(diff)


def _summarize(files):
    s = {"total": len(files), "identical": 0, "different": 0, "only_dc": 0, "only_dr": 0}
    for f in files:
        if f["status"] == "identical":
            s["identical"] += 1
        elif f["status"] == "different":
            s["different"] += 1
        elif f["status"] == "only-dc":
            s["only_dc"] += 1
        elif f["status"] == "only-dr":
            s["only_dr"] += 1
    s["drift"] = s["different"] + s["only_dc"] + s["only_dr"]
    return s


def _is_excluded(path, patterns):
    if not patterns:
        return False
    pp = PurePosixPath(path)
    for pat in patterns:
        pat = (pat or "").strip()
        if not pat:
            continue
        # directory-prefix or exact-path exclude, e.g. "backup/", "conf.d", "nginx.conf"
        norm = pat.rstrip("/")
        if "*" not in pat and "?" not in pat and (path == norm or path.startswith(norm + "/")):
            return True
        # glob match where '*' does NOT cross '/'; a slash-less pattern matches the basename at any depth
        try:
            if pp.match(pat):
                return True
        except (ValueError, IndexError):
            pass
    return False


def _compare_single(pair, folder, username, password, exclude_patterns=None):
    """Blocking SSH comparison of one DC<->DR pair. Returns a pair result dict."""
    exclude_patterns = exclude_patterns or []
    dc_node = pair["dc_node"]
    dr_node = pair["dr_node"]
    port_dc = int(pair.get("port_dc") or 22)
    port_dr = int(pair.get("port_dr") or 22)

    result = {
        "pair_id": pair["id"], "dc_node": dc_node, "dr_node": dr_node,
        "port_dc": port_dc, "port_dr": port_dr,
        "status": "identical", "error": None, "summary": None, "files": [], "logs": [],
        "excluded": 0,
    }
    c_dc = c_dr = s_dc = s_dr = None
    try:
        result["logs"].append(f"Connecting DC {dc_node}:{port_dc}")
        c_dc = _connect_ssh(dc_node, username, password, port_dc)
        s_dc = c_dc.open_sftp()
        result["logs"].append(f"Connecting DR {dr_node}:{port_dr}")
        c_dr = _connect_ssh(dr_node, username, password, port_dr)
        s_dr = c_dr.open_sftp()

        s_dc.stat(folder)
        s_dr.stat(folder)

        result["logs"].append(f"Scanning DC {dc_node}:{folder}")
        files_dc = _scan_remote_directory(s_dc, folder)
        result["logs"].append(f"DC {dc_node}: {len(files_dc)} files")
        result["logs"].append(f"Scanning DR {dr_node}:{folder}")
        files_dr = _scan_remote_directory(s_dr, folder)
        result["logs"].append(f"DR {dr_node}: {len(files_dr)} files")

        all_paths = sorted(set(files_dc.keys()) | set(files_dr.keys()))
        if exclude_patterns:
            kept = [p for p in all_paths if not _is_excluded(p, exclude_patterns)]
            result["excluded"] = len(all_paths) - len(kept)
            all_paths = kept
            if result["excluded"]:
                result["logs"].append(f"Excluded {result['excluded']} file(s) by pattern")
        for path in all_paths:
            fdc = files_dc.get(path)
            fdr = files_dr.get(path)
            if fdc and not fdr:
                result["files"].append({"path": path, "status": "only-dc", "dc": fdc, "dr": None, "binary": False, "diff": None})
                continue
            if fdr and not fdc:
                result["files"].append({"path": path, "status": "only-dr", "dc": None, "dr": fdr, "binary": False, "diff": None})
                continue
            if fdc["sha256"] == fdr["sha256"]:
                result["files"].append({"path": path, "status": "identical", "dc": fdc, "dr": fdr, "binary": False, "diff": None})
                continue
            cdc = _read_remote_file(s_dc, fdc["remote_path"], MAX_DIFF_FILE_SIZE)
            cdr = _read_remote_file(s_dr, fdr["remote_path"], MAX_DIFF_FILE_SIZE)
            if cdc is None or cdr is None:
                result["files"].append({"path": path, "status": "different", "dc": fdc, "dr": fdr, "binary": True, "diff": None})
                continue
            diff = _unified_diff(path, cdc, cdr, dc_node, dr_node)
            result["files"].append({"path": path, "status": "different", "dc": fdc, "dr": fdr, "binary": False, "diff": diff})

        summary = _summarize(result["files"])
        result["summary"] = summary
        result["status"] = "drift" if summary["drift"] > 0 else "identical"
        result["logs"].append("Comparison complete")
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["logs"].append(f"FAILED: {exc}")
    finally:
        for c in (s_dc, s_dr, c_dc, c_dr):
            if c:
                try:
                    c.close()
                except Exception:
                    pass
    return result


def _compare_mapping_sync(mapping):
    """Compare every DC<->DR pair in a mapping."""
    folder = mapping["folder"]
    username = mapping["ssh_username"]
    password = decrypt_secret(mapping.get("ssh_password_enc", ""))
    exclude_patterns = mapping.get("exclude_patterns", [])
    pairs_out = []
    for pair in mapping.get("pairs", []):
        pairs_out.append(_compare_single(pair, folder, username, password, exclude_patterns))
    return pairs_out


def _aggregate(pairs):
    agg = {"total": 0, "identical": 0, "different": 0, "only_dc": 0, "only_dr": 0, "drift": 0,
           "pairs_total": len(pairs), "pairs_drifted": 0, "pairs_failed": 0, "pairs_synced": 0}
    for p in pairs:
        if p["status"] == "failed":
            agg["pairs_failed"] += 1
            continue
        if p["status"] == "drift":
            agg["pairs_drifted"] += 1
        else:
            agg["pairs_synced"] += 1
        s = p.get("summary") or {}
        for k in ("total", "identical", "different", "only_dc", "only_dr", "drift"):
            agg[k] += s.get(k, 0)
    return agg


# ============================================================
# FRESHDESK INCIDENT (MOCKED) — one per mapping run
# ============================================================

async def create_freshdesk_incident(mapping, run, agg):
    incident_id = str(uuid.uuid4())
    drifted = [p for p in run["pairs"] if p["status"] == "drift"]

    lines = []
    for p in drifted:
        s = p.get("summary") or {}
        changed = [f["path"] for f in p["files"] if f["status"] != "identical"]
        lines.append(f"  • {p['dc_node']}  <->  {p['dr_node']}  —  {s.get('drift', 0)} file(s) differ")
        for c in changed[:20]:
            lines.append(f"      - {c}")

    subject = f"[Config Drift] {mapping['name']} — {agg['pairs_drifted']} DC/DR pair(s) drifted"
    description = (
        "Nginx configuration drift detected between DC and DR nodes.\n\n"
        f"Business: {mapping.get('business_name', '')}\n"
        f"Mapping: {mapping['name']}\n"
        f"Config folder: {mapping['folder']}\n\n"
        f"{agg['pairs_drifted']} of {agg['pairs_total']} DC/DR pair(s) drifted "
        f"({agg['different']} different, {agg['only_dc']} only on DC, {agg['only_dr']} only on DR).\n\n"
        "Drifted pairs:\n" + "\n".join(lines)
    )

    result = await freshdesk.create_ticket(subject, description, priority="high", status="open")

    if not result["mock"]:
        ticket_id = result["ticket_id"]
        ticket_url = result["url"]
    else:
        ticket_id = f"FD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{incident_id[:6].upper()}"
        ticket_url = freshdesk.mock_url(ticket_id)

    doc = {
        "id": incident_id,
        "run_id": run["id"],
        "mapping_id": mapping["id"],
        "business_id": mapping["business_id"],
        "business_name": mapping.get("business_name", ""),
        "mapping_name": mapping["name"],
        "freshdesk_ticket_id": ticket_id,
        "freshdesk_url": ticket_url,
        "subject": subject,
        "description": description,
        "priority": "high",
        "status": "open",
        "drift_count": agg["drift"],
        "mocked": result["mock"],
        "freshdesk_error": result.get("error"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.incidents.insert_one({**doc})
    return doc


# ============================================================
# RUN EXECUTOR
# ============================================================

async def _create_run(mapping, triggered_by):
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run_doc = {
        "id": run_id,
        "mapping_id": mapping["id"],
        "mapping_name": mapping["name"],
        "business_id": mapping["business_id"],
        "business_name": mapping.get("business_name", ""),
        "status": "running",
        "triggered_by": triggered_by,
        "started_at": now,
        "completed_at": None,
        "error": None,
        "summary": None,
        "pairs": [],
        "incident_id": None,
    }
    await db.runs.insert_one({**run_doc})
    return run_doc


async def _run_comparison(mapping, run_doc):
    run_id = run_doc["id"]
    pairs = await asyncio.to_thread(_compare_mapping_sync, mapping)
    agg = _aggregate(pairs)

    run_doc["pairs"] = pairs
    run_doc["summary"] = agg
    run_doc["completed_at"] = datetime.now(timezone.utc).isoformat()

    if agg["pairs_total"] > 0 and agg["pairs_failed"] == agg["pairs_total"]:
        run_doc["status"] = "failed"
        run_doc["error"] = "; ".join(p["error"] for p in pairs if p.get("error"))[:500]
    elif agg["pairs_drifted"] > 0:
        run_doc["status"] = "drift"
    else:
        run_doc["status"] = "synced"

    if agg["pairs_drifted"] > 0:
        incident = await create_freshdesk_incident(mapping, run_doc, agg)
        run_doc["incident_id"] = incident["id"]

    await db.runs.update_one({"id": run_id}, {"$set": {
        "pairs": run_doc["pairs"], "summary": run_doc["summary"],
        "completed_at": run_doc["completed_at"], "status": run_doc["status"],
        "error": run_doc["error"], "incident_id": run_doc["incident_id"],
    }})
    await db.node_pairs.update_one({"id": mapping["id"]}, {"$set": {
        "last_run_at": run_doc["completed_at"], "last_status": run_doc["status"], "last_summary": agg,
    }})
    return run_doc


async def _load_mapping(mapping_id):
    mapping = await db.node_pairs.find_one({"id": mapping_id})
    if not mapping:
        return None
    business = await db.businesses.find_one({"id": mapping["business_id"]})
    mapping["business_name"] = business["name"] if business else ""
    return mapping


async def start_comparison(mapping_id: str, triggered_by: str = "manual"):
    """Create the run and launch the heavy SSH work in the background. Returns the running run doc."""
    mapping = await _load_mapping(mapping_id)
    if not mapping:
        return None
    run_doc = await _create_run(mapping, triggered_by)
    asyncio.create_task(_run_comparison(mapping, dict(run_doc)))
    return run_doc


async def execute_comparison(mapping_id: str, triggered_by: str = "manual"):
    """Synchronous end-to-end run (used by the scheduler)."""
    mapping = await _load_mapping(mapping_id)
    if not mapping:
        return None
    run_doc = await _create_run(mapping, triggered_by)
    return await _run_comparison(mapping, run_doc)
