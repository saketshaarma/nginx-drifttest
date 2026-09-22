"""Backend regression tests for Nginx Config Drift Tracker."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nginx-config-tracker.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@driftwatch.io"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


# ------------------- AUTH -------------------

def test_login_bad_creds():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_auth():
    r = requests.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 401


def test_me_ok(client):
    r = client.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


# ------------------- BUSINESSES -------------------

def test_business_crud(client):
    # create
    r = client.post(f"{BASE_URL}/api/businesses",
                    json={"name": "TEST_biz", "description": "d"})
    assert r.status_code == 200
    biz = r.json()
    assert biz["name"] == "TEST_biz"
    bid = biz["id"]

    # list
    r = client.get(f"{BASE_URL}/api/businesses")
    assert r.status_code == 200
    assert any(b["id"] == bid for b in r.json())

    # get
    r = client.get(f"{BASE_URL}/api/businesses/{bid}")
    assert r.status_code == 200

    # node-pair (mapping) create with multiple DC<->DR pairs
    r = client.post(f"{BASE_URL}/api/node-pairs", json={
        "business_id": bid, "name": "TEST_np",
        "folder": "/etc/nginx",
        "ssh_username": "root", "ssh_password": "pw",
        "pairs": [
            {"dc_node": "10.0.0.1", "dr_node": "10.0.0.2", "port_dc": 22, "port_dr": 22},
            {"dc_node": "10.0.1.1", "dr_node": "10.0.1.2", "port_dc": 22, "port_dr": 22},
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    np_id = body["id"]
    assert "ssh_password_enc" not in body
    assert "ssh_password" not in body
    assert len(body["pairs"]) == 2
    assert all(p.get("id") for p in body["pairs"])

    # rejects mapping with no pairs
    r_bad = client.post(f"{BASE_URL}/api/node-pairs", json={
        "business_id": bid, "name": "TEST_np_empty",
        "folder": "/etc/nginx", "ssh_username": "root", "ssh_password": "pw",
        "pairs": [],
    })
    assert r_bad.status_code == 400

    # node-pair list by business
    r = client.get(f"{BASE_URL}/api/node-pairs?business_id={bid}")
    assert r.status_code == 200
    assert any(p["id"] == np_id for p in r.json())

    # node-pair update including modifying pairs list
    r = client.put(f"{BASE_URL}/api/node-pairs/{np_id}",
                   json={"name": "TEST_np2",
                         "pairs": [{"dc_node": "10.9.9.9", "dr_node": "10.9.9.10", "port_dc": 2222, "port_dr": 2222}]})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["name"] == "TEST_np2"
    assert len(updated["pairs"]) == 1
    assert updated["pairs"][0]["dc_node"] == "10.9.9.9"
    assert updated["pairs"][0]["port_dc"] == 2222

    # node-pair delete
    r = client.delete(f"{BASE_URL}/api/node-pairs/{np_id}")
    assert r.status_code == 200

    # cascade delete business
    r = client.delete(f"{BASE_URL}/api/businesses/{bid}")
    assert r.status_code == 200
    r = client.get(f"{BASE_URL}/api/businesses/{bid}")
    assert r.status_code == 404


# ------------------- DEMO SEED / DASHBOARD -------------------

def test_demo_seed_and_dashboard(client):
    r = client.post(f"{BASE_URL}/api/demo/seed")
    assert r.status_code == 200

    r = client.get(f"{BASE_URL}/api/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_businesses"] >= 1
    assert data["total_node_pairs"] >= 1
    assert "recent_runs" in data and "recent_incidents" in data


# ------------------- RUNS / INCIDENTS -------------------

def test_runs_and_incidents(client):
    r = client.get(f"{BASE_URL}/api/runs")
    assert r.status_code == 200
    runs = r.json()
    if runs:
        rid = runs[0]["id"]
        r = client.get(f"{BASE_URL}/api/runs/{rid}")
        assert r.status_code == 200
        assert "files" in r.json() or "logs" in r.json() or "status" in r.json()

    r = client.get(f"{BASE_URL}/api/incidents")
    assert r.status_code == 200
    incidents = r.json()
    if incidents:
        iid = incidents[0]["id"]
        current = incidents[0]["status"]
        new_status = "resolved" if current != "resolved" else "open"
        r = client.put(f"{BASE_URL}/api/incidents/{iid}/status?status={new_status}")
        assert r.status_code == 200
        assert r.json()["status"] == new_status


def test_compare_endpoint_async_returns_running(client):
    # ensure demo mapping exists
    client.post(f"{BASE_URL}/api/demo/seed")
    r = client.get(f"{BASE_URL}/api/node-pairs")
    pairs = r.json()
    if not pairs:
        pytest.skip("no node pairs")
    pid = pairs[0]["id"]
    import time
    t0 = time.time()
    r = client.post(f"{BASE_URL}/api/node-pairs/{pid}/compare")
    elapsed = time.time() - t0
    assert r.status_code == 200, r.text
    body = r.json()
    # Async: should return immediately as running
    assert body["status"] == "running", body
    assert elapsed < 5, f"compare returned in {elapsed}s (not async)"
    run_id = body["id"]

    # runs list is filterable by mapping_id
    r = client.get(f"{BASE_URL}/api/runs?mapping_id={pid}")
    assert r.status_code == 200
    assert any(x["id"] == run_id for x in r.json())

    # eventually completes (will be failed since hosts are fake)
    for _ in range(30):
        time.sleep(2)
        rr = client.get(f"{BASE_URL}/api/runs/{run_id}")
        assert rr.status_code == 200
        if rr.json()["status"] != "running":
            break
    final = client.get(f"{BASE_URL}/api/runs/{run_id}").json()
    assert final["status"] in ("failed", "drift", "synced"), final["status"]


def test_incident_status_invalid_rejected(client):
    r = client.get(f"{BASE_URL}/api/incidents")
    inc = r.json()
    if not inc:
        pytest.skip("no incidents")
    iid = inc[0]["id"]
    r = client.put(f"{BASE_URL}/api/incidents/{iid}/status?status=bogus")
    assert r.status_code == 400
