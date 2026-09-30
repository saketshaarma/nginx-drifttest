import os
import re
import asyncio
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# Freshdesk built-in codes
PRIORITY = {"low": 1, "medium": 2, "high": 3, "urgent": 4}
STATUS = {"open": 2, "pending": 3, "resolved": 4, "closed": 5}

PLACEHOLDER_KEYS = {"", "mock_key", "change-me", "replace_with_real_key"}
PLACEHOLDER_DOMAINS = {"", "yourcompany.freshdesk.com", "demo.freshdesk.com"}


def _domain() -> str:
    d = os.environ.get("FRESHDESK_DOMAIN", "").strip().rstrip("/")
    return re.sub(r"^https?://", "", d).rstrip("/")


def _api_key() -> str:
    return os.environ.get("FRESHDESK_API_KEY", "").strip()


def is_configured() -> bool:
    """Real Freshdesk is usable only when a real domain + key are set."""
    return (
        _domain().lower() not in PLACEHOLDER_DOMAINS
        and _api_key().lower() not in PLACEHOLDER_KEYS
    )


def _requester_email() -> str:
    return (
        os.environ.get("FRESHDESK_REQUESTER_EMAIL", "").strip()
        or os.environ.get("ADMIN_EMAIL", "").strip()
        or "alerts@driftwatch.local"
    )


def mock_url(ticket_id: str) -> str:
    dom = _domain() or "demo.freshdesk.com"
    return f"https://{dom}/a/tickets/{ticket_id}"


async def create_ticket(subject: str, description: str, priority: str = "high",
                        status: str = "open") -> dict:
    """Create a real Freshdesk ticket. Returns a normalized dict.

    Falls back to a clearly-flagged mock ticket when Freshdesk is not configured
    or the API call fails, so drift tracking never breaks.
    """
    if not is_configured():
        return {"mock": True, "ok": True, "error": None}

    domain = _domain()
    url = f"https://{domain}/api/v2/tickets"
    # Freshdesk treats description as HTML
    html_desc = "<pre>" + (description.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")) + "</pre>"
    payload = {
        "subject": subject,
        "description": html_desc,
        "email": _requester_email(),
        "priority": PRIORITY.get(priority, 3),
        "status": STATUS.get(status, 2),
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(url, json=payload, auth=(_api_key(), "X"),
                                             headers={"Accept": "application/json"})
                except httpx.RequestError as exc:
                    if attempt == 2:
                        return {"mock": True, "ok": False, "error": f"Freshdesk unreachable: {exc}"}
                    await asyncio.sleep(2 ** attempt)
                    continue

                if resp.status_code == 429:
                    retry_after = min(int(resp.headers.get("Retry-After", "5")), 30)
                    if attempt == 2:
                        return {"mock": True, "ok": False, "error": "Freshdesk rate limit exceeded"}
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status_code in (500, 502, 503, 504):
                    if attempt == 2:
                        return {"mock": True, "ok": False, "error": f"Freshdesk error {resp.status_code}"}
                    await asyncio.sleep(2 ** attempt)
                    continue
                if not 200 <= resp.status_code < 300:
                    detail = ""
                    try:
                        detail = str(resp.json())[:300]
                    except Exception:
                        detail = resp.text[:300]
                    return {"mock": True, "ok": False, "error": f"Freshdesk {resp.status_code}: {detail}"}

                data = resp.json()
                ticket_id = data.get("id")
                if ticket_id is None:
                    return {"mock": True, "ok": False, "error": "Freshdesk response missing id"}
                return {
                    "mock": False, "ok": True, "error": None,
                    "ticket_id": str(ticket_id),
                    "url": f"https://{domain}/a/tickets/{ticket_id}",
                }
    except Exception as exc:  # never let ticketing crash a run
        logger.exception("Freshdesk ticket creation failed")
        return {"mock": True, "ok": False, "error": str(exc)}

    return {"mock": True, "ok": False, "error": "Freshdesk request failed"}
