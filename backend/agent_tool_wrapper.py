"""
agent_tool_wrapper.py - Bridge between Online MAS Orchestrators and Offline Edge Databases.

Allows LLM Orchestrator agents (LangChain, CrewAI, LangGraph, or custom OpenAI/Gemini function calling)
to securely query offline SMS edge nodes via Cloudflare tunnel, Ngrok, or local LAN.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("resq.offline_tool")

# Environment configuration with safe defaults
RESQ_OFFLINE_BRIDGE_URL = os.getenv("RESQ_OFFLINE_BRIDGE_URL", "http://127.0.0.1:8000")
RESQ_MAS_API_KEY = os.getenv("RESQ_MAS_API_KEY", "resq-mas-bridge-secret-2026")

# ---------------------------------------------------------------------------
# Core Tool Functions
# ---------------------------------------------------------------------------

def check_offline_bridge_health(
    bridge_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    Checks connection health to the offline edge bridge.

    Args:
        bridge_url: URL to the edge bridge (defaults to $RESQ_OFFLINE_BRIDGE_URL)
        api_key: Secret bearer token (defaults to $RESQ_MAS_API_KEY)
        timeout: HTTP timeout in seconds

    Returns:
        Dict with status, latency, and bridge health details
    """
    url = (bridge_url or RESQ_OFFLINE_BRIDGE_URL).rstrip("/")
    token = api_key or RESQ_MAS_API_KEY

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    try:
        resp = requests.get(f"{url}/health", headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return {"status": "connected", "details": resp.json()}
        return {"status": "degraded", "code": resp.status_code, "text": resp.text[:200]}
    except requests.exceptions.RequestException as e:
        return {"status": "unreachable", "error": str(e)}


def query_offline_database_json(
    bridge_url: Optional[str] = None,
    api_key: Optional[str] = None,
    limit: int = 20,
    since: Optional[str] = None,
    hazard_type: Optional[str] = None,
    urgency: Optional[str] = None,
    timeout: float = 10.0
) -> List[Dict[str, Any]]:
    """
    Queries the offline field SQLite database and returns the raw parsed SMS records as a JSON list.

    Returns:
        List[Dict[str, Any]]: List of dictionary records parsed from offline edge SMS.
    """
    url = (bridge_url or RESQ_OFFLINE_BRIDGE_URL).rstrip("/")
    token = api_key or RESQ_MAS_API_KEY

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload: Dict[str, Any] = {"limit": limit}
    if since:
        payload["since"] = since
    if hazard_type:
        payload["hazard_type"] = hazard_type
    if urgency:
        payload["urgency"] = urgency

    try:
        resp = requests.post(f"{url}/api/query-offline", json=payload, headers=headers, timeout=timeout)
        if resp.status_code in (404, 405):
            resp = requests.get(f"{url}/api/query-offline", params=payload, headers=headers, timeout=timeout)

        if resp.status_code != 200:
            logger.error("Error from offline bridge (%s): %s", resp.status_code, resp.text)
            return []

        data = resp.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("records", data.get("results", data.get("data", [])))
        return []
    except requests.exceptions.RequestException as e:
        logger.error("Failed to query offline bridge: %s", e)
        return []


def query_offline_database(
    bridge_url: Optional[str] = None,
    api_key: Optional[str] = None,
    limit: int = 20,
    since: Optional[str] = None,
    hazard_type: Optional[str] = None,
    urgency: Optional[str] = None,
    timeout: float = 10.0
) -> str:
    """
    Queries the offline field SQLite database for parsed SMS ground reports.

    Returns a clean Markdown table suitable for injecting directly into LLM prompts.
    """
    url = (bridge_url or RESQ_OFFLINE_BRIDGE_URL).rstrip("/")
    token = api_key or RESQ_MAS_API_KEY

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload: Dict[str, Any] = {"limit": limit}
    if since:
        payload["since"] = since
    if hazard_type:
        payload["hazard_type"] = hazard_type
    if urgency:
        payload["urgency"] = urgency

    try:
        # Try POST /api/query-offline
        resp = requests.post(f"{url}/api/query-offline", json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 404 or resp.status_code == 405:
            # Fallback to GET /api/query-offline with query parameters
            resp = requests.get(f"{url}/api/query-offline", params=payload, headers=headers, timeout=timeout)

        if resp.status_code != 200:
            return f"❌ Error querying offline database (HTTP {resp.status_code}): {resp.text[:300]}"

        data = resp.json()
        records: List[Dict[str, Any]] = []

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("records", data.get("results", data.get("data", [])))

        if not records:
            return "ℹ️ No offline ground records found matching the criteria."

        # Format as Markdown table for LLM agent reasoning
        lines = [
            f"### 📡 Offline Field Database Reports ({len(records)} records)",
            "",
            "| ID | Type | Urgency | Status | Coordinates | People | Summary | Timestamp |",
            "|---|---|---|---|---|---|---|---|"
        ]

        for rec in records:
            rec_id = rec.get("id") or rec.get("record_id") or rec.get("sms_id") or "N/A"
            em_type = rec.get("emergency_type") or rec.get("hazard") or "UNKNOWN"
            prio = rec.get("urgency") or rec.get("priority") or "HIGH"
            status = rec.get("victim_status") or rec.get("status") or "REPORTED"
            lat = rec.get("lat") or rec.get("latitude") or "0.0"
            lng = rec.get("lng") or rec.get("longitude") or "0.0"
            coords = f"{lat}, {lng}"
            people = rec.get("trapped_count") or rec.get("injured_count") or rec.get("count") or "1"
            raw_text = (rec.get("raw_text") or rec.get("message") or rec.get("instructions") or "").replace("|", "-").replace("\n", " ")
            summary = (raw_text[:45] + "...") if len(raw_text) > 45 else raw_text
            ts = rec.get("timestamp") or rec.get("created_at") or "Recent"

            lines.append(f"| {rec_id} | {em_type} | {prio} | {status} | `{coords}` | {people} | {summary} | {ts} |")

        return "\n".join(lines)

    except requests.exceptions.RequestException as e:
        return f"❌ Failed to reach offline database at {url}: {str(e)}"


# ---------------------------------------------------------------------------
# Function Calling Schema (OpenAI / Gemini / Tool Calling)
# ---------------------------------------------------------------------------

OFFLINE_DB_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_offline_database",
        "description": "Fetch ground-truth SMS emergency reports, victim coordinates, and trapped counts from the offline field edge node.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of reports to retrieve (default: 20)",
                    "default": 20
                },
                "hazard_type": {
                    "type": "string",
                    "description": "Filter by emergency type, e.g. FLOOD, COLLAPSE, FIRE, MEDICAL, LANDSLIDE"
                },
                "urgency": {
                    "type": "string",
                    "description": "Filter by urgency level: CRITICAL, HIGH, MEDIUM, LOW"
                },
                "since": {
                    "type": "string",
                    "description": "ISO timestamp to only retrieve reports received after this time"
                }
            },
            "required": []
        }
    }
}


