from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import admin_auth
from app.db import get_db
from pydantic import BaseModel

router = APIRouter()

class DomainCreate(BaseModel):
    domain: str

@router.post("/{client_id}/domains")
def add_domain(client_id: int, payload: DomainCreate, admin=Depends(admin_auth)):
    db = get_db()
    domain = payload.domain.strip().lower()
    
    if not domain:
        raise HTTPException(status_code=400, detail="Empty domain")

    if " " in domain or domain.count(".") < 1:
        raise HTTPException(status_code=400, detail="Invalid domain format")

    r = db.execute(
        "SELECT id FROM clients WHERE id = ?", 
        (client_id,)
    ).fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Client not found")

    try:
        db.execute(
            "INSERT INTO domains (client_id, domain) VALUES (?, ?)", 
            (client_id, domain)
        )
        db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Domain already exists or DB error")

    return {"status": "domain_added", "client_id": client_id, "domain": domain}

@router.get("/{client_id}/domains")
def get_domains(client_id: int, admin=Depends(admin_auth)):
    db = get_db()

    # validate client exists
    r = db.execute(
        "SELECT id FROM clients WHERE id = ?",
        (client_id,)
    ).fetchone()

    if not r:
        raise HTTPException(404, "Client not found")

    rows = db.execute(
        "SELECT id, domain FROM domains WHERE client_id = ?",
        (client_id,)
    ).fetchall()

    return {
        "client_id": client_id,
        "domains": [
            {"id": row["id"], "domain": row["domain"]}
            for row in rows
        ]
    }



# -------------------------------
# NEW: DELETE ROUTE — DELETE SPECIFIC DOMAIN
# -------------------------------
@router.delete("/{client_id}/domains/{domain_id}")
def delete_domain(client_id: int, domain_id: int, admin=Depends(admin_auth)):
    db = get_db()

    # validate domain exists and belongs to client
    r = db.execute(
        "SELECT id FROM domains WHERE id = ? AND client_id = ?",
        (domain_id, client_id)
    ).fetchone()

    if not r:
        raise HTTPException(404, "Domain not found for this client")

    try:
        db.execute(
            "DELETE FROM domains WHERE id = ? AND client_id = ?",
            (domain_id, client_id)
        )
        db.commit()
    except Exception as e:
        print("REAL ERROR:", e)
        raise HTTPException(400, "Error deleting domain")

    return {"status": "domain_deleted", "domain_id": domain_id, "client_id": client_id}