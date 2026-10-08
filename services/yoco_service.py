# ============================================================
# KALXA TICKETING — YOCO PAYMENT SERVICE
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
# Handles Yoco hosted checkout payments for:
#
# 1. Event organizer SaaS subscriptions
# 2. Restaurant Standard/Premium subscriptions
#
# DOES NOT HANDLE:
# - Customer event ticket purchases
# - Organizer settlement accounts
# - Flutterwave payments
#
# SECURITY
# ------------------------------------------------------------
# - Secret API key stays on the server.
# - Checkout amounts are converted to cents.
# - Currency is fixed to ZAR.
# - HTTP requests have timeouts.
# - API errors are handled.
# - Checkout responses are validated.
# - Payment confirmation is NOT based on browser redirects.
#
# ============================================================

import os
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from urllib.parse import urlparse

import requests


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

YOCO_API_BASE_URL = (
    "https://payments.yoco.com/api"
)

YOCO_CHECKOUT_ENDPOINT = (
    "/checkouts"
)

YOCO_REQUEST_TIMEOUT = 20


# ============================================================
# EXCEPTIONS
# ============================================================

class YocoError(Exception):
    """Base exception for Yoco integration errors."""


class YocoConfigurationError(YocoError):
    """Missing or invalid Yoco configuration."""


class YocoAPIError(YocoError):
    """Yoco API request failed."""


class YocoValidationError(YocoError):
    """Invalid payment or checkout data."""


# ============================================================
# CONFIGURATION HELPERS
# ============================================================

def get_yoco_secret_key():

    key = (
        os.getenv("YOCO_SECRET_KEY", "")
        .strip()
    )

    if not key:
        raise YocoConfigurationError(
            "YOCO_SECRET_KEY is not configured."
        )

    return key


def yoco_is_configured():

    return bool(
        os.getenv("YOCO_SECRET_KEY", "").strip()
    )


# ============================================================
# AMOUNT HELPERS
# ============================================================

def amount_to_cents(amount):
    """
    Convert a ZAR amount to integer cents.

    Example:
        Decimal("219.00") -> 21900
        Decimal("299.00") -> 29900
    """

    try:
        value = Decimal(str(amount))

    except (InvalidOperation, TypeError, ValueError):
        raise YocoValidationError(
            "Invalid payment amount."
        )

    if not value.is_finite() or value <= 0:
        raise YocoValidationError(
            "Payment amount must be greater than zero."
        )

    cents = value * Decimal("100")

    if cents != cents.to_integral_value():
        raise YocoValidationError(
            "Payment amount cannot contain fractions of a cent."
        )

    return int(cents)


# ============================================================
# URL VALIDATION
# ============================================================

def validate_redirect_url(url):

    if not isinstance(url, str):
        raise YocoValidationError(
            "Redirect URL must be a string."
        )

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        raise YocoValidationError(
            "Yoco redirect URLs must use HTTPS."
        )

    return url


# ============================================================
# HTTP CLIENT
# ============================================================

def yoco_api_request(
    method,
    endpoint,
    payload=None,
):

    secret_key = get_yoco_secret_key()

    if method not in {"GET", "POST"}:
        raise YocoValidationError(
            "Unsupported Yoco request method."
        )

    if (
        not endpoint.startswith("/")
        or endpoint.startswith("//")
        or "://" in endpoint
    ):
        raise YocoValidationError(
            "Invalid Yoco API endpoint."
        )

    url = (
        YOCO_API_BASE_URL
        + endpoint
    )

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload if method == "POST" else None,
            timeout=YOCO_REQUEST_TIMEOUT,
            allow_redirects=False,
        )

    except requests.Timeout as error:

        logger.warning(
            "[Yoco] Request timed out: %s",
            endpoint,
        )

        raise YocoAPIError(
            "Yoco did not respond in time. Please try again."
        ) from error

    except requests.RequestException as error:

        logger.exception(
            "[Yoco] Network request failed."
        )

        raise YocoAPIError(
            "Could not communicate with Yoco."
        ) from error

    if not 200 <= response.status_code < 300:

        logger.error(
            "[Yoco] API error: status=%s endpoint=%s",
            response.status_code,
            endpoint,
        )

        raise YocoAPIError(
            "Yoco could not process the payment request."
        )

    try:
        result = response.json()

    except ValueError as error:

        raise YocoAPIError(
            "Yoco returned an invalid response."
        ) from error

    if not isinstance(result, dict):
        raise YocoAPIError(
            "Yoco returned an unexpected response format."
        )

    return result


# ============================================================
# CREATE HOSTED CHECKOUT
# ============================================================

