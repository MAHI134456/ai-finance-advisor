from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.user import User
from backend.app.schemas.transaction import TransactionCreate, TransactionResponse
from backend.app.services.transaction import (
    clean_dataframe,
    load_dataframe_from_csv,
    process_csv,
    process_csv_dataframe,
    validate_transaction,
)

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.post("/", response_model=TransactionResponse, status_code=201)
def create_single_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a single transaction."""
    try:
        # Optional: extra validation if needed
        validate_transaction(transaction.dict())

        return process_csv(
            db=db,
            user_id=current_user.id,
            transactions=[transaction.dict()]
        )[0]

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/csv", status_code=201)
async def upload_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and process transactions from CSV file."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    try:
        contents = await file.read()
        df = load_dataframe_from_csv(contents)
        cleaned_df, skipped_rows = clean_dataframe(df)

        if cleaned_df.empty:
            return {
                "message": "No valid transactions found",
                "created": 0,
                "skipped": len(skipped_rows),
                "skipped_rows": skipped_rows[:10],
            }

        created = process_csv_dataframe(
            db=db,
            user_id=current_user.id,
            df=cleaned_df
        )

        return {
            "message": "Transactions imported successfully",
            "created": len(created),
            "skipped": len(skipped_rows),
            "skipped_rows": skipped_rows[:10],
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))