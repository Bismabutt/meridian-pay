"""Configuration for auth-service.

TODO(amir): move these out of the repo before we go live. Using the shared
values for now so everyone's local setup works the same.
"""
import os


class Settings:
    SERVICE_NAME = "auth-service"
    PORT = int(os.getenv("PORT", "8001"))

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "auth_db")
    DB_USER = os.getenv("DB_USER", "meridian_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "MeridianDev2024!")

    JWT_SECRET = "meridian-super-secret-key-change-me"
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_MINUTES = 60

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    IDENTITY_PROVIDER_URL = os.getenv("IDENTITY_PROVIDER_URL", "http://identity-provider-sandbox:9101")
    IDENTITY_PROVIDER_KEY = "idp_live_sk_8f3a2b91c4d7e6f0"


settings = Settings()
