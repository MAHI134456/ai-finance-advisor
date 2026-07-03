# routers/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from backend.app.db.dependencies import get_db
from backend.app.services.analytics import AnalyticsService
from backend.app.schemas.analytics import (FinancialSummary,MonthlyTrendResponse,TopMerchantsResponse,CategoryBreakdownResponse)
from backend.app.auth.dependencies import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary", response_model=FinancialSummary)
def get_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    analytics_service = AnalyticsService(db)
    return analytics_service.get_financial_summary(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/category-breakdown", response_model=CategoryBreakdownResponse)
def get_category_breakdown(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    analytics_service = AnalyticsService(db)
    return analytics_service.get_category_breakdown(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/monthly-trends", response_model=MonthlyTrendResponse)
def get_monthly_trends(
    period: Optional[int] = 3,  # Default to last 3 months
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    analytics_service = AnalyticsService(db)
    return analytics_service.get_monthly_trend(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/top-merchants", response_model=TopMerchantsResponse)
def get_top_merchants(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    analytics_service = AnalyticsService(db)
    return analytics_service.get_top_merchants(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )
