"""Payment provider abstraction (blueprint section 26). Swappable via config."""
from app.payments.base import PaymentProvider, CheckoutSession, PaymentEvent  # noqa: F401
from app.core.config import settings


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "paystack":
        from app.payments.paystack import PaystackProvider
        return PaystackProvider()
    from app.payments.mock import MockProvider
    return MockProvider()
