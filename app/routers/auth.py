from fastapi import APIRouter, Header, HTTPException
from app.db import get_db

router = APIRouter()

@router.get("/validate")
def validate_client(token: str = Header(None)):
    if not token:
        raise HTTPException(401, "Missing token")

    db = get_db()
    row = db.execute("SELECT id, client_id FROM client_users WHERE token = ?", (token,)).fetchone()

    if not row:
        raise HTTPException(403, "Invalid token")

    return {"user_id": row["id"], "client_id": row["client_id"]}
