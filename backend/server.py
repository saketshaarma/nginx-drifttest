from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, APIRouter, Depends, HTTPException, BackgroundTasks
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import db, encrypt_secret
from auth import auth_router, get_current_user, seed_admin
from comparison import execute_comparison
from scheduler import scheduler, schedule_node_pair, remove_node_pair_job, load_all_schedules, start_scheduler

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Nginx Config Drift Tracker")
api_router = APIRouter(prefix="/api")


# ============================================================
# MODELS
# ============================================================

class BusinessInput(BaseModel):
    name: str
    description: str = ""


class NodePairInput(BaseModel):
    business_id: str
    name: str
    node1: str
    node2: str
    port1: int = 22
    port2: int = 22
    folder: str = "/etc/nginx"
    ssh_username: str
    ssh_password: str = ""
    schedule_enabled: bool = False
    schedule_interval_minutes: int = 60


class NodePairUpdate(BaseModel):
    name: Optional[str] = None
    node1: Optional[str] = None
    node2: Optional[str] = None
    port1: Optional[int] = None
    port2: Optional[int] = None
    folder: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    schedule_enabled: Optional[bool] = None
    schedule_interval_minutes: Optional[int] = None


def clean_node_pair(pair: dict) -> dict:
    pair = {k: v for k, v in pair.items() if k != "_id"}
    pair.pop("ssh_password_enc", None)
    pair["has_credentials"] = True
    return pair


def clean_doc(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "_id"}


# ============================================================
# BUSINESS ROUTES
# ============================================================

@api_router.get("/businesses")
async def list_businesses(user: dict = Depends(get_current_user)):
    businesses = await db.businesses.find().sort("created_at", -1).to_list(1000)
    out = []
    for b in businesses:
        b = clean_doc(b)
        b["node_pair_count"] = await db.node_pairs.count_documents({"business_id": b["id"]})
        out.append(b)
    return out


@api_router.post("/businesses")
async def create_business(payload: BusinessInput, user: dict = Depends(get_current_user)):
    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "description": payload.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["email"],
    }
    await db.businesses.insert_one({**doc})
    return doc


@api_router.get("/businesses/{business_id}")
async def get_business(business_id: str, user: dict = Depends(get_current_user)):
    b = await db.businesses.find_one({"id": business_id})
    if not b:
        raise HTTPException(status_code=404, detail="Business not found")
    return clean_doc(b)


