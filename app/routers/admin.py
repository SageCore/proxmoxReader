from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import get_db
from app.utils.security import verify_password, generate_token

router = APIRouter()

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def admin_login(payload: AdminLoginRequest):
    db = get_db()

    row = db.execute(
        "SELECT * FROM admins WHERE username = ?", (payload.username,)
    ).fetchone()

    if not row or not verify_password(payload.password, row["password"]):
        raise HTTPException(401, "Invalid credentials")

    token = generate_token()

    db.execute(
        "UPDATE admins SET token = ? WHERE id = ?", (token, row["id"])
    )
    db.commit()

    return {"token": token}
