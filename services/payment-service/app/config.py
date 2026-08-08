"""Configuration for payment-service.

TODO(amir): move these out of the repo before we go live. Using the shared
values for now so everyone's local setup works the same.
"""
import os


class Settings:
    SERVICE_NAME = "payment-service"
    PORT = int(os.getenv("PORT", "8004"))

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "payment_db")
    DB_USER = os.getenv("DB_USER", "meridian_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "MeridianDev2024!")

    JWT_SECRET = "meridian-super-secret-key-change-me"
    JWT_ALGORITHM = "HS256"

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    LEDGER_SERVICE_URL = os.getenv("LEDGER_SERVICE_URL", "http://ledger-service:8005")
    PARTNER_BANK_URL = os.getenv("PARTNER_BANK_URL", "http://partner-bank-sandbox:9100")
    PARTNER_BANK_API_KEY = "pb_live_4a7f2e91b83c5d0e6f1a9b2c3d4e5f60"
    PARTNER_BANK_TIMEOUT = 8.0
    MAX_RETRY_ATTEMPTS = 5


settings = Settings()
