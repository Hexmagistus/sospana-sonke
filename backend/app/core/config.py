"""Application configuration, loaded from environment variables.

All secrets and environment-specific values live here so that nothing sensitive
is hard-coded in the codebase (Security Architecture, blueprint section 15).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core
    APP_NAME: str = "Sospana Sonke"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    # Comma-separated list of allowed browser origins (the frontend URL in production).
    CORS_ORIGINS: str = "http://localhost:3000"

    # First-boot bootstrap (used by managed hosting). All optional and idempotent.
    AUTO_SEED: bool = False              # import the bundled company CSV if the table is empty
    ADMIN_EMAIL: str | None = None       # create this admin on first boot if it doesn't exist
    ADMIN_PASSWORD: str | None = None

    # Database. Defaults to a local SQLite file so the app runs with zero setup;
    # production uses the Postgres URL supplied via docker-compose / environment.
    DATABASE_URL: str = "sqlite:///./sospana.db"

    # Security
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-use-a-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 48
    PASSWORD_RESET_EXPIRE_HOURS: int = 2
    MFA_ISSUER: str = "Sospana Sonke"

    # Scraper health alerting
    SOURCE_FAILURE_ALERT_THRESHOLD: int = 3   # consecutive failures before an admin alert

    # JavaScript-rendered careers pages (Phase 2). Uses headless Chromium — heavier,
    # so OFF by default (enable on infrastructure with enough memory).
    JS_RENDER_ENABLED: bool = False

    # URL tester
    URL_TEST_TIMEOUT_SECONDS: float = 10.0
    URL_TEST_USER_AGENT: str = "SospanaSonkeBot/0.1 (+https://sospanasonke.co.za/bot)"

    # File storage (CV uploads and generated documents).
    # Default is local disk for development; production uses S3-compatible storage.
    STORAGE_BACKEND: str = "local"          # local | s3
    STORAGE_DIR: str = "./storage"          # used when STORAGE_BACKEND=local
    S3_BUCKET: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_REGION: str | None = None

    # Upload limits and allowed CV types (blueprint sections 4 & 15).
    MAX_UPLOAD_MB: int = 8
    ALLOWED_CV_EXTENSIONS: tuple[str, ...] = ("pdf", "docx", "txt")

    # Malware scanning. When enabled, uploads are scanned with ClamAV (clamd).
    # When disabled, a safe fallback runs (size + type/magic-byte checks only).
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    # AI provider abstraction (blueprint section 24).
    AI_PROVIDER: str = "heuristic"          # heuristic | claude | openai
    AI_MODEL: str = "claude-haiku"          # provider-specific model id
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    # Subscription & payments (blueprint sections 17 & 26).
    PAYMENT_PROVIDER: str = "mock"          # mock | paystack
    PAYSTACK_SECRET_KEY: str | None = None
    PAYSTACK_PUBLIC_KEY: str | None = None
    PAYMENT_CALLBACK_URL: str = "http://localhost:3000/subscription/return"
    PLAN_AMOUNT_ZAR: int = 100              # the R100/month price
    PLAN_CURRENCY: str = "ZAR"
    BILLING_PERIOD_DAYS: int = 30
    TRIAL_DAYS: int = 14                     # free trial on sign-up; 0 disables
    PAST_DUE_GRACE_DAYS: int = 3             # access retained briefly after a failed renewal

    # Notifications & email (blueprint section 31).
    EMAIL_PROVIDER: str = "console"          # console | smtp
    EMAIL_FROM: str = "Sospana Sonke <no-reply@sospanasonke.co.za>"
    NOTIFY_EMAILS: bool = False              # send emails in addition to dashboard notifications
    NOTIFY_SMS: bool = False
    NOTIFY_PUSH: bool = False
    SMS_PROVIDER: str = "console"            # console | twilio
    PUSH_PROVIDER: str = "console"           # console | fcm
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    # Application automation (blueprint sections 13, 14, 28 — Phase 2).
    # OFF by default: a global kill-switch so automated submission is opt-in and safe.
    AUTOMATION_ENABLED: bool = False
    PLAYWRIGHT_EXECUTABLE_PATH: str | None = None   # set to the installed Chromium in prod
    PLAYWRIGHT_TIMEOUT_MS: int = 20000
    PLAYWRIGHT_USER_AGENT: str = "SospanaSonkeBot/0.1 (+https://sospanasonke.co.za/bot)"


@lru_cache
def get_settings() -> "Settings":
    return Settings()


settings = get_settings()
