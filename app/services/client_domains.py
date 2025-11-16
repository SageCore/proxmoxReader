# app/services/client_domains.py
from app.db import get_db

def get_domains_for_client(client_id: int):
    conn = get_db()
    cur = conn.execute("SELECT domain FROM domains WHERE client_id = ?", (client_id,))
    rows = cur.fetchall()
    return [row["domain"] for row in rows]
