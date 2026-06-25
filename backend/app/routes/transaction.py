import csv
import io
from datetime import datetime
from typing import List, Optional

from dateutil.parser import parse
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.db.dependencies import get_db
from backend.app.models.transaction import Transaction
from backend.app.models.user import User
from backend.app.schemas.transaction import TransactionCreate, TransactionResponse

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)

@router.post("/", response_model=TransactionResponse, status_code=201)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        new_transaction = Transaction(
        user_id=current_user.id,
        amount=transaction.amount,
        merchant=transaction.merchant,
        date=transaction.date,
        category=transaction.category,
        transaction_type=transaction.transaction_type,
        )

        db.add(new_transaction)

        db.commit()

        db.refresh(new_transaction)

        return new_transaction

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    

@router.post("/csv", status_code=201)
def upload_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    try:
        contents = file.file.read()
        text_stream = io.StringIO(contents.decode("utf-8-sig"))
        reader = csv.DictReader(text_stream)

        if not reader.fieldnames:
            raise HTTPException(
                status_code=400,
                detail="CSV file is empty"
            )

        created_count = 0
        skipped_rows = []

        for row_number, row in enumerate(reader, start=2):
            if not row:
                continue

            if not any((value or "").strip() for value in row.values()):
                continue

            merchant = (row.get("merchant") or row.get("Merchant") or "").strip()
            amount_raw = (row.get("amount") or row.get("Amount") or "").strip()
            date_raw = (row.get("date") or row.get("Date") or "").strip()
            category = (row.get("category") or row.get("Category") or "").strip()
            transaction_type = (
                row.get("transaction_type")
                or row.get("Transaction Type")
                or row.get("type")
                or ""
            ).strip()

            if not all([merchant, amount_raw, date_raw, category, transaction_type]):
                skipped_rows.append(
                    {
                        "row": row_number,
                        "reason": "Missing required values"
                    }
                )
                continue

            try:
                amount = float(amount_raw)
                parsed_date = parse(date_raw)
            except Exception:
                skipped_rows.append(
                    {
                        "row": row_number,
                        "reason": "Invalid amount or date format"
                    }
                )
                continue

            new_transaction = Transaction(
                user_id=current_user.id,
                merchant=merchant,
                amount=amount,
                date=parsed_date,
                category=category,
                transaction_type=transaction_type,
            )
            db.add(new_transaction)
            created_count += 1

        db.commit()

        return {
            "message": "Transactions imported successfully",
            "created": created_count,
            "skipped": len(skipped_rows),
            "skipped_rows": skipped_rows[:10],
        }

    except UnicodeDecodeError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="CSV file must be UTF-8 encoded"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.get("/", response_model=List[TransactionResponse])
def get_transaction(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category: Optional[str] = None,
    transaction_type: Optional[str] = None
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category:
        query = query.filter(Transaction.category == category)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    return query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()