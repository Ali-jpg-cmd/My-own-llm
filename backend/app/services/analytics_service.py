"""
Analytics service for tracking usage and generating insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.usage import Usage
from app.models.request_log import RequestLog
from app.models.user import User

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and usage tracking"""
    
    def get_user_usage_stats(self, db: Session, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get usage data
        usage_query = db.query(Usage).filter(
            and_(
                Usage.user_id == user_id,
                Usage.created_at >= start_date
            )
        )
        
        total_requests = usage_query.count()
        total_tokens = usage_query.with_entities(func.sum(Usage.total_tokens)).scalar() or 0
        total_cost = usage_query.with_entities(func.sum(Usage.total_cost)).scalar() or 0.0
        
        # Get daily usage
        daily_usage = db.query(
            func.date(Usage.created_at).label('date'),
            func.count(Usage.id).label('requests'),
            func.sum(Usage.total_tokens).label('tokens'),
            func.sum(Usage.total_cost).label('cost')
        ).filter(
            and_(
                Usage.user_id == user_id,
                Usage.created_at >= start_date
            )
        ).group_by(func.date(Usage.created_at)).all()
        
        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "daily_usage": [
                {
                    "date": str(day.date),
                    "requests": day.requests,
                    "tokens": day.tokens or 0,
                    "cost": float(day.cost or 0)
                }
                for day in daily_usage
            ]
        }
    
    def get_global_stats(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get global usage statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total users
        total_users = db.query(User).count()
        active_users = db.query(User).filter(
            User.last_login >= start_date
        ).count()
        
        # Total usage
        total_requests = db.query(Usage).filter(
            Usage.created_at >= start_date
        ).count()
        
        total_tokens = db.query(Usage).filter(
            Usage.created_at >= start_date
        ).with_entities(func.sum(Usage.total_tokens)).scalar() or 0
        
        total_cost = db.query(Usage).filter(
            Usage.created_at >= start_date
        ).with_entities(func.sum(Usage.total_cost)).scalar() or 0.0
        
        # Popular models
        popular_models = db.query(
            Usage.model_used,
            func.count(Usage.id).label('count')
        ).filter(
            Usage.created_at >= start_date
        ).group_by(Usage.model_used).order_by(func.count(Usage.id).desc()).limit(5).all()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "popular_models": [
                {"model": model.model_used, "count": model.count}
                for model in popular_models
            ]
        }
    
    def track_usage(self, db: Session, user_id: int, usage_data: Dict[str, Any]) -> Usage:
        """Track a new usage record"""
        usage = Usage(
            user_id=user_id,
            endpoint=usage_data.get("endpoint", ""),
            model_used=usage_data.get("model_used", ""),
            provider=usage_data.get("provider", ""),
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
            cost_per_1k_tokens=usage_data.get("cost_per_1k_tokens", 0.002),
            total_cost=usage_data.get("total_cost", 0.0),
            request_id=usage_data.get("request_id"),
            response_time_ms=usage_data.get("response_time_ms"),
            status_code=usage_data.get("status_code", 200)
        )
        
        usage.calculate_cost()
        
        db.add(usage)
        db.commit()
        db.refresh(usage)
        
        return usage


# Global analytics service instance
analytics_service = AnalyticsService()
