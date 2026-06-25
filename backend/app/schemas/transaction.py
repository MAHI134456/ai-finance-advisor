from pydantic import BaseModel, ConfigDict
from datetime import datetime


class TransactionCreate(BaseModel):
    merchant: str
    amount: float
    date: datetime
    category: str
    transaction_type: str


class TransactionResponse(TransactionCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)