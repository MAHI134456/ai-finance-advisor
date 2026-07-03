from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.user import User
from backend.app.services.transaction import process_csv_upload
from backend.app.schemas.transaction import TransactionCreate
from backend.app.models.transaction import Transaction

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.post("/csv", status_code=201)
async def upload_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    print(f"DEBUG: Uploading for user_id = {current_user.id}")
    
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        contents = await file.read()
        result = process_csv_upload(db=db, user_id=current_user.id, contents=contents)
        print(f"DEBUG: Upload result = {result}")
        return result

    except Exception as e:
        print(f"ERROR during upload: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Keep this for single transaction creation (separate from CSV)
@router.post("/", status_code=201)
def create_single_transaction(
    transaction: TransactionCreate,   # Make sure you have this schema
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a single transaction manually."""
    try:
        # You can add validation here if needed
        tx = Transaction(
            user_id=current_user.id,
            merchant=transaction.merchant,
            amount=transaction.amount,
            date=transaction.date,
            category=transaction.category,
            transaction_type=transaction.transaction_type
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return tx
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))