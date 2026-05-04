from sqlalchemy import text

from fastapi import FastAPI
import os
from backend.app.db.database import engine

app = FastAPI(
    title="AI Personal Finance Advisor",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Personal Finance Advisor API!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/db-check")
def db_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    
    return {"database": "connected"}