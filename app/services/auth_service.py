from fastapi import Header, HTTPException
from app.db import get_db

def admin_auth(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing admin token")

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid token format")

    token = authorization.split("Bearer ")[1]

    db = get_db()
    row = db.execute(
        "SELECT id FROM admins WHERE token = ?", (token,)
    ).fetchone()

    if not row:
        raise HTTPException(403, "Invalid admin token")

    return {"admin_id": row["id"]}

def client_auth(token: str = Header(None)):
    if not token:
        raise HTTPException(401, "Missing token")

    db = get_db()
    row = db.execute(
        "SELECT id, client_id FROM client_users WHERE token = ?", (token,)
    ).fetchone()

    if not row:
        raise HTTPException(403, "Invalid token")

    return {"user_id": row["id"], "client_id": row["client_id"]}