def create_yoco_checkout(
    *,
    amount,
    payment_reference,
    success_url,
    cancel_url,
    failure_url=None,
    metadata=None,
):

    amount_cents = amount_to_cents(amount)

    reference = str(
        payment_reference or ""
    ).strip()

    if not reference or len(reference) > 100:
        raise YocoValidationError(
            "A valid payment reference is required."
        )

    success_url = validate_redirect_url(
        success_url
    )

    cancel_url = validate_redirect_url(
        cancel_url
    )

    if failure_url:
        failure_url = validate_redirect_url(
            failure_url
        )

    if metadata is not None and not isinstance(metadata, dict):
        raise YocoValidationError(
            "Checkout metadata must be a dictionary."
        )

    payload = {
        "amount": amount_cents,
        "currency": "ZAR",
        "successUrl": success_url,
        "cancelUrl": cancel_url,
        "failureUrl": failure_url or cancel_url,
        "metadata": {
            **(metadata or {}),
            "kalxa_payment_reference": reference,
        },
    }

    result = yoco_api_request(
        "POST",
        YOCO_CHECKOUT_ENDPOINT,
        payload,
    )

    checkout_id = str(
        result.get("id") or ""
    ).strip()

    redirect_url = (
        result.get("redirectUrl")
        or ""
    )

    if not checkout_id:
        raise YocoAPIError(
            "Yoco did not return a checkout ID."
        )

    if not redirect_url:
        raise YocoAPIError(
            "Yoco did not return a checkout URL."
        )

    validate_redirect_url(
        redirect_url
    )

    return {
        "checkout_id": checkout_id,
        "checkout_url": redirect_url,
        "amount_cents": amount_cents,
        "currency": "ZAR",
        "payment_reference": reference,
        "raw_response": result,
    }


# ============================================================
# EVENT ORGANIZER SUBSCRIPTION CHECKOUT
# ============================================================

def create_organizer_subscription_checkout(
    *,
    payment,
    organizer,
    success_url,
    cancel_url,
):

    if not payment or not organizer:
        raise YocoValidationError(
            "Payment and organizer are required."
        )

    if payment.organizer_id != organizer.id:
        raise YocoValidationError(
            "Subscription does not belong to this organizer."
        )

    if payment.payment_status != "pending":
        raise YocoValidationError(
            "Only pending subscriptions can be paid."
        )

    return create_yoco_checkout(
        amount=payment.amount,
        payment_reference=payment.payment_reference,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "payment_type": "organizer_subscription",
            "subscription_payment_id": payment.id,
            "organizer_id": organizer.id,
            "account_type": organizer.account_type,
            "plan_name": payment.plan_name,
            "period_days": payment.period_days,
        },
    )


# ============================================================
# RESTAURANT SUBSCRIPTION CHECKOUT
# ============================================================

def create_restaurant_subscription_checkout(
    *,
    payment,
    advert,
    organizer,
    success_url,
    cancel_url,
):

    if not payment or not advert or not organizer:
        raise YocoValidationError(
            "Payment, restaurant and organizer are required."
        )

    if (
        payment.organizer_id != organizer.id
        or payment.restaurant_advert_id != advert.id
        or advert.organizer_id != organizer.id
    ):
        raise YocoValidationError(
            "Restaurant subscription ownership mismatch."
        )

    if payment.payment_status != "pending":
        raise YocoValidationError(
            "Only pending subscriptions can be paid."
        )

    return create_yoco_checkout(
        amount=payment.amount,
        payment_reference=payment.payment_reference,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "payment_type": "restaurant_subscription",
            "restaurant_subscription_payment_id": payment.id,
            "restaurant_advert_id": advert.id,
            "organizer_id": organizer.id,
            "plan_tier": payment.plan_tier,
            "plan_name": payment.plan_name,
            "period_days": payment.period_days,
        },
    )


# ============================================================
# PAYMENT LOOKUP
# ============================================================
#
# This helper is reserved for reconciliation.
#
# Confirm the checkout retrieval endpoint and response schema
# in the Yoco API version enabled for your account before
# using it for payment verification.
#
# ============================================================

def get_yoco_checkout(checkout_id):

    checkout_id = str(
        checkout_id or ""
    ).strip()

    if not checkout_id:
        raise YocoValidationError(
            "Checkout ID is required."
        )

    if not checkout_id.replace("-", "").replace("_", "").isalnum():
        raise YocoValidationError(
            "Invalid checkout ID."
        )

    return yoco_api_request(
        "GET",
        f"/checkouts/{checkout_id}",
    )
