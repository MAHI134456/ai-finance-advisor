from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

from backend.app.db.database import engine, Base
from backend.app.db.dependencies import get_db
from backend.app.auth.dependencies import get_current_user



from backend.app.models.user import User
from backend.app.models.transaction import Transaction

from backend.app.routes import auth, transaction, analytics

app = FastAPI(
    title="AI Personal Finance Advisor",
    version="0.3.0"
)


Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(transaction.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"message": "API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/db-check")
def db_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}
    

@app.get("/debug-sample")
def debug_sample(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    samples = db.query(Transaction).filter(Transaction.user_id == current_user.id).limit(8).all()
    
    return {
        "user_id": current_user.id,
        "count": len(samples),
        "samples": [
            {
                "date": str(t.date),
                "amount": t.amount,
                "type": t.transaction_type,
                "merchant": t.merchant,
                "category": t.category
            } for t in samples
        ]
    }