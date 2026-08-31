# ============================================================
# STAGE 1 — build the binary (this whole stage gets thrown away)
# ============================================================
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Dependencies first, so this layer caches independently of the code
COPY go.mod go.sum ./
RUN go mod download

# Now the source
COPY main.go ./

# Compile a fully static binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o ledger-service .

# ============================================================
# STAGE 2 — the final image (tiny, binary only)
# ============================================================
FROM alpine:3.19

RUN apk add --no-cache curl ca-certificates

WORKDIR /app

# Non-root user
RUN adduser -D -u 1001 appuser

# Copy ONLY the binary from stage 1
COPY --from=builder --chown=appuser:appuser /build/ledger-service .

USER appuser

EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1
CMD ["./ledger-service"]