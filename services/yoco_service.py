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
# - Paystack event ticket payments
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
# - Subscription activation requires independent verification.
#
# ============================================================

import logging
import os
import re

from decimal import Decimal, InvalidOperation
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

YOCO_MAX_RESPONSE_BYTES = (
    1024 * 1024
)

YOCO_CURRENCY = "ZAR"


# ============================================================
# EXCEPTIONS
# ============================================================

class YocoError(Exception):
    """
    Base exception for Yoco integration errors.
    """


class YocoConfigurationError(YocoError):
    """
    Missing or invalid Yoco configuration.
    """


class YocoAPIError(YocoError):
    """
    Yoco API request failed.
    """


class YocoValidationError(YocoError):
    """
    Invalid payment or checkout data.
    """


# ============================================================
# CONFIGURATION HELPERS
# ============================================================

def get_yoco_secret_key():
    """
    Retrieve the Yoco secret API key.

    The key must never be exposed to the browser.
    """

    key = (
        os.getenv(
            "YOCO_SECRET_KEY",
            "",
        )
        .strip()
    )

    if not key:

        raise YocoConfigurationError(
            "YOCO_SECRET_KEY is not configured."
        )

    return key


def yoco_is_configured():
    """
    Return True when a Yoco secret key is configured.
    """

    return bool(
        os.getenv(
            "YOCO_SECRET_KEY",
            "",
        ).strip()
    )


# ============================================================
# AMOUNT HELPERS
# ============================================================

