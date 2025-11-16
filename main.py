from fastapi import FastAPI
from app.db import init_db
from app.routers import admin, clients, auth
from app.routers import tracker, domains, domain_filter, spam_quarantine, spam_content
from dotenv import load_dotenv
import os

load_dotenv()  # this reads .env and sets env vars

app = FastAPI()

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(admin.router, prefix="/admin")
app.include_router(clients.router, prefix="/clients")
app.include_router(auth.router, prefix="/auth")
app.include_router(tracker.router, prefix="/pmg", tags=["pmg"])
app.include_router(domains.router, prefix="/domains", tags=["domains"])
app.include_router(domain_filter.router, prefix="/domain_filter", tags=["domain_filter"])
app.include_router(spam_quarantine.router, prefix="/spam_quarantine", tags=["spam_quarantine"])
app.include_router(spam_content.router, prefix="/spam_content", tags=["spam_content"])