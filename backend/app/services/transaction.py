from sqlalchemy.orm import Session
from datetime import datetime
import io
import pandas as pd
from typing import List, Dict, Tuple

from backend.app.models.transaction import Transaction  # Adjust import as needed


def validate_transaction(transaction_data: dict) -> None:
    """Validate a single transaction dict."""
    required_fields = ["merchant", "amount", "date", "category", "transaction_type"]
    
    for field in required_fields:
        if field not in transaction_data:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(transaction_data["merchant"], str):
        raise ValueError("Merchant must be a string")
    if not isinstance(transaction_data["amount"], (int, float)):
        raise ValueError("Amount must be a number")
    if not isinstance(transaction_data["date"], str):
        raise ValueError("Date must be a string")
    if not isinstance(transaction_data["category"], str):
        raise ValueError("Category must be a string")
    if not isinstance(transaction_data["transaction_type"], str):
        raise ValueError("Transaction type must be a string")
    
    # Optional: more validation (e.g., positive amount, valid date, enum for type)
    if transaction_data["amount"] <= 0:
        raise ValueError("Amount must be positive")
    
    try:
        datetime.fromisoformat(transaction_data["date"].replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")


def load_dataframe_from_csv(contents: bytes) -> pd.DataFrame:
    """Load a CSV byte stream into a pandas DataFrame."""
    try:
        return pd.read_csv(
            io.BytesIO(contents),
            dtype=str,
            encoding="utf-8-sig"
        )
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")


def validate_dataframe(df: pd.DataFrame) -> None:
    """Validate a pandas DataFrame from CSV."""
    required_columns = ["merchant", "amount", "date", "category", "transaction_type"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Basic type checks
    if not pd.api.types.is_string_dtype(df["merchant"]):
        raise ValueError("Merchant column must contain strings")
    if not pd.api.types.is_numeric_dtype(df["amount"]):
        raise ValueError("Amount column must contain numbers")
    # Add more checks as needed...


def clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Clean a raw transaction DataFrame and return valid rows with skipped metadata."""
    df = df.copy()
    invalid_rows = []

    df.columns = [str(col).strip().lower() for col in df.columns]

    column_map = {
        "merchant": ["merchant", "description", "payee", "narrative", "transaction description"],
        "amount": ["amount", "amt", "transaction amount", "value", "amount paid", "paid amount"],
        "date": ["date", "transaction date", "posted date", "payment date", "date posted"],
        "category": ["category", "cat", "transaction category", "type"],
        "transaction_type": ["transaction_type", "type", "txn_type", "debit/credit", "dr/cr", "cr/dr"]
    }

    mapped = {}
    for canonical, names in column_map.items():
        for name in names:
            if name in df.columns:
                mapped[canonical] = name
                break
        else:
            mapped[canonical] = None

    if not mapped["merchant"] or not mapped["amount"] or not mapped["date"]:
        raise ValueError("CSV must contain at least merchant, amount, and date columns")

    clean_df = pd.DataFrame()
    clean_df["merchant"] = df[mapped["merchant"]].astype(str).str.strip()
    clean_df["date"] = df[mapped["date"]].astype(str).str.strip()
    clean_df["amount"] = df[mapped["amount"]].astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False).str.replace("£", "", regex=False).str.replace("€", "", regex=False)
    clean_df["category"] = df[mapped["category"]].astype(str).str.strip() if mapped["category"] else "Uncategorized"
    clean_df["transaction_type"] = df[mapped["transaction_type"]].astype(str).str.strip() if mapped["transaction_type"] else ""

    if mapped["category"] is None:
        clean_df["category"] = "Uncategorized"

    if mapped["transaction_type"] is None:
        clean_df["transaction_type"] = ""

    for idx, row in clean_df.iterrows():
        errors = []
        if not row["merchant"]:
            errors.append("missing merchant")
        if not row["amount"]:
            errors.append("missing amount")
        if not row["date"]:
            errors.append("missing date")

        try:
            row["amount"] = float(row["amount"])
        except Exception:
            errors.append("invalid amount")

        try:
            row["date"] = pd.to_datetime(row["date"], errors="raise")
        except Exception:
            errors.append("invalid date")

        if not row["transaction_type"]:
            row["transaction_type"] = "debit" if row["amount"] < 0 else "credit"

        if errors:
            invalid_rows.append({
                "row": int(idx + 2),
                "reason": ", ".join(errors)
            })

    valid_df = clean_df[~clean_df.index.isin([r["row"] - 2 for r in invalid_rows])].copy()
    valid_df["date"] = pd.to_datetime(valid_df["date"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
    valid_df["category"] = valid_df["category"].replace({"": "Uncategorized"})
    valid_df["transaction_type"] = valid_df["transaction_type"].replace({"": "debit"})

    return valid_df, invalid_rows


def create_transaction(
    db: Session,
    user_id: int,
    merchant: str,
    amount: float,
    date: str | datetime,
    category: str,
    transaction_type: str
) -> Transaction:
    """Create and save a single transaction (for small cases or testing)."""
    if isinstance(date, str):
        date = datetime.fromisoformat(date.replace("Z", "+00:00"))
    
    transaction = Transaction(
        user_id=user_id,
        merchant=merchant,
        amount=amount,
        date=date,
        category=category,
        transaction_type=transaction_type
    )
    return save_transaction(db, transaction)


def save_transaction(db: Session, transaction: Transaction) -> Transaction:
    """Save a single ORM object."""
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def save_transactions(db: Session, transactions: List[Transaction]) -> List[Transaction]:
    """Bulk save multiple ORM objects (recommended)."""
    if not transactions:
        return []
    
    db.add_all(transactions)
    db.commit()
    
    # Refresh all (optional — expensive for very large batches)
    for t in transactions:
        db.refresh(t)
    
    return transactions


def process_csv(
    db: Session,
    user_id: int,
    transactions: List[Dict]
) -> List[Transaction]:
    """Process list of dicts (e.g. from CSV parsing)."""
    created_transactions = []
    
    for tx_data in transactions:
        validate_transaction(tx_data)  # Validate each
        
        # Convert to ORM instance
        if isinstance(tx_data["date"], str):
            date_obj = datetime.fromisoformat(tx_data["date"].replace("Z", "+00:00"))
        else:
            date_obj = tx_data["date"]
        
        transaction = Transaction(
            user_id=user_id,
            merchant=tx_data["merchant"],
            amount=float(tx_data["amount"]),
            date=date_obj,
            category=tx_data["category"],
            transaction_type=tx_data["transaction_type"]
        )
        created_transactions.append(transaction)
    
    # Bulk save once
    return save_transactions(db, created_transactions)


# Optional: Direct DataFrame version
def process_csv_dataframe(
    db: Session,
    user_id: int,
    df: pd.DataFrame
) -> List[Transaction]:
    """Process pandas DataFrame directly (very efficient for CSVs)."""
    validate_dataframe(df)
    
    transactions = []
    for _, row in df.iterrows():
        tx_data = row.to_dict()
        validate_transaction(tx_data)  # or handle vectorized
        
        transaction = Transaction(
            user_id=user_id,
            merchant=str(row["merchant"]),
            amount=float(row["amount"]),
            date=pd.to_datetime(row["date"]).to_pydatetime(),
            category=str(row["category"]),
            transaction_type=str(row["transaction_type"])
        )
        transactions.append(transaction)
    
    return save_transactions(db, transactions)