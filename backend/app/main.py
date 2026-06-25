from fastapi import FastAPI
from sqlalchemy import text

from backend.app.db.database import (
    engine,
    Base
)

from backend.app.routes import auth
from backend.app.models.user import User
from backend.app.models.transaction import Transaction
from backend.app.routes import transaction

app = FastAPI(
    title="AI Personal Finance Advisor",
    version="0.3.0"
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)

app.include_router(transaction.router)

@app.get("/")
def root():
    return {
        "message": "API is running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

@app.get("/db-check")
def db_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "database": "connected"
    }