# ============================================================
# KALXA TICKETING — YOCO WEBHOOK SECURITY
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
# Verify incoming Yoco webhook requests.
#
# SECURITY
# ------------------------------------------------------------
# - Uses YOCO_WEBHOOK_SECRET.
# - Validates Standard Webhooks headers.
# - Validates webhook timestamp.
# - Verifies HMAC-SHA256 signature.
# - Uses constant-time signature comparison.
# - Rejects oversized payloads.
# - Rejects invalid JSON.
#
# IMPORTANT
# ------------------------------------------------------------
# A valid webhook signature proves that the event
# was signed using the configured webhook secret.
#
# It does NOT independently prove that a checkout
# is completed or that a subscription should activate.
#
# KALXA must still verify the payment with Yoco.
#
# ============================================================

import base64
import hashlib
import hmac
import json
import os
import time


# ============================================================
# CONFIGURATION
# ============================================================

YOCO_WEBHOOK_MAX_BODY_BYTES = (
    1024 * 1024
)

YOCO_WEBHOOK_TIMESTAMP_TOLERANCE = (
    180
)


# ============================================================
# EXCEPTIONS
# ============================================================

class YocoWebhookError(Exception):
    """
    Invalid or unverifiable Yoco webhook.
    """


# ============================================================
# WEBHOOK SECRET
# ============================================================

def get_yoco_webhook_secret():
    """
    Retrieve and decode the webhook signing secret.

    Expected format:
        whsec_<base64 encoded signing key>
    """

    secret = (
        os.getenv(
            "YOCO_WEBHOOK_SECRET",
            "",
        )
        .strip()
    )

    if not secret.startswith("whsec_"):

        raise YocoWebhookError(
            "Webhook signing secret is not configured."
        )

    encoded_secret = (
        secret[len("whsec_"):]
    )

    if not encoded_secret:

        raise YocoWebhookError(
            "Webhook signing secret is empty."
        )

    try:

        signing_secret = (
            base64.b64decode(
                encoded_secret,
                validate=True,
            )
        )

    except Exception as error:

        raise YocoWebhookError(
            "Invalid webhook signing secret."
        ) from error

    if not signing_secret:

        raise YocoWebhookError(
            "Decoded webhook signing secret is empty."
        )

    return signing_secret


# ============================================================
# HEADER VALIDATION
# ============================================================

def get_yoco_webhook_headers(headers):
    """
    Extract Standard Webhooks headers.

    Required:
        webhook-id
        webhook-timestamp
        webhook-signature
    """

    if headers is None:

        raise YocoWebhookError(
            "Webhook headers are missing."
        )

    message_id = str(
        headers.get(
            "webhook-id",
            "",
        )
        or ""
    ).strip()

    timestamp = str(
        headers.get(
            "webhook-timestamp",
            "",
        )
        or ""
    ).strip()

    signature_header = str(
        headers.get(
            "webhook-signature",
            "",
        )
        or ""
    ).strip()

    if not all(
        (
            message_id,
            timestamp,
            signature_header,
        )
    ):

        raise YocoWebhookError(
            "Missing Standard Webhooks headers."
        )

    if len(message_id) > 255:

        raise YocoWebhookError(
            "Webhook message ID is too long."
        )

    if len(signature_header) > 4096:

        raise YocoWebhookError(
            "Webhook signature header is too long."
        )

    return (
        message_id,
        timestamp,
        signature_header,
    )


# ============================================================
# TIMESTAMP VERIFICATION
# ============================================================

def verify_yoco_webhook_timestamp(timestamp):
    """
    Reject webhook messages outside the allowed
    timestamp window.

    Helps limit replay attacks.
    """

    if not isinstance(timestamp, str):

        raise YocoWebhookError(
            "Invalid webhook timestamp."
        )

    if (
        not timestamp.isascii()
        or not timestamp.isdecimal()
    ):

        raise YocoWebhookError(
            "Invalid webhook timestamp."
        )

    if len(timestamp) > 20:

        raise YocoWebhookError(
            "Invalid webhook timestamp length."
        )

    try:

        timestamp_int = int(
            timestamp
        )

    except ValueError as error:

        raise YocoWebhookError(
            "Invalid webhook timestamp."
        ) from error

    current_timestamp = int(
        time.time()
    )

    difference = abs(
        current_timestamp
        -
        timestamp_int
    )

    if (
        difference
        >
        YOCO_WEBHOOK_TIMESTAMP_TOLERANCE
    ):

        raise YocoWebhookError(
            "Webhook timestamp outside allowed window."
        )

    return timestamp_int


# ============================================================
# SIGNATURE VERIFICATION
# ============================================================

