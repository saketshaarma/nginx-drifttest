"""Unit tests for comparison._is_excluded and freshdesk.create_ticket (mocked httpx).

db.py reads MONGO_URL at import time; we call load_dotenv() before importing modules
so tests run standalone. Env is restored + modules reloaded in teardown.
"""
import os
import sys
import base64
import importlib
import pathlib
import pytest
from dotenv import load_dotenv

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# import after load_dotenv
import comparison  # noqa: E402
import freshdesk  # noqa: E402


# ---------------- _is_excluded ----------------

class TestIsExcluded:
    def test_star_log_excludes_root_and_nested(self):
        assert comparison._is_excluded("access.log", ["*.log"]) is True
        assert comparison._is_excluded("a/b/x.log", ["*.log"]) is True

    def test_ssl_key_glob_only_one_level(self):
        assert comparison._is_excluded("ssl/site.key", ["ssl/*.key"]) is True
        # fnmatch matches '*' greedily across '/' too in Python fnmatch,
        # but the spec here says deeper paths must NOT match "ssl/*.key".
        assert comparison._is_excluded("ssl/deep/site.key", ["ssl/*.key"]) is False

    def test_exact_path_excludes_only_that(self):
        assert comparison._is_excluded("conf.d/local.conf", ["conf.d/local.conf"]) is True
        assert comparison._is_excluded("conf.d/other.conf", ["conf.d/local.conf"]) is False

    def test_directory_prefix(self):
        assert comparison._is_excluded("backup/old.conf", ["backup/"]) is True
        assert comparison._is_excluded("backup/deep/file.conf", ["backup/"]) is True

    def test_unmatched_not_excluded(self):
        assert comparison._is_excluded("nginx.conf", ["*.log", "ssl/*.key"]) is False

    def test_empty_and_whitespace_patterns_ignored(self):
        assert comparison._is_excluded("nginx.conf", ["", "  "]) is False

    def test_no_patterns(self):
        assert comparison._is_excluded("nginx.conf", []) is False
        assert comparison._is_excluded("nginx.conf", None) is False


# ---------------- freshdesk.create_ticket (mocked httpx) ----------------

@pytest.fixture
def freshdesk_real_env(monkeypatch):
    """Configure real Freshdesk env + reload the module."""
    monkeypatch.setenv("FRESHDESK_DOMAIN", "acme.freshdesk.com")
    monkeypatch.setenv("FRESHDESK_API_KEY", "realkey123")
    importlib.reload(freshdesk)
    yield freshdesk
    # teardown: restore .env values and reload
    load_dotenv(BACKEND_DIR / ".env", override=True)
    importlib.reload(freshdesk)


class _FakeResp:
    def __init__(self, status_code, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._json


class _FakeAsyncClient:
    """Captures the POST call so tests can assert on request shape."""
    calls = []
    response_factory = None  # set per-test
    raise_exc = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def post(self, url, json=None, auth=None, headers=None):
        _FakeAsyncClient.calls.append({
            "url": url, "json": json, "auth": auth, "headers": headers,
        })
        if _FakeAsyncClient.raise_exc is not None:
            raise _FakeAsyncClient.raise_exc
        return _FakeAsyncClient.response_factory()


@pytest.fixture(autouse=True)
def reset_fake_client():
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.response_factory = lambda: _FakeResp(201, {"id": 12345})
    _FakeAsyncClient.raise_exc = None
    yield


class TestFreshdeskRealPath:
    def test_is_configured_true_with_real_env(self, freshdesk_real_env):
        assert freshdesk_real_env.is_configured() is True

    @pytest.mark.asyncio
    async def test_create_ticket_success(self, freshdesk_real_env, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient.response_factory = lambda: _FakeResp(201, {"id": 12345})

        result = await freshdesk_real_env.create_ticket(
            subject="Drift subject", description="body <b>&</b>",
            priority="high", status="open",
        )

        assert result["mock"] is False
        assert result["ok"] is True
        assert result["ticket_id"] == "12345"
        assert result["url"] == "https://acme.freshdesk.com/a/tickets/12345"

        assert len(_FakeAsyncClient.calls) == 1
        call = _FakeAsyncClient.calls[0]
        assert call["url"] == "https://acme.freshdesk.com/api/v2/tickets"
        assert call["auth"] == ("realkey123", "X")
        body = call["json"]
        assert body["subject"] == "Drift subject"
        assert "description" in body and isinstance(body["description"], str)
        assert body["email"]  # non-empty
        assert isinstance(body["priority"], int) and body["priority"] == 3
        assert isinstance(body["status"], int) and body["status"] == 2

    @pytest.mark.asyncio
    async def test_create_ticket_401_returns_mock_fallback(self, freshdesk_real_env, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
        _FakeAsyncClient.response_factory = lambda: _FakeResp(401, {"message": "unauthorized"})
        result = await freshdesk_real_env.create_ticket("s", "d")
        assert result["mock"] is True
        assert result["ok"] is False
        assert isinstance(result.get("error"), str) and result["error"]

    @pytest.mark.asyncio
    async def test_create_ticket_network_error_returns_mock_fallback(self, freshdesk_real_env, monkeypatch):
        import httpx
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
        # httpx.RequestError so freshdesk retries then falls back
        _FakeAsyncClient.raise_exc = httpx.RequestError("boom", request=None)
        # short-circuit retry sleep
        import asyncio
        async def _no_sleep(*a, **k):
            return None
        monkeypatch.setattr(asyncio, "sleep", _no_sleep)

        result = await freshdesk_real_env.create_ticket("s", "d")
        assert result["mock"] is True
        assert result["ok"] is False
        assert "Freshdesk unreachable" in (result.get("error") or "")


# ---------------- create_freshdesk_incident mock branch ----------------

class TestCreateIncidentMockBranch:
    @pytest.mark.asyncio
    async def test_mock_incident_has_mocked_true_and_mock_url(self, monkeypatch):
        # Ensure MOCK_KEY -> is_configured False
        monkeypatch.setenv("FRESHDESK_DOMAIN", "yourcompany.freshdesk.com")
        monkeypatch.setenv("FRESHDESK_API_KEY", "MOCK_KEY")
        importlib.reload(freshdesk)
        importlib.reload(comparison)
        assert freshdesk.is_configured() is False

        # Stub db.incidents.insert_one so we don't need mongo
        captured = {}
        class _FakeCollection:
            async def insert_one(self, doc):
                captured["doc"] = doc
                return None
        # comparison references `db` from db module -- patch it
        monkeypatch.setattr(comparison.db, "incidents", _FakeCollection(), raising=False)

        mapping = {
            "id": "m1", "business_id": "b1", "business_name": "Biz",
            "name": "MapX", "folder": "/etc/nginx",
        }
        run = {
            "id": "r1",
            "pairs": [{
                "dc_node": "dc1", "dr_node": "dr1", "status": "drift",
                "summary": {"drift": 1},
                "files": [{"path": "nginx.conf", "status": "different"}],
            }],
        }
        agg = {"pairs_drifted": 1, "pairs_total": 1, "different": 1,
               "only_dc": 0, "only_dr": 0, "drift": 1}

        doc = await comparison.create_freshdesk_incident(mapping, run, agg)

        assert doc["mocked"] is True
        assert doc["freshdesk_ticket_id"].startswith("FD-")
        assert doc["freshdesk_url"].startswith("https://yourcompany.freshdesk.com/a/tickets/FD-")
        assert captured["doc"]["mocked"] is True

        # restore env + modules
        load_dotenv(BACKEND_DIR / ".env", override=True)
        importlib.reload(freshdesk)
        importlib.reload(comparison)
