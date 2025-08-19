"""
Rate limiting service (in-memory, per-process)
"""

import time
import logging
from typing import Tuple, Dict
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitService:
    """Simple in-memory, per-process rate limiter.
    Not distributed; sufficient for free, single-instance deployments.
    """
    
    def __init__(self):
        self.default_requests = settings.rate_limit_requests
        self.default_window = settings.rate_limit_window
        # key -> { 'window_start': int, 'count': int }
        self._counters: Dict[str, Dict[str, int]] = {}
    
    def _get_window_start(self, window: int) -> int:
        current_time = int(time.time())
        return (current_time // window) * window

    def check_rate_limit(self, identifier: str, requests: int = None, window: int = None) -> Tuple[bool, dict]:
        """Check if a request is allowed based on rate limits"""
        if requests is None:
            requests = self.default_requests
        if window is None:
            window = self.default_window
        
        window_start = self._get_window_start(window)
        entry = self._counters.get(identifier)
        
        if not entry or entry.get('window_start') != window_start:
            # New window
            self._counters[identifier] = {'window_start': window_start, 'count': 0}
            entry = self._counters[identifier]
        
        if entry['count'] >= requests:
            reset_ts = window_start + window
            reset_time = datetime.fromtimestamp(reset_ts)
            return False, {
                'limit': requests,
                'remaining': 0,
                'reset': reset_time.isoformat(),
                'window': window
            }
        
        # Increment
        entry['count'] += 1
        remaining = max(0, requests - entry['count'])
        reset_ts = window_start + window
        reset_time = datetime.fromtimestamp(reset_ts)
        
        return True, {
            'limit': requests,
            'remaining': remaining,
            'reset': reset_time.isoformat(),
            'window': window
        }
    
    def enforce_rate_limit(self, identifier: str, requests: int = None, window: int = None):
        is_allowed, info = self.check_rate_limit(identifier, requests, window)
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    'error': 'Rate limit exceeded',
                    'limit': info['limit'],
                    'reset': info['reset'],
                    'window': info['window']
                },
                headers={
                    'X-RateLimit-Limit': str(info['limit']),
                    'X-RateLimit-Remaining': str(info.get('remaining', 0)),
                    'X-RateLimit-Reset': info['reset']
                }
            )
        return info


# Global rate limit service instance
rate_limit_service = RateLimitService()
