"""Small process-local fixed-window limiter for staging and single-instance use.

Production multi-instance deployments must replace the store with a shared backend;
the policy itself remains independent of that backend.
"""
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

@dataclass(frozen=True)
class RateLimitPolicy:
    limit: int
    window_seconds: int = 60

class FixedWindowRateLimiter:
    def __init__(self, *, clock=monotonic):
        self.clock=clock;self._buckets={};self._lock=Lock()
    def allow(self,key,policy):
        now=self.clock()
        with self._lock:
            started,count=self._buckets.get(key,(now,0))
            if now-started>=policy.window_seconds:started,count=now,0
            if count>=policy.limit:return False
            self._buckets[key]=(started,count+1);return True

class CommercialRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self,app,limiter=None,auth_policy=None,payment_mutation_policy=None):
        super().__init__(app);self.limiter=limiter or FixedWindowRateLimiter()
        self.auth_policy=auth_policy or RateLimitPolicy(100);self.payment_mutation_policy=payment_mutation_policy or RateLimitPolicy(200)
    async def dispatch(self,request,call_next):
        path=request.url.path;method=request.method
        policy=None;bucket=None
        if path.startswith('/auth/'):
            policy=self.auth_policy;bucket='auth'
        elif method not in {'GET','HEAD','OPTIONS'} and ('payment-attempt' in path or path.startswith('/commercial/refunds')):
            policy=self.payment_mutation_policy;bucket='payment'
        if policy:
            client=request.client.host if request.client else 'unknown'
            if not self.limiter.allow((bucket,client),policy):
                return JSONResponse(status_code=429,content={'detail':'Rate limit exceeded'},headers={'Retry-After':str(policy.window_seconds)})
        return await call_next(request)