# ---------------------------------------------------------------------------
# LangChain / LangGraph & CrewAI Tool Compatibility
# ---------------------------------------------------------------------------

try:
    from langchain_core.tools import tool

    @tool
    def offline_database_tool(
        limit: int = 20,
        hazard_type: Optional[str] = None,
        urgency: Optional[str] = None
    ) -> str:
        """
        Query the offline field database to retrieve real-time SMS disaster reports,
        trapped victim counts, and GPS coordinates from ground edge devices.
        """
        return query_offline_database(
            limit=limit,
            hazard_type=hazard_type,
            urgency=urgency
        )

except ImportError:
    # Fallback if langchain_core is not installed in current environment
    class _OfflineDatabaseToolCallable:
        name = "offline_database_tool"
        description = "Query the offline field database for SMS disaster reports, coordinates, and victim status."

        def __call__(self, *args, **kwargs):
            return query_offline_database(*args, **kwargs)

        def run(self, *args, **kwargs):
            return query_offline_database(*args, **kwargs)

    offline_database_tool = _OfflineDatabaseToolCallable()


if __name__ == "__main__":
    print(f"[*] Testing connection to: {RESQ_OFFLINE_BRIDGE_URL}")
    health = check_offline_bridge_health()
    print("[*] Health response:", json.dumps(health, indent=2))
