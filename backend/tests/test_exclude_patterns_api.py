"""End-to-end API tests for node_pairs.exclude_patterns."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nginx-config-tracker.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@driftwatch.io"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def business_id(client):
    r = client.post(f"{BASE_URL}/api/businesses",
                    json={"name": "TEST_excl_biz", "description": "excl"})
    assert r.status_code == 200
    bid = r.json()["id"]
    yield bid
    client.delete(f"{BASE_URL}/api/businesses/{bid}")


def test_create_node_pair_exclude_patterns_stripped(client, business_id):
    """POST stores exclude_patterns with whitespace stripped and empties removed."""
    r = client.post(f"{BASE_URL}/api/node-pairs", json={
        "business_id": business_id,
        "name": "TEST_np_excl",
        "folder": "/etc/nginx",
        "ssh_username": "root",
        "ssh_password": "pw",
        "pairs": [{"dc_node": "10.0.0.1", "dr_node": "10.0.0.2",
                   "port_dc": 22, "port_dr": 22}],
        "exclude_patterns": ["*.log", " ssl/*.key ", ""],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["exclude_patterns"] == ["*.log", "ssl/*.key"]
    np_id = body["id"]

    # GET returns them
    g = client.get(f"{BASE_URL}/api/node-pairs/{np_id}")
    assert g.status_code == 200
    assert g.json()["exclude_patterns"] == ["*.log", "ssl/*.key"]

    # PUT updates and persists
    u = client.put(f"{BASE_URL}/api/node-pairs/{np_id}",
                   json={"exclude_patterns": ["  backup/  ", "conf.d/local.conf", " "]})
    assert u.status_code == 200, u.text
    assert u.json()["exclude_patterns"] == ["backup/", "conf.d/local.conf"]

    # Round-trip via GET after update
    g2 = client.get(f"{BASE_URL}/api/node-pairs/{np_id}")
    assert g2.json()["exclude_patterns"] == ["backup/", "conf.d/local.conf"]

    # cleanup
    client.delete(f"{BASE_URL}/api/node-pairs/{np_id}")


def test_create_without_exclude_patterns_defaults_to_empty(client, business_id):
    r = client.post(f"{BASE_URL}/api/node-pairs", json={
        "business_id": business_id,
        "name": "TEST_np_no_excl",
        "folder": "/etc/nginx",
        "ssh_username": "root",
        "ssh_password": "pw",
        "pairs": [{"dc_node": "10.0.0.3", "dr_node": "10.0.0.4",
                   "port_dc": 22, "port_dr": 22}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("exclude_patterns", []) == []
    client.delete(f"{BASE_URL}/api/node-pairs/{body['id']}")
