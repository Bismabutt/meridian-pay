"""api-gateway — single entry point.

Authenticates, applies per-client rate limits, and routes to internal services.
Clients address one endpoint and have no knowledge of internal topology.
"""
import logging
import time

import httpx
import redis
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — api-gateway", version="2.3.0")

rds = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)

ROUTES = {
    "auth": settings.AUTH_SERVICE_URL,
    "accounts": settings.ACCOUNT_SERVICE_URL,
    "payments": settings.PAYMENT_SERVICE_URL,
    "fx": settings.FX_SERVICE_URL,
}

PUBLIC_PATHS = {"/v1/auth/login", "/v1/auth/register", "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


def check_rate_limit(identity: str, tier: str = "standard") -> bool:
    """Fixed window counter. One window per second per client."""
    limit = settings.RATE_LIMITS.get(tier, 100)
    key = f"rl:{identity}:{int(time.time())}"
    count = rds.incr(key)
    if count == 1:
        rds.expire(key, 2)
    return count <= limit


async def verify_token(authorization: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.AUTH_SERVICE_URL}/v1/auth/verify",
            headers={"Authorization": authorization},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return resp.json()


@app.api_route("/v1/{segment}/{path:path}",
               methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(segment: str, path: str, request: Request):
    upstream = ROUTES.get(segment)
    if not upstream:
        raise HTTPException(status_code=404, detail="Unknown route")

    full_path = f"/v1/{segment}/{path}"
    identity = request.client.host

    if full_path not in PUBLIC_PATHS:
        authorization = request.headers.get("authorization")
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        claims = await verify_token(authorization)
        identity = claims["user_id"]

    if not check_rate_limit(identity):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    body = await request.body()
    async with httpx.AsyncClient(timeout=30.0) as client:
        upstream_resp = await client.request(
            request.method,
            f"{upstream}{full_path}",
            content=body,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            params=dict(request.query_params),
        )

    log.info("%s %s -> %s", request.method, full_path, upstream_resp.status_code)
    return JSONResponse(status_code=upstream_resp.status_code,
                        content=upstream_resp.json() if upstream_resp.content else {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
