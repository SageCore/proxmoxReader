from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.auth_service import admin_auth
from app.utils.security import hash_password, generate_token
from app.db import get_db

router = APIRouter()

class CreateClientRequest(BaseModel):
    name: str

#here a client is created by admin

@router.post("/create")
def create_client(payload: CreateClientRequest, admin=Depends(admin_auth)):
    db = get_db()

    try:
        db.execute("INSERT INTO clients (name) VALUES (?)", (payload.name,))
        db.commit()
    except Exception:
        raise HTTPException(400, "Client already exists")

    return {"status": "client_created"}


class CreateClientUserRequest(BaseModel):
    client_id: int
    username: str
    password: str

@router.delete("/delete/{client_id}")
def delete_client(client_id: int, admin=Depends(admin_auth)):
    db = get_db()

    # ensure client exists
    cur = db.execute("SELECT id FROM clients WHERE id = ?", (client_id,))
    if cur.fetchone() is None:
        raise HTTPException(404, "Client not found")

    # delete client-related items
    db.execute("DELETE FROM client_users WHERE client_id = ?", (client_id,))
    db.execute("DELETE FROM domains WHERE client_id = ?", (client_id,))
    db.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    db.commit()

    return {"status": "client_deleted", "client_id": client_id}


#client user against a client is created by admin and a token is generated for that user
@router.post("/create-user")
def create_client_user(payload: CreateClientUserRequest, admin=Depends(admin_auth)):
    db = get_db()

    hashed = hash_password(payload.password)
    token = generate_token()

    try:
        db.execute("""
            INSERT INTO client_users (client_id, username, password, token, role)
            VALUES (?, ?, ?, ?, 'client')
        """, (payload.client_id, payload.username, hashed, token))
        db.commit()
    except Exception:
        raise HTTPException(400, "Error creating client user")

    return {"status": "user_created", "token": token}

@router.delete("/delete-user/{user_id}")
def delete_client_user(user_id: int, admin=Depends(admin_auth)):
    db = get_db()

    cur = db.execute("SELECT id FROM client_users WHERE id = ?", (user_id,))
    row = cur.fetchone()

    if row is None:
        raise HTTPException(404, "User not found")

    try:
        db.execute("DELETE FROM client_users WHERE id = ?", (user_id,))
        db.commit()

    except Exception as e:
        print("REAL ERROR:", e)
        raise HTTPException(400, "Error creating client user")


    return {"status": "client_user_deleted", "user_id": user_id}

# ============================
# GET ROUTES
# ============================

# Get all clients
@router.get("/get-all")
def get_all_clients(admin=Depends(admin_auth)):
    db = get_db()
    rows = db.execute("SELECT id, name, created_at FROM clients").fetchall()

    return {"clients": [dict(r) for r in rows]}


# Get a single client and all its related data
@router.get("/get/{client_id}")
def get_client(client_id: int, admin=Depends(admin_auth)):
    db = get_db()

    # fetch client
    c = db.execute("SELECT id, name, created_at FROM clients WHERE id = ?", (client_id,)).fetchone()
    if c is None:
        raise HTTPException(404, "Client not found")

    # fetch domains
    domains = db.execute("SELECT id, domain FROM domains WHERE client_id = ?", (client_id,)).fetchall()

    # fetch users
    users = db.execute("""
        SELECT id, username, role, created_at 
        FROM client_users 
        WHERE client_id = ?
    """, (client_id,)).fetchall()

    return {
        "client": dict(c),
        "domains": [dict(d) for d in domains],
        "users": [dict(u) for u in users]
    }


# Get all users under a specific client
@router.get("/users/{client_id}")
def get_client_users(client_id: int, admin=Depends(admin_auth)):
    db = get_db()

    rows = db.execute("""
        SELECT id, username, role, created_at,token
        FROM client_users 
        WHERE client_id = ?
    """, (client_id,)).fetchall()

    return {"client_id": client_id, "users": [dict(r) for r in rows]}


# Get a single user by ID
@router.get("/user/{user_id}")
def get_single_user(user_id: int, admin=Depends(admin_auth)):
    db = get_db()

    row = db.execute("""
        SELECT id, client_id, username, role, created_at,token
        FROM client_users 
        WHERE id = ?
    """, (user_id,)).fetchone()

    if row is None:
        raise HTTPException(404, "User not found")

    return {"user": dict(row)}

