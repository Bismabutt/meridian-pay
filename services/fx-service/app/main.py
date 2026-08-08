"""fx-service — currency conversion.

Rates are cached. If the provider is unavailable the last known rate is served
within a staleness window; beyond that conversions are refused rather than
mispriced.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.db import query

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Meridian Pay — fx-service", version="1.0.3")


class ConversionRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount_minor: int


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


def _fetch_rate(pair: str):
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(
            f"{settings.FX_PROVIDER_URL}/v1/rates/{pair}",
            headers={"X-Api-Key": settings.FX_PROVIDER_KEY},
        )
        resp.raise_for_status()
        return float(resp.json()["rate"])


def get_rate(pair: str):
    """Return (rate, source, age_seconds)."""
    try:
        rate = _fetch_rate(pair)
        query(
            """INSERT INTO fx_rate_snapshots (id, pair, rate, fetched_at)
               VALUES (%s,%s,%s,NOW())""",
            (str(uuid.uuid4()), pair, rate), fetch=None,
        )
        return rate, "live", 0
    except Exception as exc:
        log.warning("fx provider unavailable for %s: %s", pair, exc)

    cached = query(
        """SELECT rate, fetched_at FROM fx_rate_snapshots
            WHERE pair = %s ORDER BY fetched_at DESC LIMIT 1""",
        (pair,), fetch="one",
    )
    if not cached:
        raise HTTPException(status_code=503, detail="No rate available for this pair")

    age = (datetime.now(timezone.utc) - cached["fetched_at"]).total_seconds()
    if age > settings.RATE_STALENESS_LIMIT_SECONDS:
        raise HTTPException(
            status_code=503,
            detail=f"Cached rate is {int(age)}s old, beyond the {settings.RATE_STALENESS_LIMIT_SECONDS}s limit",
        )
    return float(cached["rate"]), "cache", int(age)


@app.get("/v1/fx/rates/{pair}")
def read_rate(pair: str):
    rate, source, age = get_rate(pair.upper())
    return {"pair": pair.upper(), "rate": rate, "source": source, "age_seconds": age}


@app.post("/v1/fx/convert")
def convert(req: ConversionRequest):
    pair = f"{req.from_currency.upper()}{req.to_currency.upper()}"
    rate, source, age = get_rate(pair)
    effective = rate * (1 - settings.MARGIN_BPS / 10000)
    converted = int(req.amount_minor * effective)

    query(
        """INSERT INTO conversions (id, pair, mid_rate, effective_rate,
                amount_minor, converted_minor, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,NOW())""",
        (str(uuid.uuid4()), pair, rate, effective, req.amount_minor, converted),
        fetch=None,
    )
    return {
        "pair": pair, "mid_rate": rate, "effective_rate": round(effective, 6),
        "margin_bps": settings.MARGIN_BPS, "amount_minor": req.amount_minor,
        "converted_minor": converted, "rate_source": source, "rate_age_seconds": age,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
