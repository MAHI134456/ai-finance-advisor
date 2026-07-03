from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional



class FinancialSummary(BaseModel):
    total_income: float = Field(..., description="Total income amount, example=5200.00")
    total_expenses: float = Field(..., description="Total expenses amount, example=3200.00")
    net_balance: float = Field(..., description="Net balance (income - expenses), example=2000.00")
   

    class Config:
        json_schema_extra = {
            "example": {
                "total_income": 5200.00,
                "total_expenses": 3200.00,
                "net_balance": 2000.00,
                "transaction_count": 15,
            }
        }      


class MonthlyTrendItem(BaseModel):
    month: str = Field(..., description="Month in YYYY-MM format, example='2024-01'")
    total_income: float = Field(..., description="Total income for the month, example=4000.00")
    total_expenses: float = Field(..., description="Total expenses for the month, example=2500.00")
    net_balance: float = Field(..., description="Net balance for the month (income - expenses), example=1500.00")



class MonthlyTrendResponse(BaseModel):
    trends: List[MonthlyTrendItem] = Field(..., description="List of monthly trends")
    period: Optional[str] = Field(None, description="Optional period for the trends, example='2024-01 to 2024-03'")
    class Config:
        json_schema_extra = {
            "example": {
                "trends": [
                    {"month": "2024-01", "total_income": 4000.00, "total_expenses": 2500.00, "net_balance": 1500.00},
                    {"month": "2024-02", "total_income": 4500.00, "total_expenses": 3000.00, "net_balance": 1500.00},
                    {"month": "2024-03", "total_income": 5000.00, "total_expenses": 3500.00, "net_balance": 1500.00}
                ],
                "period": "2024-01 to 2024-03"
            }
        }



class TopMerchant(BaseModel):
    merchant: str = Field(..., description="Merchant name, example='Amazon'")
    total_amount: float = Field(..., description="Total amount spent at this merchant, example=1200.00")
    transaction_count: int = Field(..., description="Number of transactions with this merchant, example=10")



class TopMerchantsResponse(BaseModel):
    merchants: List[TopMerchant] = Field(..., description="List of top merchants")
    total_merchants: Optional[int] = Field(None, description="Total number of unique merchants, example=25")
    class Config:
        json_schema_extra = {
            "example": {
                "merchants": [
                    {"merchant": "Amazon", "total_amount": 1200.00, "transaction_count": 10},
                    {"merchant": "Starbucks", "total_amount": 300.00, "transaction_count": 5},
                    {"merchant": "Uber", "total_amount": 150.00, "transaction_count": 3}
                ],
                "total_merchants": 25
            }
        }


class CategoryBreakdown(BaseModel):
    category: str = Field(..., description="Category name, example='Groceries'")
    total_amount: float = Field(..., description="Total amount spent in this category, example=500.00")
    transaction_count: int = Field(..., description="Number of transactions in this category, example=8")   


class CategoryBreakdownResponse(BaseModel):
    breakdown: List[CategoryBreakdown] = Field(..., description="List of category breakdowns")
    total_categories: Optional[int] = Field(None, description="Total number of unique categories, example=12")
    class Config:
        json_schema_extra = {
            "example": {
                "breakdown": [
                    {"category": "Groceries", "total_amount": 500.00, "transaction_count": 8},
                    {"category": "Dining", "total_amount": 300.00, "transaction_count": 5},
                    {"category": "Transportation", "total_amount": 150.00, "transaction_count": 3}
                ],
                "total_categories": 12
            }
        }


class AnalyticsFilter(BaseModel):
    start_date: Optional[datetime] = Field(None, description="Start date for filtering analytics, example='2024-01-01'")
    end_date: Optional[datetime] = Field(None, description="End date for filtering analytics, example='2024-03-31'")
    current_user: Optional[int] = Field(None, description="User ID for filtering analytics, example=1")