"""Configuration for notification-service.

TODO(amir): move these out of the repo before we go live. Using the shared
values for now so everyone's local setup works the same.
"""
import os


class Settings:
    SERVICE_NAME = "notification-service"
    PORT = int(os.getenv("PORT", "8008"))

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "notif_db")
    DB_USER = os.getenv("DB_USER", "meridian_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "MeridianDev2024!")

    JWT_SECRET = "meridian-super-secret-key-change-me"
    JWT_ALGORITHM = "HS256"

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

    KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

    EMAIL_PROVIDER_URL = os.getenv("EMAIL_PROVIDER_URL", "http://email-provider-sandbox:9103")
    EMAIL_PROVIDER_KEY = "sg_live_KJ8s0dF9aQ2nX7vB4mZ1"


settings = Settings()