@api_router.put("/businesses/{business_id}")
async def update_business(business_id: str, payload: BusinessInput, user: dict = Depends(get_current_user)):
    res = await db.businesses.update_one({"id": business_id},
                                         {"$set": {"name": payload.name, "description": payload.description}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business not found")
    b = await db.businesses.find_one({"id": business_id})
    return clean_doc(b)


@api_router.delete("/businesses/{business_id}")
async def delete_business(business_id: str, user: dict = Depends(get_current_user)):
    pairs = await db.node_pairs.find({"business_id": business_id}).to_list(1000)
    for p in pairs:
        remove_node_pair_job(p["id"])
    await db.node_pairs.delete_many({"business_id": business_id})
    await db.businesses.delete_one({"id": business_id})
    return {"message": "deleted"}


# ============================================================
# NODE PAIR ROUTES
# ============================================================

@api_router.get("/node-pairs")
async def list_node_pairs(business_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"business_id": business_id} if business_id else {}
    pairs = await db.node_pairs.find(query).sort("created_at", -1).to_list(1000)
    return [clean_node_pair(p) for p in pairs]


@api_router.post("/node-pairs")
async def create_node_pair(payload: NodePairInput, user: dict = Depends(get_current_user)):
    business = await db.businesses.find_one({"id": payload.business_id})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    doc = {
        "id": str(uuid.uuid4()),
        "business_id": payload.business_id,
        "business_name": business["name"],
        "name": payload.name,
        "node1": payload.node1,
        "node2": payload.node2,
        "port1": payload.port1,
        "port2": payload.port2,
        "folder": payload.folder,
        "ssh_username": payload.ssh_username,
        "ssh_password_enc": encrypt_secret(payload.ssh_password),
        "schedule_enabled": payload.schedule_enabled,
        "schedule_interval_minutes": payload.schedule_interval_minutes,
        "last_run_at": None,
        "last_status": None,
        "last_summary": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.node_pairs.insert_one({**doc})
    schedule_node_pair(doc)
    return clean_node_pair(doc)


@api_router.get("/node-pairs/{pair_id}")
async def get_node_pair(pair_id: str, user: dict = Depends(get_current_user)):
    p = await db.node_pairs.find_one({"id": pair_id})
    if not p:
        raise HTTPException(status_code=404, detail="Node pair not found")
    return clean_node_pair(p)


@api_router.put("/node-pairs/{pair_id}")
async def update_node_pair(pair_id: str, payload: NodePairUpdate, user: dict = Depends(get_current_user)):
    p = await db.node_pairs.find_one({"id": pair_id})
    if not p:
        raise HTTPException(status_code=404, detail="Node pair not found")
    updates = {}
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "ssh_password":
            if value:
                updates["ssh_password_enc"] = encrypt_secret(value)
        else:
            updates[key] = value
    if updates:
        await db.node_pairs.update_one({"id": pair_id}, {"$set": updates})
    p = await db.node_pairs.find_one({"id": pair_id})
    schedule_node_pair(p)
    return clean_node_pair(p)


@api_router.delete("/node-pairs/{pair_id}")
async def delete_node_pair(pair_id: str, user: dict = Depends(get_current_user)):
    remove_node_pair_job(pair_id)
    await db.node_pairs.delete_one({"id": pair_id})
    return {"message": "deleted"}


@api_router.post("/node-pairs/{pair_id}/compare")
async def trigger_compare(pair_id: str, user: dict = Depends(get_current_user)):
    p = await db.node_pairs.find_one({"id": pair_id})
    if not p:
        raise HTTPException(status_code=404, detail="Node pair not found")
    run = await execute_comparison(pair_id, triggered_by="manual")
    return clean_doc(run)


# ============================================================
# RUN ROUTES
# ============================================================

@api_router.get("/runs")
async def list_runs(node_pair_id: Optional[str] = None, limit: int = 50, user: dict = Depends(get_current_user)):
    query = {"node_pair_id": node_pair_id} if node_pair_id else {}
    runs = await db.runs.find(query, {"files": 0, "logs": 0}).sort("started_at", -1).to_list(limit)
    return [clean_doc(r) for r in runs]


@api_router.get("/runs/{run_id}")
async def get_run(run_id: str, user: dict = Depends(get_current_user)):
    r = await db.runs.find_one({"id": run_id})
    if not r:
        raise HTTPException(status_code=404, detail="Run not found")
    return clean_doc(r)


# ============================================================
# INCIDENT ROUTES
# ============================================================

@api_router.get("/incidents")
async def list_incidents(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = {"status": status} if status else {}
    incidents = await db.incidents.find(query).sort("created_at", -1).to_list(500)
    return [clean_doc(i) for i in incidents]


@api_router.put("/incidents/{incident_id}/status")
async def update_incident_status(incident_id: str, status: str, user: dict = Depends(get_current_user)):
    if status not in {"open", "resolved", "closed"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    res = await db.incidents.update_one({"id": incident_id}, {"$set": {"status": status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    i = await db.incidents.find_one({"id": incident_id})
    return clean_doc(i)


# ============================================================
# DASHBOARD STATS
# ============================================================

@api_router.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(get_current_user)):
    total_businesses = await db.businesses.count_documents({})
    total_pairs = await db.node_pairs.count_documents({})
    drifted_pairs = await db.node_pairs.count_documents({"last_status": "drift"})
    synced_pairs = await db.node_pairs.count_documents({"last_status": "synced"})
    open_incidents = await db.incidents.count_documents({"status": "open"})
    total_incidents = await db.incidents.count_documents({})
    total_runs = await db.runs.count_documents({})

    recent_runs = await db.runs.find({}, {"files": 0, "logs": 0}).sort("started_at", -1).to_list(8)
    recent_incidents = await db.incidents.find().sort("created_at", -1).to_list(5)

    return {
        "total_businesses": total_businesses,
        "total_node_pairs": total_pairs,
        "drifted_pairs": drifted_pairs,
        "synced_pairs": synced_pairs,
        "open_incidents": open_incidents,
        "total_incidents": total_incidents,
        "total_runs": total_runs,
        "recent_runs": [clean_doc(r) for r in recent_runs],
        "recent_incidents": [clean_doc(i) for i in recent_incidents],
    }


@api_router.post("/demo/seed")
async def demo_seed(user: dict = Depends(get_current_user)):
    from demo_seed import seed_demo
    return await seed_demo(user["email"])


@api_router.get("/")
async def root():
    return {"message": "Nginx Config Drift Tracker API"}


# ============================================================
# APP WIRING
# ============================================================

app.include_router(auth_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await db.users.create_index("email", unique=True)
    await db.node_pairs.create_index("business_id")
    await db.runs.create_index("node_pair_id")
    await db.incidents.create_index("status")
    await seed_admin()
    await load_all_schedules()
    start_scheduler()
    logger.info("Startup complete")


@app.on_event("shutdown")
async def on_shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
