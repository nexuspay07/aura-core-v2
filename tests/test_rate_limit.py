from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.rate_limit import CommercialRateLimitMiddleware, FixedWindowRateLimiter, RateLimitPolicy

def test_fixed_window_limiter_is_deterministic_and_resets():
 now=[0];limiter=FixedWindowRateLimiter(clock=lambda:now[0]);policy=RateLimitPolicy(2,10)
 assert limiter.allow('key',policy) and limiter.allow('key',policy) and not limiter.allow('key',policy)
 now[0]=10;assert limiter.allow('key',policy)

def test_middleware_returns_safe_429_for_auth_and_leaves_health_unlimited():
 app=FastAPI();app.add_middleware(CommercialRateLimitMiddleware,limiter=FixedWindowRateLimiter(),auth_policy=RateLimitPolicy(1))
 @app.post('/auth/login')
 def login():return {'ok':True}
 @app.get('/health')
 def health():return {'ok':True}
 client=TestClient(app);assert client.post('/auth/login').status_code==200;response=client.post('/auth/login');assert response.status_code==429 and response.json()=={'detail':'Rate limit exceeded'};assert client.get('/health').status_code==200
