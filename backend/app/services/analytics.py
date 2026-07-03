from sqlalchemy import func, extract, desc, and_
from sqlalchemy.orm import Session
from sqlalchemy.sql import case
from datetime import date, timedelta
from typing import List, Optional
import calendar

from backend.app.models.transaction import Transaction 
from backend.app.schemas.analytics import (
    FinancialSummary,
    MonthlyTrendResponse,
    MonthlyTrendItem,
    TopMerchantsResponse,
    TopMerchant,
    CategoryBreakdown,
    CategoryBreakdownResponse
)


class AnalyticsService:
    """Service layer for financial analytics """

    def __init__(self, db: Session):
        self.db = db

    def get_financial_summary(
        self, 
        user_id: int, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> FinancialSummary:
    
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        total_count = query.count()

        
        total_income = query.filter(
            func.lower(Transaction.transaction_type).in_(["credit", "income"])
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0.0

        # Expenses: only "debit" or "expense"
        total_expenses = query.filter(
            func.lower(Transaction.transaction_type).in_(["debit", "expense"])
        ).with_entities(func.sum(Transaction.amount)).scalar() or 0.0

        net_balance = total_income - total_expenses

        print(f"DEBUG - Total records: {total_count} | Income: {total_income:.2f} | Expenses: {total_expenses:.2f}")

        return FinancialSummary(
            total_income=round(float(total_income), 2),
            total_expenses=round(float(total_expenses), 2),
            net_balance=round(float(net_balance), 2),
            transaction_count=total_count
        )
     
    def get_category_breakdown(
        self, user_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> CategoryBreakdownResponse:
        """Complete breakdown of all financial activity by category"""
    
        # 1. Build the base query to group by category
        query = self.db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("total_amount"),
            func.count(Transaction.id).label("transaction_count")
        ).filter(
            Transaction.user_id == user_id  # No type filter, includes everything
        )

        # 2. Apply optional date filters
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        results = query.group_by(Transaction.category)

        # 3. Format the data into your list structure
        breakdown = [
            CategoryBreakdown(
                category=row.category or "Uncategorized",
                total_amount=round(float(row.total_amount), 2),
                transaction_count=row.transaction_count
            )
            for row in results
        ]  

        # 4. Return the exact response structure you requested
        return CategoryBreakdownResponse(
            breakdown=breakdown,
            total_categories=len(breakdown)
        )
     
    def get_monthly_trend(
        self, user_id: int, months: int = 6, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> MonthlyTrendResponse:
        """Monthly income, expenses and net for line chart"""
        
        end = date.today()
        start = date(end.year, end.month - months + 1, 1) if months else date(end.year - 1, end.month, 1)

        query = self.db.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(
                case((Transaction.amount > 0, Transaction.amount), else_=0)
            ).label('income'),
            func.sum(
                case((Transaction.transaction_type == "debit", Transaction.amount), else_=0)
            ).label('expenses')
        ).filter(
            Transaction.user_id == user_id,
            Transaction.category != "Income",
            Transaction.date >= start,
            Transaction.date <= end
        ).group_by('year', 'month').order_by('year', 'month')

        results = query.all()

        trend = []
        for row in results:
            month_str = f"{int(row.year)}-{int(row.month):02d}"
            total_income = float(row.income or 0)
            total_expenses = float(row.expenses or 0)
            trend.append(
                MonthlyTrendItem(
                    month=month_str,
                    total_income=round(total_income, 2),
                    total_expenses=round(total_expenses, 2),
                    net_balance=round(total_income - total_expenses, 2)
                )
            )

        return MonthlyTrendResponse(trends=trend, period=f"Last {months} months")

    def get_top_merchants(
        self, user_id: int, limit: int = 10, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> TopMerchantsResponse:
        """Top merchants by total spending (expenses)"""
    
        # Bundle exclusions to make the query much cleaner
        excluded_categories = [
            "Income", "Transfer", "Refund", "Adjustment", "Reimbursement", 
            "Investment", "Loan", "Other", "Uncategorized", "Savings", 
            "Withdrawal", "Deposit"
        ]

        query = self.db.query(
            Transaction.merchant,
            func.sum(Transaction.amount).label("amount"),
            func.count(Transaction.id).label("transaction_count")
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "debit",  # Fixed: Expenses are debits in your system
            Transaction.category.notin_(excluded_categories),
            Transaction.merchant.isnot(None),
            Transaction.merchant != ""  # Guard against empty strings
        )

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        # Group, order by highest spending first, and apply the limit
        results = query.group_by(Transaction.merchant)\
                    .order_by(func.sum(Transaction.amount).desc())\
                    .limit(limit)\
                    .all()

        # Format into your response structure
        merchants = [
            TopMerchant(
                merchant=row.merchant,
                amount=round(float(row.amount), 2),
                transaction_count=row.transaction_count
            )
            for row in results
        ]

        return TopMerchantsResponse(
        merchants=merchants,
        total_merchants=len(merchants)
    )