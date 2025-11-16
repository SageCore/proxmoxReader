# app/routers/domain_filter.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth_service import client_auth
from app.db import get_db
from app.services import pmg_api
from typing import List

router = APIRouter()

def _matches_receiving_domain(item: dict, domains_set: set) -> bool:
    """
    Only match if the receiving address (to, recipient, rcpt_to, etc.) matches domains_set
    """
    receiving_keys = ["to", "recipient", "rcpt_to", "receiver_address"]
    for k in receiving_keys:
        v = item.get(k)
        if v and isinstance(v, str) and v.lower().split("@")[-1] in domains_set:
            return True
    return False

@router.get("/blocklist")
def filter_blocklist(limit: int = Query(500, le=5000), user=Depends(client_auth)):
    """
    Returns tracker entries NOT belonging to the client's assigned domains (blocked domains)
    """
    client_id = user["client_id"]
    db = get_db()
    rows = db.execute("SELECT domain FROM domains WHERE client_id = ?", (client_id,)).fetchall()
    client_domains = set(r["domain"].lower() for r in rows)
    if not client_domains:
        raise HTTPException(status_code=404, detail="No domains assigned to this client")

    try:
        items = pmg_api.get_all_tracker(params={"limit": limit}, limit_per_node=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PMG API error: {e}")

    # filter out items matching client's domains
    filtered = [it for it in items if not _matches_receiving_domain(it, client_domains)]

    # dedupe
    seen = set()
    deduped = []
    for it in filtered:
        uid = it.get("id") or it.get("message_id") or f"{it.get('from')}_{it.get('to')}_{it.get('time', it.get('timestamp',''))}_{it.get('subject','')}"
        if uid in seen:
            continue
        seen.add(uid)
        deduped.append(it)

    return {"count": len(deduped), "items": deduped}


@router.get("/whitelist")
def filter_whitelist(limit: int = Query(500, le=5000), user=Depends(client_auth)):
    """
    Returns tracker entries ONLY belonging to the client's assigned domains (whitelisted domains)
    """
    client_id = user["client_id"]
    db = get_db()
    rows = db.execute("SELECT domain FROM domains WHERE client_id = ?", (client_id,)).fetchall()
    client_domains = set(r["domain"].lower() for r in rows)
    if not client_domains:
        raise HTTPException(status_code=404, detail="No domains assigned to this client")

    try:
        items = pmg_api.get_all_tracker(params={"limit": limit}, limit_per_node=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PMG API error: {e}")

    # keep only items matching client's domains
    filtered = [it for it in items if _matches_receiving_domain(it, client_domains)]

    # dedupe
    seen = set()
    deduped = []
    for it in filtered:
        uid = it.get("id") or it.get("message_id") or f"{it.get('from')}_{it.get('to')}_{it.get('time', it.get('timestamp',''))}_{it.get('subject','')}"
        if uid in seen:
            continue
        seen.add(uid)
        deduped.append(it)

    return {"count": len(deduped), "items": deduped}
