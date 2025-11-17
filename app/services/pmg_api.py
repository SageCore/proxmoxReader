# app/services/pmg_api.py
import os
from dotenv import load_dotenv
import requests
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

load_dotenv()

PMG_HOSTS = os.getenv("PMG_HOSTS").split(",")
PMG_USERNAME = os.getenv("PMG_USERNAME")
PMG_PASSWORD = os.getenv("PMG_PASSWORD")
PMG_VERIFY_SSL = os.getenv("PMG_VERIFY_SSL", "false").lower() in ("true", "1", "yes")
REQUEST_TIMEOUT = int(os.getenv("PMG_REQ_TIMEOUT", "20"))

if not PMG_USERNAME or not PMG_PASSWORD:
    raise ValueError("PMG_USERNAME and PMG_PASSWORD must be set in env")

def _base_api_url(host: str) -> str:
    return f"https://{host}/api2/json/"

def login_and_get_session(host: str):
    session = requests.Session()
    session.verify = PMG_VERIFY_SSL

    url = f"https://{host}/api2/json/access/ticket"
    payload = {
        "username": f"{PMG_USERNAME}@pmg",
        "password": PMG_PASSWORD
    }

    resp = session.post(url, data=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    j = resp.json()
    data = j.get("data") or {}

    ticket = data.get("ticket")
    csrf = data.get("CSRFPreventionToken")

    if not ticket:
        raise ValueError("No PMG ticket returned on login")

    # PMG requires PMGAuthCookie to be set manually
    session.cookies.set("PMGAuthCookie", ticket, domain=host.split(':')[0])

    return {"session": session, "csrf": csrf}


def get_nodes(host: str) -> List[str]:
    """
    Fetch node names from a single host using an authenticated session.
    """
    s = login_and_get_session(host)
    session = s["session"]
    csrf = s.get("csrf")

    headers = {}
    if csrf:
        headers["CSRFPreventionToken"] = csrf

    url = _base_api_url(host) + "nodes"
    r = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    data = j.get("data") or []

    nodes = []
    for n in data:
        node_name = n.get("node") or n.get("name")
        if node_name:
            nodes.append(node_name)
    return nodes

def get_tracker_for_node(host: str, node: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Query nodes/{node}/tracker on a specific host.
    """
    s = login_and_get_session(host)
    session = s["session"]
    csrf = s.get("csrf")

    headers = {}
    if csrf:
        headers["CSRFPreventionToken"] = csrf

    url = _base_api_url(host) + f"nodes/{node}/tracker"
    r = session.get(url, headers=headers, params=params or {}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    j = r.json()
    return j.get("data") or []

def get_all_tracker(params: Optional[Dict[str, Any]] = None, limit_per_node: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch tracker data from all nodes across all hosts.
    """
    all_items = []
    errors = []

    for host in PMG_HOSTS:
        try:
            nodes = get_nodes(host)
        except Exception as e:
            errors.append({"host": host, "error": str(e)})
            continue

        for node in nodes:
            try:
                query_params = params if params else None

                items = get_tracker_for_node(host, node, params=query_params)
                for it in items:
                    it["_pmg_host"] = host
                    it["_pmg_node"] = node
                all_items.extend(items)
                time.sleep(0.07)
            except Exception as e:
                errors.append({"host": host, "node": node, "error": str(e)})

    if errors:
        print("PMG fetch errors:", errors)

    return all_items
