"""Prometheus metrics.

Metric names are chosen to answer business questions rather than describe
system internals: how many payments are succeeding, how long a customer
waits, and how many payments are waiting on the partner bank.
"""
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from starlette.requests import Request
from starlette.responses import Response

# ------------------------------------------------------------
# RED metrics — applied to every service
# ------------------------------------------------------------

http_requests_total = Counter(
    "http_requests_total",
    "HTTP requests received",
    ["service", "method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Time from request received to response sent",
    ["service", "method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0),
)

http_requests_in_flight = Gauge(
    "http_requests_in_flight",
    "Requests currently being processed",
    ["service"],
)


def install_metrics(app, service_name: str):
    """Attach request metrics and the /metrics endpoint to a FastAPI app."""

    @app.middleware("http")
    async def _record(request: Request, call_next):
        if request.url.path in ("/metrics", "/health"):
            return await call_next(request)

        # Use the route template rather than the raw path, so /v1/payments/abc
        # and /v1/payments/def do not become separate time series.
        path = request.scope.get("route").path if request.scope.get("route") else request.url.path

        http_requests_in_flight.labels(service=service_name).inc()
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - started
            http_requests_in_flight.labels(service=service_name).dec()
            http_requests_total.labels(
                service=service_name,
                method=request.method,
                path=path,
                status=str(status),
            ).inc()
            http_request_duration_seconds.labels(
                service=service_name,
                method=request.method,
                path=path,
            ).observe(elapsed)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
