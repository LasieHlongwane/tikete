
import base64
import hashlib
import hmac
import json
import os
import time


class YocoWebhookError(Exception):
    pass


def verify_yoco_webhook(raw_body, headers):
    secret = os.getenv("YOCO_WEBHOOK_SECRET", "").strip()

    if not secret.startswith("whsec_"):
        raise YocoWebhookError("Webhook secret is not configured.")

    message_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signature_header = headers.get("webhook-signature", "")

    if not all((message_id, timestamp, signature_header)):
        raise YocoWebhookError("Missing webhook headers.")

    if len(raw_body) > 1024 * 1024:
        raise YocoWebhookError("Webhook body is too large.")

    try:
        timestamp_int = int(timestamp)
    except ValueError:
        raise YocoWebhookError("Invalid webhook timestamp.")

    if abs(int(time.time()) - timestamp_int) > 180:
        raise YocoWebhookError("Webhook timestamp expired.")

    try:
        signing_secret = base64.b64decode(
            secret.removeprefix("whsec_"),
            validate=True,
        )
    except Exception:
        raise YocoWebhookError("Invalid webhook secret.")

    if not signing_secret:
        raise YocoWebhookError("Empty webhook signing secret.")

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

    valid = any(
        hmac.compare_digest(
            signature.split(",", 1)[1],
            expected_signature,
        )
        for signature in signature_header.split()
        if signature.startswith("v1,")
    )

    if not valid:
        raise YocoWebhookError("Invalid webhook signature.")

    try:
        event = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        raise YocoWebhookError("Invalid webhook JSON.")

    if not isinstance(event, dict):
        raise YocoWebhookError("Invalid webhook payload.")

    return event
