from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.auth_service import client_auth
from app.services import pmg_api

router = APIRouter()

@router.get("/spam-content")
def spam_content(
    id: str = Query(..., description="Content ID of the quarantined mail"),
    host: str = Query(..., description="PMG host to query"),
    user=Depends(client_auth)
):
    """
    Fetch the full HTML content of a single spam email from PMG.
    The PMG endpoint returns raw HTML, not JSON.
    """
    try:
        # Login to PMG host
        sess_info = pmg_api.login_and_get_session(host)
        session = sess_info["session"]
        csrf = sess_info.get("csrf")

        headers = {}
        if csrf:
            headers["CSRFPreventionToken"] = csrf

        # Request the raw HTML content
        resp = session.get(
            f"https://{host}/api2/htmlmail/quarantine/content",
            params={"id": id},
            headers=headers,
            timeout=pmg_api.REQUEST_TIMEOUT,
            verify=pmg_api.PMG_VERIFY_SSL
        )
        resp.raise_for_status()

        # Return the raw HTML
        content = resp.text
        if not content:
            raise HTTPException(status_code=404, detail=f"No content found for id {id}")

        return {"id": id, "host": host, "content": content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching content for id {id} on host {host}: {e}")
