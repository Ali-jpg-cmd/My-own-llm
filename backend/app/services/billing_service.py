"""
Billing service for Stripe integration and subscription management
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

import stripe
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)


class BillingService:
    """Service for handling billing and subscriptions"""
    
    def __init__(self):
        if settings.stripe_secret_key:
            stripe.api_key = settings.stripe_secret_key
        self.price_ids = {
            "basic": "price_basic_monthly",
            "pro": "price_pro_monthly",
            "enterprise": "price_enterprise_monthly"
        }
    
    def create_customer(self, user: User, email: str) -> str:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user.id}
            )
            return customer.id
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create billing account"
            )
    
    def create_subscription(self, user: User, tier: str) -> Dict[str, Any]:
        """Create a subscription for a user"""
        try:
            if not user.stripe_customer_id:
                customer_id = self.create_customer(user, user.email)
                user.stripe_customer_id = customer_id
            
            price_id = self.price_ids.get(tier)
            if not price_id:
                raise ValueError(f"Invalid subscription tier: {tier}")
            
            subscription = stripe.Subscription.create(
                customer=user.stripe_customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"]
            )
            
            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create subscription"
            )
    
    def cancel_subscription(self, user: User) -> bool:
        """Cancel a user's subscription"""
        try:
            if not user.stripe_customer_id:
                return False
            
            subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
            for sub in subscriptions.data:
                if sub.status == "active":
                    stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
                    return True
            
            return False
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return False
    
    def get_subscription_status(self, user: User) -> Optional[Dict[str, Any]]:
        """Get current subscription status"""
        try:
            if not user.stripe_customer_id:
                return None
            
            subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
            if not subscriptions.data:
                return None
            
            latest_sub = subscriptions.data[0]
            return {
                "id": latest_sub.id,
                "status": latest_sub.status,
                "current_period_end": latest_sub.current_period_end,
                "cancel_at_period_end": latest_sub.cancel_at_period_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get subscription status: {e}")
            return None
    
    def calculate_cost(self, tokens: int) -> float:
        """Calculate cost based on token usage"""
        return (tokens / 1000) * settings.price_per_1k_tokens


# Global billing service instance
billing_service = BillingService()
