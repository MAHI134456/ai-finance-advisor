from sqlalchemy.orm import Session
from datetime import datetime
import io
import pandas as pd
from typing import List, Dict
from fastapi import HTTPException

from backend.app.models.transaction import Transaction


def load_dataframe_from_csv(contents: bytes) -> pd.DataFrame:
    """Load CSV bytes into pandas DataFrame."""
    try:
        return pd.read_csv(
            io.BytesIO(contents),
            dtype=str,
            encoding="utf-8-sig"
        )
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Clean CSV data and separate valid vs invalid rows."""
    df = df.copy()
    invalid_rows = []

    # Normalize column names
    df.columns = [str(col).strip().lower() for col in df.columns]

    column_map = {
        "merchant": ["merchant", "description", "payee", "narrative", "details", "beneficiary","reference","transaction details"],
        "amount": ["amount", "amt", "value","transaction amount",],
        "date": ["date", "transaction date", "posted date", "booking date", "entry date"],
        "category": ["category", "cat","transaction category"],
        "transaction_type": ["transaction_type", "type", "transaction type", "debit/credit", "debit_credit"]
    }

    mapped = {}
    for canonical, possibles in column_map.items():
        for name in possibles:
            if name in df.columns:
                mapped[canonical] = name
                break
        else:
            mapped[canonical] = None

    if not mapped["merchant"] or not mapped["amount"] or not mapped["date"]:
        raise ValueError("CSV must have merchant, amount, and date columns.")

    # Build clean DataFrame
    clean_df = pd.DataFrame()
    clean_df["merchant"] = df[mapped["merchant"]].astype(str).str.strip()
    clean_df["date_str"] = df[mapped["date"]].astype(str).str.strip()
    clean_df["amount"] = pd.to_numeric(
        df[mapped["amount"]].astype(str).str.replace(r"[$£€,]", "", regex=True),
        errors="coerce"
    )
    clean_df["category"] = df[mapped["category"]].astype(str).str.strip() if mapped["category"] else "Uncategorized"
    clean_df["transaction_type"] = df[mapped["transaction_type"]].astype(str).str.strip() if mapped["transaction_type"] else ""

    valid_mask = pd.Series(True, index=clean_df.index)

    for idx, row in clean_df.iterrows():
        errors = []
        if not row["merchant"].strip():
            errors.append("missing merchant")
        if pd.isna(row["amount"]) or row["amount"] == 0:
            errors.append("invalid amount")
        if not row["date_str"].strip():
            errors.append("missing date")

        # Robust date parsing
        try:
            parsed_date = pd.to_datetime(row["date_str"])
            clean_df.at[idx, "date"] = parsed_date.date()   # Store as date
        except:
            errors.append("invalid date")

        if errors:
            invalid_rows.append({"row": int(idx + 2), "reason": ", ".join(errors)})
            valid_mask.at[idx] = False
        else:
            # Set transaction type
            if not str(row["transaction_type"]).strip():
                clean_df.at[idx, "transaction_type"] = "debit" if row["amount"] < 0 else "credit"

    valid_df = clean_df.loc[valid_mask].copy()
    valid_df["category"] = valid_df["category"].replace({"", "nan"}, "Uncategorized")
    
    return valid_df, invalid_rows


def process_csv_upload(db: Session, user_id: int, contents: bytes) -> Dict:
    """Main function called by your upload endpoint."""
    df, invalid_rows = clean_dataframe(load_dataframe_from_csv(contents))

    if df.empty:
        return {
            "message": "No valid transactions found",
            "created": 0,
            "skipped": len(invalid_rows),
            "skipped_rows": invalid_rows
        }

    # Create Transaction objects
    transactions = []
    for _, row in df.iterrows():
        transaction = Transaction(
            user_id=user_id,
            merchant=row["merchant"],
            amount=float(row["amount"]),
            date=row["date"],                    # date object
            category=row["category"],
            transaction_type=row["transaction_type"]
        )
        transactions.append(transaction)

    # Save to database
    try:
        db.add_all(transactions)
        db.commit()
        return {
            "message": f"Successfully imported {len(transactions)} transactions",
            "created": len(transactions),
            "skipped": len(invalid_rows),
            "skipped_rows": invalid_rows[:20]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))