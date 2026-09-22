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

    # node-pair create
    r = client.post(f"{BASE_URL}/api/node-pairs", json={
        "business_id": bid, "name": "TEST_np",
        "node1": "10.0.0.1", "node2": "10.0.0.2",
        "port1": 22, "port2": 22, "folder": "/etc/nginx",
        "ssh_username": "root", "ssh_password": "pw",
    })
    assert r.status_code == 200
    np_id = r.json()["id"]
    assert "ssh_password_enc" not in r.json()
    assert "ssh_password" not in r.json()

    # node-pair list by business
    r = client.get(f"{BASE_URL}/api/node-pairs?business_id={bid}")
    assert r.status_code == 200
    assert any(p["id"] == np_id for p in r.json())

    # node-pair update
    r = client.put(f"{BASE_URL}/api/node-pairs/{np_id}",
                   json={"name": "TEST_np2"})
    assert r.status_code == 200
    assert r.json()["name"] == "TEST_np2"

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


def test_compare_endpoint_graceful_fail(client):
    # find/create a nodepair, trigger compare, expect graceful (unreachable => failed)
    r = client.get(f"{BASE_URL}/api/node-pairs")
    pairs = r.json()
    if not pairs:
        pytest.skip("no node pairs")
    pid = pairs[0]["id"]
    r = client.post(f"{BASE_URL}/api/node-pairs/{pid}/compare")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("failed", "drift", "synced")
