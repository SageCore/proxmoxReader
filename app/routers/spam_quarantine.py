from fastapi import APIRouter, Depends
from app.services.auth_service import client_auth
from app.services import pmg_spam
from typing import Optional
from fastapi import Query
import time

router = APIRouter()

# @router.get("/spam-quarantine")
# def spam_quarantine(
#     user=Depends(client_auth),
#     starttime: Optional[int] = Query(None, description="Unix epoch start time for spam query"),
#     endtime: Optional[int] = Query(None, description="Unix epoch end time for spam query"),
# ):
    
#     client_id = user["client_id"]  # depends on your auth structure
#     items = pmg_spam.get_spam_quarantine(client_id=client_id, starttime=starttime, endtime=endtime)

    
#     return {"count": len(items), "items": items}

@router.get("/spam-quarantine")
def spam_quarantine(
    user=Depends(client_auth),
    starttime: Optional[int] = Query(None, description="Unix epoch start time for spam query", ge=0),
    endtime: Optional[int] = Query(None, description="Unix epoch end time for spam query", ge=0),
    limit: Optional[int] = Query(500, description="Max number of spam messages to return", ge=1)
):
    client_id = user["client_id"]
    now = int(time.time())

    # set defaults if None
    if starttime is None:
        starttime = now - 864000 # ~1000 days ago
    if endtime is None:
        endtime = now

    items = pmg_spam.get_spam_quarantine(client_id=client_id, starttime=starttime, endtime=endtime)

    if limit:
        items = items[:limit]

    return {"count": len(items), "items": items}

