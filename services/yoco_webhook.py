
import base64
import hashlib
import hmac
import json
import os
import time


class YocoWebhookError(Exception):
    pass


class YocoWebhookError(Exception):
    pass


def verify_yoco_webhook(raw_body, headers):
    secret = os.getenv(
        "YOCO_WEBHOOK_SECRET", ""
    ).strip()

    if not secret.startswith("whsec_"):
        raise YocoWebhookError(
            "Webhook signing secret is not configured."
        )

    if not isinstance(raw_body, bytes):
        raise YocoWebhookError(
            "Invalid raw request body."
        )

    if len(raw_body) > 1024 * 1024:
        raise YocoWebhookError(
            "Webhook body exceeds size limit."
        )

    message_id = (
        headers.get("webhook-id") or ""
    ).strip()

    timestamp = (
        headers.get("webhook-timestamp") or ""
    ).strip()

    signature_header = (
        headers.get("webhook-signature") or ""
    ).strip()

    if not all((
        message_id,
        timestamp,
        signature_header,
    )):
        raise YocoWebhookError(
            "Missing Standard Webhooks headers."
        )

    if not timestamp.isascii() or not timestamp.isdecimal():
        raise YocoWebhookError(
            "Invalid webhook timestamp."
        )

    timestamp_int = int(timestamp)

    if abs(int(time.time()) - timestamp_int) > 180:
        raise YocoWebhookError(
            "Webhook timestamp outside allowed window."
        )

    try:
        signing_secret = base64.b64decode(
            secret[len("whsec_"):],
            validate=True,
        )
    except Exception as exc:
        raise YocoWebhookError(
            "Invalid signing secret configuration."
        ) from exc

    if not signing_secret:
        raise YocoWebhookError(
            "Empty signing secret."
        )

    signed_payload = (
        message_id.encode("utf-8")
        + b"."
        + timestamp.encode("utf-8")
        + b"."
        + raw_body
    )

    expected_signature = base64.b64encode(
        hmac.new(
            signing_secret,
            signed_payload,
            hashlib.sha256,
        ).digest()
    ).decode("ascii")

    valid = False

    for entry in signature_header.split():
        version, separator, signature = entry.partition(",")

        if (
            separator
            and version == "v1"
            and signature
            and hmac.compare_digest(
                signature,
                expected_signature,
            )
        ):
            valid = True
            break

    if not valid:
        raise YocoWebhookError(
            "Signature mismatch."
        )

    try:
        event = json.loads(
            raw_body.decode("utf-8")
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise YocoWebhookError(
            "Invalid webhook JSON."
        ) from exc

    if not isinstance(event, dict):
        raise YocoWebhookError(
            "Webhook event must be an object."
        )

    return event

