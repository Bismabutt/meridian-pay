"""FX rates provider sandbox."""
import os
import random

from fastapi import FastAPI, HTTPException

app = FastAPI(title="FX Provider Sandbox")

STATE = {"available": True}
BASE_RATES = {"GBPUSD": 1.2680, "GBPEUR": 1.1720, "GBPPKR": 352.40,
              "USDGBP": 0.7886, "EURGBP": 0.8532}


@app.get("/health")
def health():
    return {"status": "ok" if STATE["available"] else "unavailable"}


@app.post("/admin/outage")
def set_outage(enabled: bool):
    STATE["available"] = not enabled
    return {"available": STATE["available"]}


@app.get("/v1/rates/{pair}")
def rate(pair: str):
    if not STATE["available"]:
        raise HTTPException(status_code=503, detail="Rates feed unavailable")
    base = BASE_RATES.get(pair.upper())
    if not base:
        raise HTTPException(status_code=404, detail="Unknown currency pair")
    # small random walk so rates move like a real feed
    return {"pair": pair.upper(), "rate": round(base * random.uniform(0.998, 1.002), 6)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "9102")))