def verify_yoco_webhook_signature(
    *,
    raw_body,
    message_id,
    timestamp,
    signature_header,
    signing_secret,
):
    """
    Verify the Standard Webhooks HMAC-SHA256
    signature.

    Supports multiple signature entries.

    Example header:
        v1,<signature> v1,<signature>
    """

    # ========================================================
    # CONSTRUCT SIGNED PAYLOAD
    # ========================================================

    signed_payload = (

        message_id.encode(
            "utf-8"
        )

        +

        b"."

        +

        timestamp.encode(
            "utf-8"
        )

        +

        b"."

        +

        raw_body

    )

    # ========================================================
    # CALCULATE EXPECTED SIGNATURE
    # ========================================================

    expected_signature = (
        base64.b64encode(

            hmac.new(

                signing_secret,

                signed_payload,

                hashlib.sha256,

            ).digest()

        ).decode(
            "ascii"
        )
    )

    # ========================================================
    # CHECK ALL SUPPORTED SIGNATURES
    # ========================================================

    valid_signature = False

    for entry in signature_header.split():

        version, separator, signature = (
            entry.partition(",")
        )

        if not separator:
            continue

        if version != "v1":
            continue

        if not signature:
            continue

        if hmac.compare_digest(
            signature,
            expected_signature,
        ):

            valid_signature = True

            break

    if not valid_signature:

        raise YocoWebhookError(
            "Webhook signature mismatch."
        )

    return True


# ============================================================
# MAIN WEBHOOK VERIFICATION
# ============================================================

def verify_yoco_webhook(
    raw_body,
    headers,
):
    """
    Verify an incoming Yoco webhook.

    Parameters:
        raw_body:
            Original request body as bytes.

        headers:
            Flask request.headers.

    Returns:
        Parsed webhook event dictionary.

    Raises:
        YocoWebhookError
    """

    # ========================================================
    # VALIDATE RAW BODY
    # ========================================================

    if not isinstance(
        raw_body,
        bytes,
    ):

        raise YocoWebhookError(
            "Invalid raw request body."
        )

    if not raw_body:

        raise YocoWebhookError(
            "Webhook body is empty."
        )

    if (
        len(raw_body)
        >
        YOCO_WEBHOOK_MAX_BODY_BYTES
    ):

        raise YocoWebhookError(
            "Webhook body exceeds size limit."
        )

    # ========================================================
    # EXTRACT HEADERS
    # ========================================================

    (
        message_id,
        timestamp,
        signature_header,
    ) = get_yoco_webhook_headers(
        headers
    )

    # ========================================================
    # VERIFY TIMESTAMP
    # ========================================================

    verify_yoco_webhook_timestamp(
        timestamp
    )

    # ========================================================
    # DECODE SIGNING SECRET
    # ========================================================

    signing_secret = (
        get_yoco_webhook_secret()
    )

    # ========================================================
    # VERIFY SIGNATURE
    # ========================================================

    verify_yoco_webhook_signature(

        raw_body=
            raw_body,

        message_id=
            message_id,

        timestamp=
            timestamp,

        signature_header=
            signature_header,

        signing_secret=
            signing_secret,

    )

    # ========================================================
    # DECODE JSON
    # ========================================================

    try:

        event = json.loads(
            raw_body.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        ValueError,
    ) as error:

        raise YocoWebhookError(
            "Invalid webhook JSON."
        ) from error

    # ========================================================
    # VALIDATE EVENT STRUCTURE
    # ========================================================

    if not isinstance(event, dict):

        raise YocoWebhookError(
            "Webhook event must be an object."
        )

    event_type = (
        event.get("type")
    )

    if not isinstance(
        event_type,
        str,
    ):

        raise YocoWebhookError(
            "Webhook event type is missing."
        )

    if not event_type.strip():

        raise YocoWebhookError(
            "Webhook event type is empty."
        )

    return event


# ============================================================
# WEBHOOK IDENTIFIER EXTRACTION
# ============================================================

def extract_yoco_webhook_identifiers(event):
    """
    Extract identifiers from a verified Yoco event.

    This helper does not verify payment success.

    It does not assume that a Yoco payment ID
    is interchangeable with a checkout ID.

    Returns:
        {
            "event_type": str,
            "checkout_id": str | None,
            "payment_id": str | None,
        }

    IMPORTANT:
        The caller must independently verify the
        corresponding checkout with Yoco.
    """

    if not isinstance(event, dict):

        raise YocoWebhookError(
            "Invalid webhook event."
        )

    event_type = str(
        event.get("type")
        or ""
    ).strip()

    # ========================================================
    # EVENT DATA
    # ========================================================

    data = event.get(
        "payload"
    )

    if data is None:

        data = event.get(
            "data"
        )

    if not isinstance(data, dict):

        return {

            "event_type":
                event_type,

            "checkout_id":
                None,

            "payment_id":
                None,

        }

    # ========================================================
    # CHECKOUT ID
    # ========================================================

    checkout_id = (
        data.get("checkoutId")
        or data.get("checkout_id")
    )

    checkout = data.get(
        "checkout"
    )

    if (
        not checkout_id
        and isinstance(checkout, dict)
    ):

        checkout_id = (
            checkout.get("id")
        )

    # ========================================================
    # PAYMENT ID
    # ========================================================

    payment_id = (
        data.get("paymentId")
        or data.get("payment_id")
    )

    # For payment events, data.id may identify the payment,
    # not the checkout.

    if (
        not payment_id
        and event_type.startswith("payment.")
    ):

        payment_id = (
            data.get("id")
        )

    # ========================================================
    # NORMALIZE IDENTIFIERS
    # ========================================================

    if checkout_id is not None:

        checkout_id = str(
            checkout_id
        ).strip() or None

    if payment_id is not None:

        payment_id = str(
            payment_id
        ).strip() or None

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "event_type":
            event_type,

        "checkout_id":
            checkout_id,

        "payment_id":
            payment_id,

    }
