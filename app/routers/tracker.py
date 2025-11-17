# app/routers/tracker.py
import os
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth_service import client_auth
from app.db import get_db
from app.services import pmg_api

router = APIRouter()

def _normalize_email(s: str) -> str:
    return s.strip().lower()

def _matches_domain(item: dict, domains_set: set) -> bool:
    # defensive checks across multiple likely fields
    keys_to_check = [
        "recipient", "to", "receiver", "rcpt_to", "receiver_address",
        "user", "username", "mailbox", "from", "sender", "sender_address"
    ]
    domain_keys = ["receiver_domain", "rcpt_domain", "domain", "maildomain"]
    for k in keys_to_check:
        v = item.get(k)
        if not v or not isinstance(v, str):
            continue
        lv = v.lower()
        # direct mailbox check
        for d in domains_set:
            if lv.endswith("@" + d):
                return True
            if lv == d:
                return True
    for k in domain_keys:
        v = item.get(k)
        if not v:
            continue
        if isinstance(v, str) and v.lower() in domains_set:
            return True
    return False

@router.get("/tracking")
def get_tracking(
    starttime: int = Query(..., description="Unix start time"),
    endtime: int = Query(..., description="Unix end time"),
    user=Depends(client_auth)):
    """
    Returns tracking center entries belonging to the authenticated client's domains.
    - limit: max items to request per node (default 500)
    """
    client_id = user["client_id"]
    db = get_db()
    rows = db.execute("SELECT domain FROM domains WHERE client_id = ?", (client_id,)).fetchall()
    domains = [r["domain"] for r in rows]
    if not domains:
        raise HTTPException(status_code=404, detail="No domains assigned to this client")
    domains_set = set(d.lower() for d in domains)

    # fetch all tracker items across configured hosts and nodes
    try:
        items = pmg_api.get_all_tracker(params={
            "starttime": starttime,
            "endtime": endtime
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PMG API error: {e}")

    # filter items by domain
    filtered = [it for it in items if _matches_domain(it, domains_set)]

    # dedupe — use unique fields where possible
    seen = set()
    deduped = []
    for it in filtered:
        # try common unique fields, else fallback to composite key
        uid = None
        if isinstance(it.get("id"), (str, int)):
            uid = f"id:{it.get('id')}"
        elif it.get("message_id"):
            uid = f"msgid:{it.get('message_id')}"
        else:
            # composite key
            uid = f"{it.get('from')}_{it.get('recipient')}_{it.get('time', it.get('timestamp',''))}_{it.get('subject','')}"
        if uid in seen:
            continue
        seen.add(uid)
        deduped.append(it)

    return {"count": len(deduped), "items": deduped} 