def amount_to_cents(amount):
    """
    Convert a ZAR amount to integer cents.

    Examples:
        Decimal("219.00") -> 21900
        Decimal("299.00") -> 29900

    Rejects:
        - Zero
        - Negative amounts
        - Invalid decimals
        - Fractions of a cent
        - Boolean values
    """

    if isinstance(amount, bool):

        raise YocoValidationError(
            "Invalid payment amount."
        )

    try:

        value = Decimal(
            str(amount)
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as error:

        raise YocoValidationError(
            "Invalid payment amount."
        ) from error

    if not value.is_finite():

        raise YocoValidationError(
            "Payment amount must be finite."
        )

    if value <= 0:

        raise YocoValidationError(
            "Payment amount must be greater than zero."
        )

    cents = (
        value * Decimal("100")
    )

    if cents != cents.to_integral_value():

        raise YocoValidationError(
            "Payment amount cannot contain fractions of a cent."
        )

    return int(cents)


# ============================================================
# REDIRECT URL VALIDATION
# ============================================================

def validate_redirect_url(url):
    """
    Validate an HTTPS redirect URL.

    Used for:
        successUrl
        cancelUrl
        failureUrl
        Yoco redirectUrl
    """

    if not isinstance(url, str):

        raise YocoValidationError(
            "Redirect URL must be a string."
        )

    url = url.strip()

    if not url:

        raise YocoValidationError(
            "Redirect URL is required."
        )

    if any(
        character.isspace()
        for character in url
    ):

        raise YocoValidationError(
            "Redirect URL contains whitespace."
        )

    try:

        parsed = urlparse(
            url
        )

        port = parsed.port

    except ValueError as error:

        raise YocoValidationError(
            "Invalid redirect URL."
        ) from error

    if parsed.scheme.lower() != "https":

        raise YocoValidationError(
            "Yoco redirect URLs must use HTTPS."
        )

    if not parsed.hostname:

        raise YocoValidationError(
            "Redirect URL must contain a hostname."
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):

        raise YocoValidationError(
            "Redirect URL cannot contain credentials."
        )

    if port is not None and not (
        1 <= port <= 65535
    ):

        raise YocoValidationError(
            "Invalid redirect URL port."
        )

    return url


# ============================================================
# CHECKOUT ID VALIDATION
# ============================================================

def validate_yoco_checkout_id(checkout_id):
    """
    Validate a Yoco checkout identifier before
    inserting it into an API endpoint.
    """

    if not isinstance(checkout_id, str):

        raise YocoValidationError(
            "Checkout ID must be a string."
        )

    checkout_id = checkout_id.strip()

    if not checkout_id:

        raise YocoValidationError(
            "Checkout ID is required."
        )

    if len(checkout_id) > 200:

        raise YocoValidationError(
            "Checkout ID is too long."
        )

    if not re.fullmatch(
        r"[A-Za-z0-9_-]+",
        checkout_id,
    ):

        raise YocoValidationError(
            "Invalid checkout ID."
        )

    return checkout_id


# ============================================================
# HTTP CLIENT
# ============================================================

def yoco_api_request(
    method,
    endpoint,
    payload=None,
):
    """
    Make an authenticated request to Yoco.

    Supported methods:
        GET
        POST

    Raises:
        YocoConfigurationError
        YocoValidationError
        YocoAPIError
    """

    secret_key = (
        get_yoco_secret_key()
    )

    # ========================================================
    # VALIDATE METHOD
    # ========================================================

    if not isinstance(method, str):

        raise YocoValidationError(
            "Invalid Yoco request method."
        )

    method = method.upper().strip()

    if method not in {
        "GET",
        "POST",
    }:

        raise YocoValidationError(
            "Unsupported Yoco request method."
        )

    # ========================================================
    # VALIDATE ENDPOINT
    # ========================================================

    if not isinstance(endpoint, str):

        raise YocoValidationError(
            "Invalid Yoco API endpoint."
        )

    if (
        not endpoint.startswith("/")
        or endpoint.startswith("//")
        or "://" in endpoint
        or "?" in endpoint
        or "#" in endpoint
        or "\\" in endpoint
    ):

        raise YocoValidationError(
            "Invalid Yoco API endpoint."
        )

    # ========================================================
    # BUILD URL
    # ========================================================

    url = (
        YOCO_API_BASE_URL.rstrip("/")
        +
        endpoint
    )

    # ========================================================
    # REQUEST HEADERS
    # ========================================================

    headers = {

        "Authorization":
            f"Bearer {secret_key}",

        "Content-Type":
            "application/json",

        "Accept":
            "application/json",

    }

    # ========================================================
    # SEND REQUEST
    # ========================================================

    try:

        response = requests.request(

            method=method,

            url=url,

            headers=headers,

            json=(
                payload
                if method == "POST"
                else None
            ),

            timeout=YOCO_REQUEST_TIMEOUT,

            allow_redirects=False,

        )

    except requests.Timeout as error:

        logger.warning(
            "[Yoco] Request timed out: %s",
            endpoint,
        )

        raise YocoAPIError(
            "Yoco did not respond in time."
        ) from error

    except requests.RequestException as error:

        logger.error(
            "[Yoco] Network request failed: %s",
            type(error).__name__,
        )

        raise YocoAPIError(
            "Could not communicate with Yoco."
        ) from error

    # ========================================================
    # VALIDATE HTTP STATUS
    # ========================================================

    if not (
        200 <= response.status_code < 300
    ):

        logger.error(
            (
                "[Yoco] API request failed: "
                "status=%s endpoint=%s"
            ),
            response.status_code,
            endpoint,
        )

        raise YocoAPIError(
            "Yoco could not process the payment request."
        )

    # ========================================================
    # VALIDATE RESPONSE SIZE
    # ========================================================

    if (
        len(response.content)
        > YOCO_MAX_RESPONSE_BYTES
    ):

        raise YocoAPIError(
            "Yoco response exceeded the allowed size."
        )

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        result = response.json()

    except ValueError as error:

        raise YocoAPIError(
            "Yoco returned invalid JSON."
        ) from error

    # ========================================================
    # VALIDATE RESPONSE STRUCTURE
    # ========================================================

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
    """
    Create a Yoco hosted checkout.

    Returns:
        checkout_id
        checkout_url
        amount_cents
        currency
        payment_reference
        raw_response

    IMPORTANT:
        A created checkout is not proof of payment.
    """

    # ========================================================
    # VALIDATE AMOUNT
    # ========================================================

    amount_cents = (
        amount_to_cents(
            amount
        )
    )

    # ========================================================
    # VALIDATE PAYMENT REFERENCE
    # ========================================================

    reference = str(
        payment_reference or ""
    ).strip()

    if (
        not reference
        or len(reference) > 100
    ):

        raise YocoValidationError(
            "A valid payment reference is required."
        )

    # ========================================================
    # VALIDATE REDIRECT URLS
    # ========================================================

    success_url = (
        validate_redirect_url(
            success_url
        )
    )

    cancel_url = (
        validate_redirect_url(
            cancel_url
        )
    )

    if failure_url:

        failure_url = (
            validate_redirect_url(
                failure_url
            )
        )

    else:

        failure_url = (
            cancel_url
        )

    # ========================================================
    # VALIDATE METADATA
    # ========================================================

    if metadata is None:

        metadata = {}

    if not isinstance(metadata, dict):

        raise YocoValidationError(
            "Checkout metadata must be a dictionary."
        )

    # ========================================================
    # BUILD CHECKOUT REQUEST
    # ========================================================

    payload = {

        "amount":
            amount_cents,

        "currency":
            YOCO_CURRENCY,

        "successUrl":
            success_url,

        "cancelUrl":
            cancel_url,

        "failureUrl":
            failure_url,

        "metadata": {

            **metadata,

            "kalxa_payment_reference":
                reference,

        },

    }

    # ========================================================
    # CREATE CHECKOUT
    # ========================================================

    result = (
        yoco_api_request(
            "POST",
            YOCO_CHECKOUT_ENDPOINT,
            payload,
        )
    )

    # ========================================================
    # EXTRACT CHECKOUT ID
    # ========================================================

    checkout_id = (
        validate_yoco_checkout_id(
            result.get("id")
        )
    )

    # ========================================================
    # EXTRACT CHECKOUT URL
    # ========================================================

    redirect_url = (
        result.get("redirectUrl")
        or ""
    )

    if not redirect_url:

        raise YocoAPIError(
            "Yoco did not return a checkout URL."
        )

    redirect_url = (
        validate_redirect_url(
            redirect_url
        )
    )

    # ========================================================
    # RETURN CHECKOUT DETAILS
    # ========================================================

    return {

        "checkout_id":
            checkout_id,

        "checkout_url":
            redirect_url,

        "amount_cents":
            amount_cents,

        "currency":
            YOCO_CURRENCY,

        "payment_reference":
            reference,

        "raw_response":
            result,

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
    """
    Create a Yoco checkout for an organizer
    SaaS subscription.
    """

    if (
        payment is None
        or organizer is None
    ):

        raise YocoValidationError(
            "Payment and organizer are required."
        )

    # ========================================================
    # VERIFY OWNERSHIP
    # ========================================================

    if (
        payment.organizer_id
        != organizer.id
    ):

        raise YocoValidationError(
            "Subscription does not belong to this organizer."
        )

    # ========================================================
    # REQUIRE PENDING PAYMENT
    # ========================================================

    if payment.payment_status != "pending":

        raise YocoValidationError(
            "Only pending subscriptions can be paid."
        )

    # ========================================================
    # CREATE CHECKOUT
    # ========================================================

    return create_yoco_checkout(

        amount=
            payment.amount,

        payment_reference=
            payment.payment_reference,

        success_url=
            success_url,

        cancel_url=
            cancel_url,

        metadata={

            "payment_type":
                "organizer_subscription",

            "subscription_payment_id":
                payment.id,

            "organizer_id":
                organizer.id,

            "account_type":
                organizer.account_type,

            "plan_name":
                payment.plan_name,

            "period_days":
                payment.period_days,

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
    """
    Create a Yoco checkout for a restaurant
    Standard/Premium subscription.
    """

    if (
        payment is None
        or advert is None
        or organizer is None
    ):

        raise YocoValidationError(
            "Payment, restaurant and organizer are required."
        )

    # ========================================================
    # VERIFY OWNERSHIP
    # ========================================================

    if (
        payment.organizer_id
        != organizer.id

        or payment.restaurant_advert_id
        != advert.id

        or advert.organizer_id
        != organizer.id
    ):

        raise YocoValidationError(
            "Restaurant subscription ownership mismatch."
        )

    # ========================================================
    # REQUIRE PENDING PAYMENT
    # ========================================================

    if payment.payment_status != "pending":

        raise YocoValidationError(
            "Only pending subscriptions can be paid."
        )

    # ========================================================
    # CREATE CHECKOUT
    # ========================================================

    return create_yoco_checkout(

        amount=
            payment.amount,

        payment_reference=
            payment.payment_reference,

        success_url=
            success_url,

        cancel_url=
            cancel_url,

        metadata={

            "payment_type":
                "restaurant_subscription",

            "restaurant_subscription_payment_id":
                payment.id,

            "restaurant_advert_id":
                advert.id,

            "organizer_id":
                organizer.id,

            "plan_tier":
                payment.plan_tier,

            "plan_name":
                payment.plan_name,

            "period_days":
                payment.period_days,

        },

    )


# ============================================================
# RETRIEVE YOCO CHECKOUT
# ============================================================

def get_yoco_checkout(checkout_id):
    """
    Retrieve an existing checkout directly from Yoco.

    Used by:
        - Webhook payment verification
        - Customer return verification
        - Subscription reconciliation

    IMPORTANT:
        The returned checkout must still be checked
        against the local payment record.

        This function does not activate subscriptions.
    """

    # ========================================================
    # VALIDATE CHECKOUT ID
    # ========================================================

    checkout_id = (
        validate_yoco_checkout_id(
            checkout_id
        )
    )

    # ========================================================
    # FETCH CHECKOUT
    # ========================================================

    checkout = (
        yoco_api_request(
            "GET",
            f"{YOCO_CHECKOUT_ENDPOINT}/{checkout_id}",
        )
    )

    # ========================================================
    # VERIFY RESPONSE CHECKOUT ID
    # ========================================================

    returned_id = (
        checkout.get("id")
    )

    if returned_id != checkout_id:

        logger.error(
            "[Yoco] Retrieved checkout ID mismatch."
        )

        raise YocoValidationError(
            "Retrieved checkout ID does not match the requested checkout."
        )

    # ========================================================
    # RETURN VERIFIED RESOURCE
    # ========================================================

    return checkout
