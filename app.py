# ============================================================
# KALXA TICKETING - APP
# ============================================================

import io
import hashlib
import hmac
import json
import math
import os
import secrets
import threading
import time
import string
import uuid
import urllib.error
import urllib.parse
import urllib.request
import requests
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal, InvalidOperation, ROUND_UP
from zoneinfo import ZoneInfo

import qrcode

import firebase_admin
from firebase_admin import (
    credentials,
    messaging,
)

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_migrate import Migrate
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    URLSafeTimedSerializer,
)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from models import (
    AttendeeContact,
    CheckIn,
    EntryPass,
    EventBoost,
    EventBoostReminder,
    GeocodedArea,
    KalxaBridgeTokenUse,
    Organizer,
    PushCampaign,
    PushDelivery,
    PushSubscription,
    SubscriptionPayment,
    TicketEvent,
    TicketOrder,
    TicketOrderItem,
    TicketType,
    db,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# KALXA EVENT BOOST
# ============================================================

EVENT_BOOST_BASIC_PRICE = Decimal(
    os.environ.get(
        "EVENT_BOOST_BASIC_PRICE",
        "49.00",
    )
)

EVENT_BOOST_PRO_PRICE = Decimal(
    os.environ.get(
        "EVENT_BOOST_PRO_PRICE",
        "99.00",
    )
)

EVENT_BOOST_RADIUS_KM = Decimal(
    os.environ.get(
        "LOCAL_NOTIFICATION_RADIUS_KM",
        "80",
    )
)

BOOST_CRON_SECRET = (
    os.environ.get(
        "BOOST_CRON_SECRET",
        "",
    )
    .strip()
)

EVENT_BOOST_PLANS = {
    "basic": {
        "name":
            "KALXA EVENT BOOST",
        "price":
            EVENT_BOOST_BASIC_PRICE,
        "campaign_limit":
            1,
        "reminders": [
            "launch",
        ],
    },

    "pro": {
        "name":
            "EVENT BOOST PRO",
        "price":
            EVENT_BOOST_PRO_PRICE,
        "campaign_limit":
            5,
        "reminders": [
            "launch",
            "three_days",
            "tomorrow",
            "tonight",
            "happening_now",
        ],
    },
}


# ============================================================
# LOCAL EVENT NOTIFICATION TARGETING
# ============================================================

LOCAL_NOTIFICATION_RADIUS_KM = float(
    os.environ.get(
        "LOCAL_NOTIFICATION_RADIUS_KM",
        "60",
    )
)

NOMINATIM_BASE_URL = (
    os.environ.get(
        "NOMINATIM_BASE_URL",
        "https://nominatim.openstreetmap.org",
    )
    .strip()
    .rstrip("/")
)

NOMINATIM_USER_AGENT = (
    os.environ.get(
        "NOMINATIM_USER_AGENT",
        "Kalxa-Ticketing/1.0",
    )
    .strip()
)

_nominatim_lock = threading.Lock()
_nominatim_last_request_at = 0.0


# ============================================================
# PAYSTACK
# ============================================================

PAYSTACK_SECRET_KEY = (
    os.environ.get("PAYSTACK_SECRET_KEY", "").strip()
)

PAYSTACK_BASE_URL = "https://api.paystack.co"

# Pay-by-Bank checkout is now enabled.
#
# South African Paystack EFT / Capitec Pay pricing is currently
# 2% excluding VAT. 15% VAT on the processing charge gives an
# effective default fee rate of 2.3%.
#
# Keep this configurable so a pricing change does not require
# an application code change.
PAYSTACK_EFT_EFFECTIVE_FEE_RATE = Decimal(
    os.environ.get(
        "PAYSTACK_EFT_EFFECTIVE_FEE_RATE",
        "0.023",
    )
)


def calculate_paystack_checkout_amount(
    ticket_face_value,
):

    face_value = Decimal(
        str(
            ticket_face_value
            or 0
        )
    ).quantize(
        Decimal("0.01")
    )


    if face_value <= 0:

        return (
            Decimal("0.00"),
            Decimal("0.00"),
        )


    rate = (
        PAYSTACK_EFT_EFFECTIVE_FEE_RATE
    )


    if (
        rate < 0
        or rate >= 1
    ):

        raise RuntimeError(
            "Invalid Paystack processing fee rate."
        )


    # Paystack's guidance for passing a percentage fee is to
    # gross up the price so the intended settlement remains
    # after the processing charge. ROUND_UP ensures the
    # organizer is never short by a cent due to rounding.
    checkout_amount = (
        (
            face_value
            /
            (
                Decimal("1.00")
                - rate
            )
        )
        + Decimal("0.01")
    ).quantize(
        Decimal("0.01"),
        rounding=
            ROUND_UP,
    )


    processing_fee = (
        checkout_amount
        - face_value
    ).quantize(
        Decimal("0.01")
    )


    return (
        checkout_amount,
        processing_fee,
    )


def paystack_is_configured():

    return bool(PAYSTACK_SECRET_KEY)


def paystack_api_request(
    method,
    path,
    payload=None,
):

    if not paystack_is_configured():

        raise RuntimeError(
            "PAYSTACK_SECRET_KEY is not configured."
        )


    url = (
        f"{PAYSTACK_BASE_URL}{path}"
    )


    headers = {
        "Authorization":
            f"Bearer {PAYSTACK_SECRET_KEY}",

        "Accept":
            "application/json",

        "Content-Type":
            "application/json",

        # Avoid Python urllib's default HTTP signature,
        # which Cloudflare can classify as a banned
        # browser/bot signature on api.paystack.co.
        "User-Agent":
            "Kalxa-Ticketing/1.0",
    }


    try:

        response = requests.request(
            method=
                method.upper(),

            url=
                url,

            json=(
                payload
                if payload is not None
                else None
            ),

            headers=
                headers,

            timeout=
                20,
        )


    except requests.RequestException as error:

        raise RuntimeError(
            (
                "Could not connect to Paystack. "
                "Please try again."
            )
        ) from error


    try:

        result = (
            response.json()
        )


    except ValueError:

        result = {
            "status":
                False,

            "message":
                (
                    response.text
                    or (
                        "Paystack returned an "
                        "invalid response."
                    )
                ),
        }


    if not response.ok:

        message = (
            result.get(
                "message"
            )
            if isinstance(
                result,
                dict,
            )
            else None
        )


        if not message:

            message = (
                response.text
                or (
                    f"HTTP {response.status_code}"
                )
            )


        raise RuntimeError(
            f"Paystack: {message}"
        )


    if not isinstance(
        result,
        dict,
    ):

        raise RuntimeError(
            "Paystack returned an invalid response."
        )


    if not result.get(
        "status"
    ):

        raise RuntimeError(
            result.get(
                "message"
            )
            or "Paystack request failed."
        )


    return result


def finalize_paystack_ticket_order(
    order,
    transaction_data,
):

    if (
        order.payment_status
        == "paid"
    ):

        return order


    if (
        not isinstance(
            transaction_data,
            dict,
        )
        or transaction_data.get(
            "status"
        )
        != "success"
    ):

        raise RuntimeError(
            "Paystack transaction is not successful."
        )


    reference = (
        str(
            transaction_data.get(
                "reference",
                "",
            )
        )
        .strip()
    )


    if (
        reference
        != order.payment_reference
    ):

        raise RuntimeError(
            "Paystack reference does not match this order."
        )


    expected_amount = int(
        (
            Decimal(
                str(
                    order.checkout_amount
                    or order.total_amount
                )
            )
            * 100
        )
        .quantize(
            Decimal("1"),
            rounding=
                ROUND_UP,
        )
    )


    actual_amount = int(
        transaction_data.get(
            "amount"
        )
        or 0
    )


    if (
        actual_amount
        != expected_amount
    ):

        raise RuntimeError(
            "Paystack amount does not match this order."
        )


    currency = (
        str(
            transaction_data.get(
                "currency",
                "",
            )
        )
        .strip()
        .upper()
    )


    if (
        currency
        and currency != "ZAR"
    ):

        raise RuntimeError(
            "Unexpected Paystack payment currency."
        )


    order.payment_status = (
        "paid"
    )

    order.paid_at = (
        datetime.utcnow()
    )

    order.payment_verified_at = (
        datetime.utcnow()
    )

    order.paystack_transaction_id = (
        str(
            transaction_data.get(
                "id",
                "",
            )
        )
        or None
    )

    order.payment_channel = (
        transaction_data.get(
            "channel"
        )
        or None
    )


    if order.order_items:

        for item in order.order_items:

            existing_item_passes = len(
                item.entry_passes
            )

            passes_to_create = max(
                0,
                item.quantity
                - existing_item_passes,
            )


            for _ in range(
                passes_to_create
            ):

                db.session.add(
                    EntryPass(
                        order_id=
                            order.id,

                        order_item_id=
                            item.id,

                        entry_code=
                            generate_entry_code(),

                        status=
                            "valid",
                    )
                )


    else:

        # Backward compatibility for legacy single-price orders.
        existing_pass_count = len(
            order.entry_passes
        )

        passes_to_create = max(
            0,
            order.quantity
            - existing_pass_count,
        )


        for _ in range(
            passes_to_create
        ):

            db.session.add(
                EntryPass(
                    order_id=
                        order.id,

                    entry_code=
                        generate_entry_code(),

                    status=
                        "valid",
                )
            )


    db.session.commit()


    return order


def finalize_paystack_subscription_payment(
    payment,
    transaction_data,
):

    if (
        payment.payment_status
        == "paid"
    ):

        return payment


    if (
        not isinstance(
            transaction_data,
            dict,
        )
        or transaction_data.get(
            "status"
        )
        != "success"
    ):

        raise RuntimeError(
            "Paystack subscription transaction is not successful."
        )


    reference = (
        str(
            transaction_data.get(
                "reference",
                "",
            )
        )
        .strip()
    )


    if (
        reference
        != payment.payment_reference
    ):

        raise RuntimeError(
            "Paystack subscription reference does not match."
        )


    expected_amount = int(
        (
            Decimal(
                str(
                    payment.amount
                    or 0
                )
            )
            * 100
        )
        .quantize(
            Decimal("1"),
            rounding=
                ROUND_UP,
        )
    )


    actual_amount = int(
        transaction_data.get(
            "amount"
        )
        or 0
    )


    if (
        actual_amount
        != expected_amount
    ):

        raise RuntimeError(
            "Paystack subscription amount does not match."
        )


    currency = (
        str(
            transaction_data.get(
                "currency",
                "",
            )
        )
        .strip()
        .upper()
    )


    if (
        currency
        and currency != "ZAR"
    ):

        raise RuntimeError(
            "Unexpected subscription payment currency."
        )


    organizer = (
        payment.organizer
    )


    if not organizer:

        raise RuntimeError(
            "Subscription organizer record is missing."
        )


    if organizer.is_suspended:

        raise RuntimeError(
            "Suspended organizers cannot activate subscriptions."
        )


    now = (
        datetime.utcnow()
    )


    if (
        organizer.subscription_expires_at
        and organizer.subscription_expires_at
        > now
    ):

        subscription_start = (
            organizer.subscription_expires_at
        )

    else:

        subscription_start = now


    subscription_end = (
        subscription_start
        + timedelta(
            days=(
                payment.period_days
                or KALXA_SUBSCRIPTION_PERIOD_DAYS
            )
        )
    )


    payment.payment_method = (
        "paystack"
    )

    payment.payment_status = (
        "paid"
    )

    payment.paid_at = now

    payment.confirmed_at = now

    payment.confirmed_by = (
        "paystack"
    )

    payment.subscription_start = (
        subscription_start
    )

    payment.subscription_end = (
        subscription_end
    )

    payment.payment_verified_at = (
        now
    )

    payment.paystack_transaction_id = (
        str(
            transaction_data.get(
                "id",
                "",
            )
        )
        or None
    )

    payment.payment_channel = (
        transaction_data.get(
            "channel"
        )
        or None
    )


    organizer.active = True

    organizer.subscription_status = (
        "active"
    )


    if (
        organizer.subscription_started_at
        is None
    ):

        organizer.subscription_started_at = (
            now
        )


    organizer.subscription_expires_at = (
        subscription_end
    )


    db.session.commit()


    return payment


def get_paystack_za_banks():

    query = urllib.parse.urlencode(
        {
            "currency":
                "ZAR",

            "perPage":
                100,
        }
    )

    result = paystack_api_request(
        "GET",
        f"/bank?{query}",
    )

    banks = (
        result.get("data")
        or []
    )

    filtered_banks = []

    for bank in banks:

        if (
            bank.get("active")
            is False
        ):
            continue

        currency = (
            str(
                bank.get(
                    "currency",
                    "",
                )
            )
            .strip()
            .upper()
        )

        if (
            currency
            and currency != "ZAR"
        ):
            continue

        filtered_banks.append(
            bank
        )

    filtered_banks.sort(
        key=lambda bank:
            str(
                bank.get(
                    "name",
                    "",
                )
            )
            .lower()
    )

    return filtered_banks


# ============================================================
# APP
# ============================================================

app = Flask(
    __name__
)


# ============================================================
# SECRET KEY
# ============================================================

app.config[
    "SECRET_KEY"
] = os.environ.get(
    "SECRET_KEY"
)


if not app.config[
    "SECRET_KEY"
]:

    raise RuntimeError(
        "SECRET_KEY is not configured."
    )


# ============================================================
# SESSION COOKIE CONFIGURATION
# ============================================================
#
# Render serves the production app over HTTPS.
# These settings make organizer login cookies explicit and
# stable across the login -> dashboard redirect.
# ============================================================

app.config[
    "SESSION_COOKIE_HTTPONLY"
] = True

app.config[
    "SESSION_COOKIE_SAMESITE"
] = "Lax"

app.config[
    "SESSION_COOKIE_SECURE"
] = (
    os.environ.get(
        "RENDER",
        ""
    )
    .strip()
    .lower()
    in {
        "1",
        "true",
        "yes",
    }
)


# ============================================================
# DATABASE
# ============================================================

database_url = os.environ.get(
    "DATABASE_URL"
)


if not database_url:

    raise RuntimeError(
        (
            "DATABASE_URL is not configured. "
            "Kalxa Ticketing requires PostgreSQL."
        )
    )


# ============================================================
# POSTGRESQL + PSYCOPG COMPATIBILITY
# ============================================================

if database_url.startswith(
    "postgres://"
):

    database_url = (
        database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )
    )


elif database_url.startswith(
    "postgresql://"
):

    database_url = (
        database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    )


# ============================================================
# SQLALCHEMY
# ============================================================

app.config[
    "SQLALCHEMY_DATABASE_URI"
] = database_url

app.config[
    "SQLALCHEMY_TRACK_MODIFICATIONS"
] = False

app.config[
    "SQLALCHEMY_ENGINE_OPTIONS"
] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

db.init_app(
    app
)

migrate = Migrate(
    app,
    db,
)


# ============================================================
# PUBLIC BASE URL
# ============================================================

PUBLIC_BASE_URL = (
    os.environ.get(
        "PUBLIC_BASE_URL",
        "http://127.0.0.1:5001",
    )
    .rstrip("/")
)

# ============================================================
# FIREBASE WEB PUSH
# ============================================================
#
# These values come from:
# Firebase Console -> Project Settings -> Your Web App
#
# FIREBASE_VAPID_KEY comes from:
# Project Settings -> Cloud Messaging -> Web Push certificates
#
# These are browser-facing Firebase web configuration values.
# The private Firebase service-account credentials are NOT
# required until Stage 2, when Kalxa starts sending campaigns.
# ============================================================

FIREBASE_WEB_CONFIG = {

    "apiKey": (
        os.environ.get(
            "FIREBASE_API_KEY",
            "",
        )
        .strip()
    ),

    "authDomain": (
        os.environ.get(
            "FIREBASE_AUTH_DOMAIN",
            "",
        )
        .strip()
    ),

    "projectId": (
        os.environ.get(
            "FIREBASE_PROJECT_ID",
            "",
        )
        .strip()
    ),

    "storageBucket": (
        os.environ.get(
            "FIREBASE_STORAGE_BUCKET",
            "",
        )
        .strip()
    ),

    "messagingSenderId": (
        os.environ.get(
            "FIREBASE_MESSAGING_SENDER_ID",
            "",
        )
        .strip()
    ),

    "appId": (
        os.environ.get(
            "FIREBASE_APP_ID",
            "",
        )
        .strip()
    ),
}


FIREBASE_VAPID_KEY = (
    os.environ.get(
        "FIREBASE_VAPID_KEY",
        "",
    )
    .strip()
)


def firebase_web_push_configured():

    required_values = (
        FIREBASE_WEB_CONFIG.get(
            "apiKey"
        ),
        FIREBASE_WEB_CONFIG.get(
            "projectId"
        ),
        FIREBASE_WEB_CONFIG.get(
            "messagingSenderId"
        ),
        FIREBASE_WEB_CONFIG.get(
            "appId"
        ),
        FIREBASE_VAPID_KEY,
    )


    return all(
        required_values
    )





# ============================================================
# FIREBASE ADMIN / SERVER-SIDE PUSH
# ============================================================
#
# Render environment variable:
#
# FIREBASE_SERVICE_ACCOUNT_JSON
#
# Value:
# Complete JSON contents of a Firebase service-account key.
#
# The Admin SDK is initialized lazily so normal ticketing pages
# continue to work even if server-side push is not configured.
# ============================================================

FIREBASE_SERVICE_ACCOUNT_JSON = (
    os.environ.get(
        "FIREBASE_SERVICE_ACCOUNT_JSON",
        "",
    )
    .strip()
)


def firebase_admin_configured():

    return bool(
        FIREBASE_SERVICE_ACCOUNT_JSON
        and FIREBASE_WEB_CONFIG.get(
            "projectId"
        )
    )


def get_firebase_admin_app():

    if not firebase_admin_configured():

        raise RuntimeError(
            (
                "FIREBASE_SERVICE_ACCOUNT_JSON "
                "is not configured."
            )
        )


    try:

        return firebase_admin.get_app()


    except ValueError:

        pass


    try:

        service_account_info = (
            json.loads(
                FIREBASE_SERVICE_ACCOUNT_JSON
            )
        )


    except json.JSONDecodeError as error:

        raise RuntimeError(
            (
                "FIREBASE_SERVICE_ACCOUNT_JSON "
                "contains invalid JSON."
            )
        ) from error


    project_id = (
        FIREBASE_WEB_CONFIG.get(
            "projectId"
        )
        or service_account_info.get(
            "project_id"
        )
    )


    credential = (
        credentials.Certificate(
            service_account_info
        )
    )


    return firebase_admin.initialize_app(
        credential,
        {
            "projectId":
                project_id,
        },
    )


def is_dead_firebase_registration(
    error,
):

    if not error:

        return False


    error_name = (
        error.__class__.__name__
        .strip()
        .lower()
    )


    error_code = (
        str(
            getattr(
                error,
                "code",
                "",
            )
            or ""
        )
        .strip()
        .lower()
    )


    error_text = (
        str(
            error
        )
        .strip()
        .lower()
    )


    dead_markers = (
        "unregistered",
        "registration-token-not-registered",
        "not-found",
        "requested entity was not found",
        "404",
    )


    combined = (
        f"{error_name} "
        f"{error_code} "
        f"{error_text}"
    )


    return any(
        marker in combined
        for marker in dead_markers
    )


def get_active_push_subscriptions():

    return (
        PushSubscription.query

        .outerjoin(
            AttendeeContact,
            PushSubscription.contact_id
            == AttendeeContact.id,
        )

        .filter(
            PushSubscription.active
            .is_(True)
        )

        .filter(
            PushSubscription.disabled_at
            .is_(None)
        )

        .filter(
            db.or_(
                # Device-only subscriber from the public
                # Kalxa home page.
                PushSubscription.contact_id
                .is_(None),

                # Identified ticket buyer who explicitly
                # consented to notifications.
                db.and_(
                    AttendeeContact.notification_consent
                    .is_(True),

                    AttendeeContact.opted_out_at
                    .is_(None),
                ),
            )
        )

        .order_by(
            PushSubscription.id.asc()
        )

        .all()
    )


def send_push_campaign(
    campaign,
    subscriptions,
):

    firebase_app = (
        get_firebase_admin_app()
    )


    now = (
        datetime.utcnow()
    )


    campaign.status = (
        "processing"
    )

    campaign.recipient_count = (
        len(
            subscriptions
        )
    )

    campaign.success_count = 0
    campaign.failure_count = 0


    db.session.flush()


    # ========================================================
    # FCM MULTICAST LIMIT
    # ========================================================
    #
    # Firebase accepts up to 500 FIDs in one multicast call.
    # ========================================================

    batch_size = 500


    for start in range(
        0,
        len(subscriptions),
        batch_size,
    ):

        batch = (
            subscriptions[
                start:
                start + batch_size
            ]
        )


        fids = [
            subscription.firebase_installation_id
            for subscription in batch
        ]


        message = messaging.MulticastMessage(

            notification=
                messaging.Notification(
                    title=
                        campaign.title,

                    body=
                        campaign.body,
                ),

            data={
                "campaign_id":
                    str(
                        campaign.id
                    ),
            },

            webpush=
                messaging.WebpushConfig(

                    fcm_options=
                        messaging.WebpushFCMOptions(
                            link=(
                                campaign.target_url
                                or PUBLIC_BASE_URL
                            ),
                        ),
                ),

            fids=
                fids,
        )


        try:

            response = (
                messaging.send_each_for_multicast(
                    message,
                    app=
                        firebase_app,
                )
            )


        except Exception as error:

            current_app.logger.exception(
                (
                    "[Push Campaign] Firebase "
                    "multicast request failed "
                    "campaign_id=%s error=%s"
                ),
                campaign.id,
                error,
            )


            for subscription in batch:

                delivery = PushDelivery(

                    campaign_id=
                        campaign.id,

                    push_subscription_id=
                        subscription.id,

                    firebase_installation_id=
                        subscription.firebase_installation_id,

                    status=
                        "failed",

                    error_message=
                        str(error)[:2000],
                )


                db.session.add(
                    delivery
                )


                campaign.failure_count += 1


            continue


        for (
            subscription,
            send_response,
        ) in zip(
            batch,
            response.responses,
        ):

            if send_response.success:

                delivery = PushDelivery(

                    campaign_id=
                        campaign.id,

                    push_subscription_id=
                        subscription.id,

                    firebase_installation_id=
                        subscription.firebase_installation_id,

                    status=
                        "sent",

                    firebase_message_id=
                        send_response.message_id,

                    sent_at=
                        now,
                )


                campaign.success_count += 1


            else:

                error = (
                    send_response.exception
                )


                delivery = PushDelivery(

                    campaign_id=
                        campaign.id,

                    push_subscription_id=
                        subscription.id,

                    firebase_installation_id=
                        subscription.firebase_installation_id,

                    status=
                        "failed",

                    error_message=(
                        str(error)[:2000]
                        if error
                        else
                        "Unknown Firebase send error."
                    ),
                )


                campaign.failure_count += 1


                if (
                    is_dead_firebase_registration(
                        error
                    )
                ):

                    subscription.active = (
                        False
                    )

                    subscription.disabled_at = (
                        now
                    )


            db.session.add(
                delivery
            )


    campaign.sent_at = (
        now
    )


    if (
        campaign.success_count
        > 0
        and campaign.failure_count
        == 0
    ):

        campaign.status = (
            "completed"
        )


    elif (
        campaign.success_count
        > 0
        and campaign.failure_count
        > 0
    ):

        campaign.status = (
            "partial"
        )


    else:

        campaign.status = (
            "failed"
        )


    db.session.commit()


    return campaign


# ============================================================
# EVENT BOOST HELPERS
# ============================================================

def generate_event_boost_reference():

    return (
        "KXBOOST-"
        + secrets.token_hex(
            6
        ).upper()
    )


def event_local_datetime(
    event,
):

    if (
        not event.event_date
        or not event.event_time
    ):

        return None


    return datetime.combine(
        event.event_date,
        event.event_time,
    ).replace(
        tzinfo=
            ZoneInfo(
                "Africa/Johannesburg"
            )
    )


def event_datetime_utc_naive(
    event,
):

    local_datetime = (
        event_local_datetime(
            event
        )
    )


    if not local_datetime:

        return None


    return (
        local_datetime
        .astimezone(
            timezone.utc
        )
        .replace(
            tzinfo=None
        )
    )


def event_boost_plan(
    plan_code,
):

    plan = (
        EVENT_BOOST_PLANS.get(
            str(
                plan_code
                or ""
            )
            .strip()
            .lower()
        )
    )


    if not plan:

        raise ValueError(
            "Invalid event boost plan."
        )


    return plan


def build_event_boost_schedule(
    boost,
):

    event = (
        boost.event
    )


    if not event:

        raise RuntimeError(
            "Boost event is missing."
        )


    plan = (
        event_boost_plan(
            boost.plan_code
        )
    )


    now = (
        datetime.utcnow()
    )


    event_utc = (
        event_datetime_utc_naive(
            event
        )
    )


    reminder_times = {
        "launch":
            now,
    }


    if boost.plan_code == "pro":

        if not event_utc:

            raise RuntimeError(
                "Pro boost requires an event date and time."
            )


        event_local = (
            event_local_datetime(
                event
            )
        )


        # Same-day reminder:
        # - evening events: 17:00 SAST ("Tonight")
        # - daytime events: 09:00 SAST ("Today")
        # - very early events: one hour before start
        if event_local.hour >= 17:

            same_day_local = (
                event_local.replace(
                    hour=17,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            )

        else:

            same_day_local = (
                event_local.replace(
                    hour=9,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            )


        if same_day_local >= event_local:

            same_day_local = (
                event_local
                - timedelta(
                    hours=1
                )
            )


        same_day_utc = (
            same_day_local
            .astimezone(
                timezone.utc
            )
            .replace(
                tzinfo=None
            )
        )


        reminder_times.update(
            {
                "three_days":
                    event_utc
                    - timedelta(
                        days=3
                    ),

                "tomorrow":
                    event_utc
                    - timedelta(
                        days=1
                    ),

                "tonight":
                    same_day_utc,

                "happening_now":
                    event_utc,
            }
        )


    existing_types = {
        reminder.reminder_type
        for reminder in boost.reminders
    }


    for reminder_type in plan[
        "reminders"
    ]:

        if (
            reminder_type
            in existing_types
        ):

            continue


        scheduled_for = (
            reminder_times[
                reminder_type
            ]
        )


        status = (
            "pending"
        )


        # Never send a countdown that is already obsolete.
        if (
            reminder_type
            != "launch"
            and scheduled_for
            <= now
        ):

            status = (
                "skipped"
            )


        db.session.add(
            EventBoostReminder(
                boost_id=
                    boost.id,

                reminder_type=
                    reminder_type,

                scheduled_for=
                    scheduled_for,

                status=
                    status,

                error_message=(
                    "Scheduled time had already passed "
                    "when the boost was activated."
                    if status == "skipped"
                    else None
                ),
            )
        )


def format_boost_schedule_sast(
    scheduled_for,
):

    if not scheduled_for:

        return "—"


    aware_utc = (
        scheduled_for.replace(
            tzinfo=
                timezone.utc
        )
    )


    local_time = (
        aware_utc.astimezone(
            ZoneInfo(
                "Africa/Johannesburg"
            )
        )
    )


    return (
        local_time.strftime(
            "%d %b %Y %H:%M"
        )
        + " SAST"
    )


def build_local_audience_analytics(
    event,
    radius_km,
):

    if (
        event.notification_latitude is None
        or event.notification_longitude is None
    ):

        return {
            "total":
                0,
            "average_distance_km":
                None,
            "nearest_distance_km":
                None,
            "farthest_distance_km":
                None,
            "areas":
                [],
        }


    area_buckets = {}
    distances = []


    for subscription in (
        get_active_push_subscriptions()
    ):

        if (
            subscription.home_latitude is None
            or subscription.home_longitude is None
        ):

            continue


        distance = (
            haversine_distance_km(
                event.notification_latitude,
                event.notification_longitude,
                subscription.home_latitude,
                subscription.home_longitude,
            )
        )


        if distance > float(
            radius_km
        ):

            continue


        distances.append(
            distance
        )


        area_name = (
            subscription.home_area
            or subscription.home_location_display
            or "Unknown area"
        )


        bucket_key = (
            normalize_area_key(
                area_name
            )
            or "unknown-area"
        )


        bucket = (
            area_buckets.setdefault(
                bucket_key,
                {
                    "name":
                        area_name,
                    "count":
                        0,
                    "distances":
                        [],
                },
            )
        )


        bucket[
            "count"
        ] += 1

        bucket[
            "distances"
        ].append(
            distance
        )


    areas = []


    for bucket in (
        area_buckets.values()
    ):

        bucket_distances = (
            bucket[
                "distances"
            ]
        )


        areas.append(
            {
                "name":
                    bucket[
                        "name"
                    ],

                "count":
                    bucket[
                        "count"
                    ],

                "average_distance_km":
                    round(
                        (
                            sum(
                                bucket_distances
                            )
                            /
                            len(
                                bucket_distances
                            )
                        ),
                        1,
                    ),
            }
        )


    areas.sort(
        key=lambda row: (
            -row[
                "count"
            ],
            row[
                "average_distance_km"
            ],
            row[
                "name"
            ].casefold(),
        )
    )


    if not distances:

        return {
            "total":
                0,
            "average_distance_km":
                None,
            "nearest_distance_km":
                None,
            "farthest_distance_km":
                None,
            "areas":
                [],
        }


    return {
        "total":
            len(
                distances
            ),

        "average_distance_km":
            round(
                sum(
                    distances
                )
                /
                len(
                    distances
                ),
                1,
            ),

        "nearest_distance_km":
            round(
                min(
                    distances
                ),
                1,
            ),

        "farthest_distance_km":
            round(
                max(
                    distances
                ),
                1,
            ),

        "areas":
            areas,
    }


def event_boost_notification_copy(
    event,
    reminder_type,
):

    area = (
        event.notification_area
        or event.venue
        or "your area"
    )


    if reminder_type == "launch":

        return (
            f"🔥 {event.title}",
            (
                f"{event.title} is coming to {area}. "
                "Tap to view event details and tickets."
            ),
        )


    if reminder_type == "three_days":

        return (
            f"🔥 3 DAYS TO GO: {event.title}",
            (
                f"Only 3 days until {event.title} in {area}. "
                "Tap to get your ticket."
            ),
        )


    if reminder_type == "tomorrow":

        return (
            f"⏰ TOMORROW: {event.title}",
            (
                f"{event.title} is happening tomorrow in {area}. "
                "Tap for tickets and event details."
            ),
        )


    if reminder_type == "tonight":

        event_local = (
            event_local_datetime(
                event
            )
        )


        if (
            event_local
            and event_local.hour >= 17
        ):

            return (
                f"🌙 TONIGHT: {event.title}",
                (
                    f"{event.title} is happening tonight in {area}. "
                    "Tap for tickets and event details."
                ),
            )


        return (
            f"📍 TODAY: {event.title}",
            (
                f"{event.title} is happening today in {area}. "
                "Tap for tickets and event details."
            ),
        )


    if reminder_type == "happening_now":

        return (
            f"🔴 HAPPENING NOW: {event.title}",
            (
                f"{event.title} is happening now in {area}. "
                "Tap to open the event."
            ),
        )


    raise ValueError(
        "Unknown boost reminder type."
    )


def execute_event_boost_reminder(
    reminder,
):

    reminder_id = (
        reminder.id
    )


    # Atomically claim one pending reminder.
    # If two workers/cron calls overlap, only one is allowed
    # to change pending -> processing.
    claimed = (
        EventBoostReminder.query
        .filter(
            EventBoostReminder.id
            == reminder_id,
            EventBoostReminder.status
            == "pending",
        )
        .update(
            {
                EventBoostReminder.status:
                    "processing",

                EventBoostReminder.error_message:
                    None,
            },
            synchronize_session=
                False,
        )
    )


    db.session.commit()


    if not claimed:

        return (
            db.session.get(
                EventBoostReminder,
                reminder_id,
            )
        )


    reminder = (
        db.session.get(
            EventBoostReminder,
            reminder_id,
        )
    )


    boost = (
        reminder.boost
    )


    event = (
        boost.event
        if boost
        else None
    )


    if (
        not boost
        or not boost.is_active
        or not event
    ):

        reminder.status = (
            "skipped"
        )

        reminder.error_message = (
            "Boost or event is not active."
        )

        db.session.commit()

        return reminder


    if (
        event.status
        != "published"
        or not event.active
    ):

        reminder.status = (
            "skipped"
        )

        reminder.error_message = (
            "Event is not currently published."
        )

        db.session.commit()

        return reminder


    subscriptions = (
        get_local_push_subscriptions(
            event,
            float(
                boost.radius_km
            ),
        )
    )


    if not subscriptions:

        reminder.status = (
            "skipped"
        )

        reminder.error_message = (
            "No eligible local notification audience."
        )

        db.session.commit()

        return reminder


    (
        title,
        body,
    ) = (
        event_boost_notification_copy(
            event,
            reminder.reminder_type,
        )
    )


    campaign = PushCampaign(

        event_id=
            event.id,

        title=
            title[:120],

        body=
            body[:500],

        target_url=
            url_for(
                "event_page",
                event_id=
                    event.id,
                _external=
                    True,
            ),

        target_mode=
            "radius",

        target_area=
            event.notification_area,

        target_latitude=
            event.notification_latitude,

        target_longitude=
            event.notification_longitude,

        radius_km=
            boost.radius_km,

        status=
            "draft",

        recipient_count=
            len(
                subscriptions
            ),

        created_by=(
            "event_boost:"
            + boost.plan_code
            + ":"
            + reminder.reminder_type
        ),
    )


    db.session.add(
        campaign
    )

    db.session.flush()


    reminder.campaign_id = (
        campaign.id
    )


    db.session.commit()


    try:

        send_push_campaign(
            campaign,
            subscriptions,
        )


    except Exception as error:

        db.session.rollback()


        reminder = (
            db.session.get(
                EventBoostReminder,
                reminder.id,
            )
        )


        if reminder:

            reminder.status = (
                "failed"
            )

            reminder.error_message = (
                str(
                    error
                )[:2000]
            )

            db.session.commit()


        raise


    reminder = (
        db.session.get(
            EventBoostReminder,
            reminder.id,
        )
    )


    reminder.status = (
        "sent"
    )

    reminder.sent_at = (
        datetime.utcnow()
    )

    reminder.error_message = (
        None
    )


    db.session.commit()


    return reminder


def process_due_event_boost_reminders(
    boost_id=None,
    limit=25,
):

    query = (
        EventBoostReminder.query
        .join(
            EventBoost,
            EventBoostReminder.boost_id
            == EventBoost.id,
        )
        .filter(
            EventBoost.status
            == "active"
        )
        .filter(
            EventBoostReminder.status
            == "pending"
        )
        .filter(
            EventBoostReminder.scheduled_for
            <= datetime.utcnow()
        )
    )


    if boost_id is not None:

        query = query.filter(
            EventBoostReminder.boost_id
            == boost_id
        )


    reminders = (
        query
        .order_by(
            EventBoostReminder.scheduled_for.asc()
        )
        .limit(
            limit
        )
        .all()
    )


    result = {
        "processed":
            0,

        "sent":
            0,

        "skipped":
            0,

        "failed":
            0,
    }


    for reminder in reminders:

        result[
            "processed"
        ] += 1


        try:

            execute_event_boost_reminder(
                reminder
            )


            db.session.refresh(
                reminder
            )


            if reminder.status == "sent":

                result[
                    "sent"
                ] += 1

            elif reminder.status == "skipped":

                result[
                    "skipped"
                ] += 1


        except Exception as error:

            result[
                "failed"
            ] += 1


            current_app.logger.exception(
                (
                    "[Event Boost] Reminder failed "
                    "reminder_id=%s error=%s"
                ),
                reminder.id,
                error,
            )


    return result


def finalize_event_boost_payment(
    boost,
    transaction_data,
):

    if boost.status == "active":

        return boost


    if (
        not isinstance(
            transaction_data,
            dict,
        )
        or transaction_data.get(
            "status"
        )
        != "success"
    ):

        raise RuntimeError(
            "Paystack boost transaction is not successful."
        )


    reference = str(
        transaction_data.get(
            "reference",
            "",
        )
    ).strip()


    if reference != boost.payment_reference:

        raise RuntimeError(
            "Paystack boost reference does not match."
        )


    expected_amount = int(
        (
            Decimal(
                str(
                    boost.price
                )
            )
            * 100
        )
        .quantize(
            Decimal("1"),
            rounding=
                ROUND_UP,
        )
    )


    actual_amount = int(
        transaction_data.get(
            "amount"
        )
        or 0
    )


    if actual_amount != expected_amount:

        raise RuntimeError(
            "Paystack boost amount does not match."
        )


    currency = str(
        transaction_data.get(
            "currency",
            "",
        )
    ).strip().upper()


    if (
        currency
        and currency != "ZAR"
    ):

        raise RuntimeError(
            "Unexpected boost payment currency."
        )


    now = datetime.utcnow()


    boost.status = (
        "active"
    )

    boost.paid_at = (
        now
    )

    boost.activated_at = (
        now
    )

    boost.payment_verified_at = (
        now
    )

    boost.paystack_transaction_id = (
        str(
            transaction_data.get(
                "id",
                "",
            )
        )
        or None
    )

    boost.payment_channel = (
        transaction_data.get(
            "channel"
        )
        or None
    )


    build_event_boost_schedule(
        boost
    )


    db.session.commit()


    return boost


# ============================================================
# ORGANIZER SESSION
# ============================================================

ORGANIZER_SESSION_KEY = (
    "ticketing_organizer_id"
)


# ============================================================
# SUPER ADMIN SESSION
# ============================================================

SUPERADMIN_SESSION_KEY = (
    "ticketing_superadmin"
)


# ============================================================
# SUPER ADMIN CREDENTIAL CONFIG
# ============================================================
#
# Configure these in Render:
#
# SUPERADMIN_EMAIL
# SUPERADMIN_PASSWORD_HASH
#
# Generate a password hash locally with:
#
# python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_PASSWORD'))"
# ============================================================

SUPERADMIN_EMAIL = (
    os.environ.get(
        "SUPERADMIN_EMAIL",
        "",
    )
    .strip()
    .lower()
)

SUPERADMIN_PASSWORD_HASH = (
    os.environ.get(
        "SUPERADMIN_PASSWORD_HASH",
        "",
    )
    .strip()
)


# ============================================================
# KALXA ORGANIZER SUBSCRIPTION PLAN
# ============================================================
#
# These values describe money paid by organizers to Kalxa.
#
# This subscription-payment configuration is separate from
# attendee ticket payments. Attendee ticket payments are now
# Paystack-only and never expose organizer bank details.
# ============================================================

KALXA_SUBSCRIPTION_PLAN_NAME = (
    os.environ.get(
        "KALXA_SUBSCRIPTION_PLAN_NAME",
        "Kalxa Organizer Monthly",
    )
    .strip()
)

try:

    KALXA_SUBSCRIPTION_PRICE = Decimal(
        os.environ.get(
            "KALXA_SUBSCRIPTION_PRICE",
            "199.00",
        )
    )

except InvalidOperation:

    raise RuntimeError(
        "KALXA_SUBSCRIPTION_PRICE must be a valid number."
    )


KALXA_SUBSCRIPTION_PERIOD_DAYS = 30


KALXA_SUBSCRIPTION_BANK = {

    "bank_name": (
        os.environ.get(
            "KALXA_BANK_NAME",
            "",
        )
        .strip()
    ),

    "account_holder": (
        os.environ.get(
            "KALXA_ACCOUNT_HOLDER",
            "",
        )
        .strip()
    ),

    "account_number": (
        os.environ.get(
            "KALXA_ACCOUNT_NUMBER",
            "",
        )
        .strip()
    ),

    "branch_code": (
        os.environ.get(
            "KALXA_BRANCH_CODE",
            "",
        )
        .strip()
    ),

    "instructions": (
        os.environ.get(
            "KALXA_SUBSCRIPTION_PAYMENT_INSTRUCTIONS",
            "",
        )
        .strip()
    ),
}


# ============================================================
# TICKET TYPE FORM HELPERS
# ============================================================

def parse_ticket_type_form(
    form,
):

    ids = form.getlist(
        "ticket_type_id"
    )

    names = form.getlist(
        "ticket_type_name"
    )

    prices = form.getlist(
        "ticket_type_price"
    )

    capacities = form.getlist(
        "ticket_type_capacity"
    )


    count = max(
        len(names),
        len(prices),
        len(capacities),
        len(ids),
    )


    if (
        count < 1
        or count > 10
    ):

        raise ValueError(
            "Choose between 1 and 10 ticket types."
        )


    rows = []
    seen_names = set()


    for index in range(
        count
    ):

        raw_id = (
            ids[index].strip()
            if index < len(ids)
            else ""
        )

        name = (
            names[index].strip()
            if index < len(names)
            else ""
        )

        raw_price = (
            prices[index].strip()
            if index < len(prices)
            else ""
        )

        raw_capacity = (
            capacities[index].strip()
            if index < len(capacities)
            else ""
        )


        if not name:

            raise ValueError(
                "Every ticket type needs a name."
            )


        key = name.casefold()


        if key in seen_names:

            raise ValueError(
                "Ticket type names must be unique."
            )


        seen_names.add(
            key
        )


        try:

            price = Decimal(
                raw_price
                or "0"
            ).quantize(
                Decimal("0.01")
            )


        except InvalidOperation as error:

            raise ValueError(
                f"Enter a valid price for {name}."
            ) from error


        if price < 0:

            raise ValueError(
                f"{name} price cannot be negative."
            )


        capacity = None


        if raw_capacity:

            try:

                capacity = int(
                    raw_capacity
                )

            except ValueError as error:

                raise ValueError(
                    f"Enter a valid capacity for {name}."
                ) from error


            if capacity < 1:

                raise ValueError(
                    f"{name} capacity must be at least 1."
                )


        ticket_type_id = None


        if raw_id:

            try:

                ticket_type_id = int(
                    raw_id
                )

            except ValueError:

                raise ValueError(
                    "Invalid ticket type identifier."
                )


        rows.append(
            {
                "id":
                    ticket_type_id,

                "name":
                    name,

                "price":
                    price,

                "capacity":
                    capacity,

                "sort_order":
                    index,
            }
        )


    return rows


def sync_event_legacy_ticket_summary(
    event,
    ticket_rows,
):

    event.ticket_price = min(
        row["price"]
        for row in ticket_rows
    )


    if all(
        row["capacity"]
        is not None
        for row in ticket_rows
    ):

        event.ticket_capacity = sum(
            row["capacity"]
            for row in ticket_rows
        )

    else:

        event.ticket_capacity = None


# ============================================================
# AREA GEOCODING + DISTANCE
# ============================================================

def normalize_area_key(value):

    return " ".join(
        str(value or "")
        .strip()
        .casefold()
        .split()
    )


def geocode_area(area_text):

    global _nominatim_last_request_at

    area = str(area_text or "").strip()

    if not area or len(area) > 200:
        raise ValueError("Enter a valid area or town.")

    query_key = normalize_area_key(area)

    cached = (
        GeocodedArea.query
        .filter_by(query_key=query_key)
        .first()
    )

    if cached:
        return cached

    search_text = area

    if "south africa" not in area.casefold():
        search_text = f"{area}, South Africa"

    with _nominatim_lock:

        elapsed = (
            time.monotonic()
            - _nominatim_last_request_at
        )

        if elapsed < 1.05:
            time.sleep(1.05 - elapsed)

        try:

            response = requests.get(
                NOMINATIM_BASE_URL + "/search",
                params={
                    "q": search_text,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "za",
                    "addressdetails": 1,
                },
                headers={
                    "User-Agent":
                        NOMINATIM_USER_AGENT,
                    "Accept":
                        "application/json",
                },
                timeout=15,
            )

            _nominatim_last_request_at = (
                time.monotonic()
            )

            response.raise_for_status()

            results = response.json() or []

        except (
            requests.RequestException,
            ValueError,
        ) as error:

            raise RuntimeError(
                "Location lookup is temporarily unavailable. "
                "Please try again."
            ) from error

    if not results:

        raise ValueError(
            "We could not find that South African area or town. "
            "Try a nearby town name."
        )

    result = results[0]

    try:

        latitude = float(result["lat"])
        longitude = float(result["lon"])

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:

        raise RuntimeError(
            "The location service returned an invalid result."
        ) from error

    cached = GeocodedArea(
        query_key=query_key,
        query_text=area,
        display_name=str(
            result.get("display_name", area)
        )[:500],
        latitude=latitude,
        longitude=longitude,
        provider="nominatim",
    )

    try:

        db.session.add(cached)
        db.session.commit()

    except Exception:

        db.session.rollback()

        cached = (
            GeocodedArea.query
            .filter_by(query_key=query_key)
            .first()
        )

        if not cached:
            raise

    return cached


def haversine_distance_km(
    latitude_1,
    longitude_1,
    latitude_2,
    longitude_2,
):

    earth_radius_km = 6371.0088

    lat1 = math.radians(float(latitude_1))
    lon1 = math.radians(float(longitude_1))
    lat2 = math.radians(float(latitude_2))
    lon2 = math.radians(float(longitude_2))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    value = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    central_angle = (
        2
        * math.atan2(
            math.sqrt(value),
            math.sqrt(1 - value),
        )
    )

    return earth_radius_km * central_angle


def get_local_push_subscriptions(
    event,
    radius_km=None,
):

    radius = float(
        radius_km
        if radius_km is not None
        else LOCAL_NOTIFICATION_RADIUS_KM
    )

    if (
        event.notification_latitude is None
        or event.notification_longitude is None
    ):
        return []

    local_subscriptions = []

    for subscription in get_active_push_subscriptions():

        if (
            subscription.home_latitude is None
            or subscription.home_longitude is None
        ):
            continue

        distance = haversine_distance_km(
            event.notification_latitude,
            event.notification_longitude,
            subscription.home_latitude,
            subscription.home_longitude,
        )

        if distance <= radius:
            local_subscriptions.append(subscription)

    return local_subscriptions


# ============================================================
# NORMALIZE EMAIL
# ============================================================

def normalize_email(
    value,
):

    return (
        str(
            value
            or ""
        )
        .strip()
        .lower()
    )


# ============================================================
# NORMALIZE ATTENDEE PHONE FOR AUDIENCE
# ============================================================

def normalize_attendee_phone(
    value,
):

    raw = (
        str(
            value
            or ""
        )
        .strip()
    )


    digits = "".join(
        character
        for character in raw
        if character.isdigit()
    )


    if (
        len(digits)
        == 10
        and digits.startswith(
            "0"
        )
    ):

        return (
            "+27"
            + digits[1:]
        )


    if (
        len(digits)
        == 11
        and digits.startswith(
            "27"
        )
    ):

        return (
            "+"
            + digits
        )


    if raw.startswith(
        "+"
    ) and digits:

        return (
            "+"
            + digits
        )


    return digits


# ============================================================
# CURRENT ORGANIZER
# ============================================================

def get_current_organizer():

    organizer_id = (
        session.get(
            ORGANIZER_SESSION_KEY
        )
    )


    if not organizer_id:

        return None


    try:

        organizer_id = int(
            organizer_id
        )


    except (
        TypeError,
        ValueError,
    ):

        session.pop(
            ORGANIZER_SESSION_KEY,
            None,
        )

        return None


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if (
        not organizer
        or not organizer.active
    ):

        session.pop(
            ORGANIZER_SESSION_KEY,
            None,
        )

        return None


    return organizer


# ============================================================
# REQUIRE ORGANIZER
# ============================================================

def require_ticketing_organizer():

    organizer = (
        get_current_organizer()
    )


    if organizer:

        return None


    flash(
        (
            "Please sign in to your "
            "Kalxa Ticketing organizer account."
        ),
        "error",
    )


    return redirect(
        url_for(
            "organizer_login"
        )
    )


# ============================================================
# REQUIRE ACTIVE ORGANIZER SUBSCRIPTION
# ============================================================

def require_active_subscription(
    organizer,
):

    if (
        organizer
        and organizer.is_subscription_active
    ):

        return None


    if organizer:

        status = (
            organizer.effective_subscription_status
        )

    else:

        status = "inactive"


    flash(
        (
            "Your Kalxa Ticketing subscription is "
            f"{status}. An active subscription is "
            "required to create new events."
        ),
        "error",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# CURRENT SUPER ADMIN
# ============================================================

def is_superadmin_authenticated():

    return (
        session.get(
            SUPERADMIN_SESSION_KEY
        )
        is True
    )


# ============================================================
# REQUIRE SUPER ADMIN
# ============================================================

def require_superadmin():

    if is_superadmin_authenticated():

        return None


    flash(
        "Please sign in as Kalxa Super Admin.",
        "error",
    )


    return redirect(
        url_for(
            "superadmin_login"
        )
    )


# ============================================================
# OPTIONAL DISCOVERY CONTEXT
# ============================================================

def get_ticketing_content_item_id():

    content_item_id = (
        session.get(
            "kalxa_content_item_id"
        )
    )


    if not content_item_id:

        return None


    try:

        return int(
            content_item_id
        )


    except (
        TypeError,
        ValueError,
    ):

        session.pop(
            "kalxa_content_item_id",
            None,
        )

        return None


def get_ticketing_legacy_kalxa_organizer_id():

    organizer_id = (
        session.get(
            "kalxa_organizer_id"
        )
    )


    if not organizer_id:

        return None


    try:

        return int(
            organizer_id
        )


    except (
        TypeError,
        ValueError,
    ):

        session.pop(
            "kalxa_organizer_id",
            None,
        )

        return None


# ============================================================
# UNIQUE PAYMENT REFERENCE
# ============================================================

def generate_payment_reference():

    alphabet = (
        string.ascii_uppercase
        +
        string.digits
    )


    while True:

        suffix = "".join(
            secrets.choice(
                alphabet
            )
            for _ in range(8)
        )


        reference = (
            f"KALXA-{suffix}"
        )


        exists = (
            TicketOrder.query
            .filter_by(
                payment_reference=
                    reference
            )
            .first()
        )


        if not exists:

            return reference


# ============================================================
# UNIQUE SUBSCRIPTION PAYMENT REFERENCE
# ============================================================

def generate_subscription_payment_reference():

    alphabet = (
        string.ascii_uppercase
        +
        string.digits
    )


    while True:

        suffix = "".join(
            secrets.choice(
                alphabet
            )
            for _ in range(8)
        )


        reference = (
            f"KALXA-SUB-{suffix}"
        )


        exists = (
            SubscriptionPayment.query
            .filter_by(
                payment_reference=
                    reference
            )
            .first()
        )


        if not exists:

            return reference


# ============================================================
# UNIQUE ENTRY CODE
# ============================================================

def generate_entry_code():

    alphabet = (
        string.ascii_uppercase
        +
        string.digits
    )


    while True:

        part_one = "".join(
            secrets.choice(
                alphabet
            )
            for _ in range(4)
        )


        part_two = "".join(
            secrets.choice(
                alphabet
            )
            for _ in range(4)
        )


        code = (
            f"KX-{part_one}-{part_two}"
        )


        exists = (
            EntryPass.query
            .filter_by(
                entry_code=code
            )
            .first()
        )


        if not exists:

            return code


# ============================================================
# SUPER ADMIN LOGIN
# ============================================================

@app.route(
    "/superadmin/login",
    methods=[
        "GET",
        "POST",
    ],
)
def superadmin_login():

    if is_superadmin_authenticated():

        return redirect(
            url_for(
                "superadmin_dashboard"
            )
        )


    if request.method == "POST":

        email = normalize_email(
            request.form.get(
                "email",
                "",
            )
        )


        password = (
            request.form.get(
                "password",
                ""
            )
        )


        if (
            not SUPERADMIN_EMAIL
            or not SUPERADMIN_PASSWORD_HASH
        ):

            current_app.logger.error(
                (
                    "[Super Admin] Missing "
                    "SUPERADMIN_EMAIL or "
                    "SUPERADMIN_PASSWORD_HASH."
                )
            )


            flash(
                (
                    "Super Admin credentials are not "
                    "configured on the server."
                ),
                "error",
            )


            return render_template(
                "superadmin/login.html"
            )


        email_ok = (
            secrets.compare_digest(
                email,
                SUPERADMIN_EMAIL,
            )
        )


        password_ok = (
            check_password_hash(
                SUPERADMIN_PASSWORD_HASH,
                password,
            )
            if password
            else False
        )


        if (
            not email_ok
            or not password_ok
        ):

            current_app.logger.warning(
                (
                    "[Super Admin] Invalid login "
                    "attempt email=%s"
                ),
                email,
            )


            flash(
                "Invalid Super Admin credentials.",
                "error",
            )


            return render_template(
                "superadmin/login.html"
            )


        session.clear()


        session[
            SUPERADMIN_SESSION_KEY
        ] = True


        session.permanent = True


        current_app.logger.info(
            "[Super Admin] Login successful."
        )


        return redirect(
            url_for(
                "superadmin_dashboard"
            )
        )


    return render_template(
        "superadmin/login.html"
    )


# ============================================================
# SUPER ADMIN LOGOUT
# ============================================================

@app.route(
    "/superadmin/logout"
)
def superadmin_logout():

    session.clear()


    return redirect(
        url_for(
            "superadmin_login"
        )
    )


# ============================================================
# SUPER ADMIN DASHBOARD
# ============================================================

@app.route(
    "/superadmin"
)
def superadmin_dashboard():

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    now = (
        datetime.utcnow()
    )


    total_organizers = (
        Organizer.query.count()
    )


    active_subscriptions = (
        Organizer.query
        .filter(
            Organizer.active.is_(True)
        )
        .filter(
            Organizer.subscription_status
            == "active"
        )
        .filter(
            Organizer.subscription_expires_at
            > now
        )
        .count()
    )


    suspended_organizers = (
        Organizer.query
        .filter(
            Organizer.subscription_status
            == "suspended"
        )
        .count()
    )


    inactive_or_expired = (
        total_organizers
        - active_subscriptions
        - suspended_organizers
    )


    recent_organizers = (
        Organizer.query
        .order_by(
            Organizer.created_at.desc()
        )
        .limit(10)
        .all()
    )


    pending_subscription_payments = (
        SubscriptionPayment.query
        .filter_by(
            payment_status=
                "pending"
        )
        .order_by(
            SubscriptionPayment.created_at.asc()
        )
        .limit(20)
        .all()
    )


    pending_subscription_count = (
        SubscriptionPayment.query
        .filter_by(
            payment_status=
                "pending"
        )
        .count()
    )


    # ========================================================
    # NEWLY PUBLISHED EVENTS READY FOR PUSH PROMOTION
    # ========================================================
    #
    # An event remains in this queue until it has at least one
    # completed/partial push campaign.
    #
    # failed campaigns do NOT remove the event from the queue,
    # so Super Admin can retry.
    # ========================================================

    promoted_event_ids = (
        db.session.query(
            PushCampaign.event_id
        )
        .filter(
            PushCampaign.event_id.isnot(
                None
            )
        )
        .filter(
            PushCampaign.status.in_(
                [
                    "completed",
                    "partial",
                ]
            )
        )
        .distinct()
        .subquery()
    )


    notification_ready_events = (
        TicketEvent.query
        .filter(
            TicketEvent.status
            == "published"
        )
        .filter(
            TicketEvent.active.is_(
                True
            )
        )
        .filter(
            ~TicketEvent.id.in_(
                db.select(
                    promoted_event_ids.c.event_id
                )
            )
        )
        .order_by(
            TicketEvent.published_at.desc(),
            TicketEvent.created_at.desc(),
        )
        .limit(20)
        .all()
    )


    notification_ready_count = (
        len(
            notification_ready_events
        )
    )


    active_push_audience_count = (
        len(
            get_active_push_subscriptions()
        )
    )


    return render_template(
        "superadmin/dashboard.html",

        total_organizers=
            total_organizers,

        active_subscriptions=
            active_subscriptions,

        suspended_organizers=
            suspended_organizers,

        inactive_or_expired=
            max(
                0,
                inactive_or_expired,
            ),

        recent_organizers=
            recent_organizers,

        pending_subscription_payments=
            pending_subscription_payments,

        pending_subscription_count=
            pending_subscription_count,

        notification_ready_events=
            notification_ready_events,

        notification_ready_count=
            notification_ready_count,

        active_push_audience_count=
            active_push_audience_count,

        subscription_plan_name=
            KALXA_SUBSCRIPTION_PLAN_NAME,

        subscription_price=
            KALXA_SUBSCRIPTION_PRICE,
    )




# ============================================================
# SUPER ADMIN - PUSH NOTIFICATION CENTRE
# ============================================================

@app.route(
    "/superadmin/notifications"
)
def superadmin_notifications():

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    active_subscriptions = (
        get_active_push_subscriptions()
    )


    audience_count = (
        len(
            active_subscriptions
        )
    )


    opted_in_contacts = (
        AttendeeContact.query
        .filter(
            AttendeeContact.notification_consent
            .is_(True)
        )
        .filter(
            AttendeeContact.opted_out_at
            .is_(None)
        )
        .count()
    )


    published_events = (
        TicketEvent.query
        .filter_by(
            status=
                "published",

            active=
                True,
        )
        .order_by(
            TicketEvent.published_at.desc(),
            TicketEvent.created_at.desc(),
        )
        .limit(50)
        .all()
    )


    campaigns = (
        PushCampaign.query
        .order_by(
            PushCampaign.created_at.desc()
        )
        .limit(30)
        .all()
    )


    selected_event = None


    selected_event_id = request.args.get(
        "event_id",
        type=int,
    )


    if selected_event_id:

        selected_event = (
            TicketEvent.query
            .filter_by(
                id=
                    selected_event_id,

                status=
                    "published",

                active=
                    True,
            )
            .first()
        )


    local_audience_counts = {
        event.id:
            len(
                get_local_push_subscriptions(
                    event,
                    LOCAL_NOTIFICATION_RADIUS_KM,
                )
            )
        for event in published_events
    }

    selected_local_audience_count = (
        local_audience_counts.get(
            selected_event.id,
            0,
        )
        if selected_event
        else 0
    )


    return render_template(
        "superadmin/notifications.html",

        audience_count=
            audience_count,

        opted_in_contacts=
            opted_in_contacts,

        published_events=
            published_events,

        campaigns=
            campaigns,

        selected_event=
            selected_event,

        firebase_admin_ready=
            firebase_admin_configured(),

        local_audience_counts=
            local_audience_counts,

        selected_local_audience_count=
            selected_local_audience_count,

        local_notification_radius_km=
            LOCAL_NOTIFICATION_RADIUS_KM,
    )


# ============================================================
# SUPER ADMIN - SEND PUSH NOTIFICATION
# ============================================================

@app.route(
    "/superadmin/notifications/send",
    methods=[
        "POST",
    ],
)
def superadmin_send_notification():

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    if not firebase_admin_configured():

        flash(
            (
                "Server-side Firebase sending is not "
                "configured. Add "
                "FIREBASE_SERVICE_ACCOUNT_JSON "
                "to Render first."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications"
            )
        )


    event_id = request.form.get(
        "event_id",
        type=int,
    )


    title = (
        request.form.get(
            "title",
            "",
        )
        .strip()
    )


    body = (
        request.form.get(
            "body",
            "",
        )
        .strip()
    )


    if not event_id:

        flash(
            "Choose a published event.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications"
            )
        )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            status=
                "published",

            active=
                True,
        )
        .first()
    )


    if not event:

        flash(
            (
                "The selected event is not "
                "currently published."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications"
            )
        )


    if not title:

        flash(
            "Notification title is required.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    if not body:

        flash(
            "Notification message is required.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    if len(title) > 120:

        flash(
            (
                "Notification title must be "
                "120 characters or fewer."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    if len(body) > 500:

        flash(
            (
                "Notification message must be "
                "500 characters or fewer."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    if (
        event.notification_latitude is None
        or event.notification_longitude is None
    ):

        flash(
            "This event does not have a resolved "
            "notification area yet. Edit the event first.",
            "error",
        )

        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=event.id,
            )
        )

    subscriptions = (
        get_local_push_subscriptions(
            event,
            LOCAL_NOTIFICATION_RADIUS_KM,
        )
    )

    if not subscriptions:

        flash(
            (
                "No active notification subscribers are "
                f"within {LOCAL_NOTIFICATION_RADIUS_KM:g} km "
                "of this event."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    target_url = (
        url_for(
            "event_page",
            event_id=
                event.id,

            _external=
                True,
        )
    )


    campaign = PushCampaign(

        event_id=
            event.id,

        title=
            title,

        body=
            body,

        target_url=
            target_url,

        target_mode=
            "radius",

        target_area=
            event.notification_area,

        target_latitude=
            event.notification_latitude,

        target_longitude=
            event.notification_longitude,

        radius_km=
            Decimal(
                str(
                    LOCAL_NOTIFICATION_RADIUS_KM
                )
            ),

        status=
            "draft",

        recipient_count=
            len(
                subscriptions
            ),

        created_by=
            "superadmin",
    )


    try:

        db.session.add(
            campaign
        )

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Push Campaign] Failed to "
                "create campaign event_id=%s "
                "error=%s"
            ),
            event.id,
            error,
        )


        flash(
            (
                "Notification campaign could not "
                "be created."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    try:

        send_push_campaign(
            campaign,
            subscriptions,
        )


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Push Campaign] Send failed "
                "campaign_id=%s error=%s"
            ),
            campaign.id,
            error,
        )


        campaign = (
            db.session.get(
                PushCampaign,
                campaign.id,
            )
        )


        if campaign:

            campaign.status = (
                "failed"
            )


            try:

                db.session.commit()

            except Exception:

                db.session.rollback()


        flash(
            (
                "Firebase could not send the "
                "notification campaign. Check "
                "the Render logs for the error."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",
                event_id=
                    event.id,
            )
        )


    if campaign.failure_count:

        flash(
            (
                "Notification campaign finished. "
                f"{campaign.success_count} sent, "
                f"{campaign.failure_count} failed."
            ),
            "success",
        )


    else:

        flash(
            (
                "Notification sent successfully "
                f"to {campaign.success_count} "
                "browser subscription(s)."
            ),
            "success",
        )


    return redirect(
        url_for(
            "superadmin_notifications",
            event_id=
                event.id,
        )
    )


# ============================================================
# SUPER ADMIN - ALL ORGANIZERS
# ============================================================

@app.route(
    "/superadmin/organizers"
)
def superadmin_organizers():

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    organizers = (
        Organizer.query
        .order_by(
            Organizer.created_at.desc()
        )
        .all()
    )


    return render_template(
        "superadmin/organizers.html",
        organizers=
            organizers,
    )


# ============================================================
# SUPER ADMIN - ORGANIZER PROFILE
# ============================================================

@app.route(
    "/superadmin/organizers/<int:organizer_id>"
)
def superadmin_organizer_detail(
    organizer_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if not organizer:

        abort(404)


    events = (
        TicketEvent.query
        .filter_by(
            organizer_id=
                organizer.id,

            organizer_deleted=
                False,
        )
        .order_by(
            TicketEvent.created_at.desc()
        )
        .all()
    )


    orders = (
        TicketOrder.query
        .join(
            TicketEvent,
            TicketOrder.event_id
            == TicketEvent.id,
        )
        .filter(
            TicketEvent.organizer_id
            == organizer.id
        )
        .order_by(
            TicketOrder.created_at.desc()
        )
        .all()
    )


    paid_orders = sum(
        1
        for order in orders
        if order.payment_status
        == "paid"
    )


    paid_tickets = sum(
        (
            order.quantity
            or 0
        )
        for order in orders
        if order.payment_status
        == "paid"
    )


    subscription_payments = (
        SubscriptionPayment.query
        .filter_by(
            organizer_id=
                organizer.id
        )
        .order_by(
            SubscriptionPayment.created_at.desc()
        )
        .all()
    )


    return render_template(
        "superadmin/organizer_detail.html",

        organizer=
            organizer,

        events=
            events,

        orders=
            orders,

        paid_orders=
            paid_orders,

        paid_tickets=
            paid_tickets,

        subscription_payments=
            subscription_payments,

        subscription_plan_name=
            KALXA_SUBSCRIPTION_PLAN_NAME,

        subscription_price=
            KALXA_SUBSCRIPTION_PRICE,
    )


# ============================================================
# SUPER ADMIN - CONFIRM SUBSCRIPTION PAYMENT
# ============================================================

@app.route(
    "/superadmin/subscription-payments/<int:payment_id>/confirm",
    methods=[
        "POST",
    ],
)
def superadmin_confirm_subscription_payment(
    payment_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    payment = (
        db.session.get(
            SubscriptionPayment,
            payment_id,
        )
    )


    if not payment:

        abort(404)


    organizer = (
        payment.organizer
    )


    if not organizer:

        abort(404)


    if (
        payment.payment_method
        == "paystack"
    ):

        flash(
            (
                "Paystack subscription payments are verified "
                "automatically and cannot be manually confirmed."
            ),
            "error",
        )

        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    if (
        payment.payment_status
        == "paid"
    ):

        flash(
            "This subscription payment is already confirmed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    if (
        payment.payment_status
        != "pending"
    ):

        flash(
            (
                "Only pending subscription payments "
                "can be confirmed."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    if organizer.is_suspended:

        flash(
            (
                "Reactivate this organizer before "
                "confirming subscription payment."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    now = (
        datetime.utcnow()
    )


    if (
        organizer.subscription_expires_at
        and organizer.subscription_expires_at
        > now
    ):

        subscription_start = (
            organizer.subscription_expires_at
        )

    else:

        subscription_start = now


    subscription_end = (
        subscription_start
        + timedelta(
            days=payment.period_days
            or KALXA_SUBSCRIPTION_PERIOD_DAYS
        )
    )


    payment.payment_status = (
        "paid"
    )

    payment.paid_at = now

    payment.confirmed_at = now

    payment.confirmed_by = (
        "superadmin"
    )

    payment.subscription_start = (
        subscription_start
    )

    payment.subscription_end = (
        subscription_end
    )


    organizer.active = True

    organizer.subscription_status = (
        "active"
    )


    if not organizer.subscription_started_at:

        organizer.subscription_started_at = (
            now
        )


    organizer.subscription_expires_at = (
        subscription_end
    )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Super Admin] Failed to confirm "
                "subscription payment payment_id=%s "
                "organizer_id=%s error=%s"
            ),
            payment.id,
            organizer.id,
            error,
        )


        flash(
            "Subscription payment confirmation failed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    flash(
        (
            "Subscription payment confirmed. "
            f"Access is active until "
            f"{subscription_end.strftime('%d %B %Y')}."
        ),
        "success",
    )


    return redirect(
        url_for(
            "superadmin_organizer_detail",
            organizer_id=
                organizer.id,
        )
    )


# ============================================================
# SUPER ADMIN - CANCEL SUBSCRIPTION PAYMENT
# ============================================================

@app.route(
    "/superadmin/subscription-payments/<int:payment_id>/cancel",
    methods=[
        "POST",
    ],
)
def superadmin_cancel_subscription_payment(
    payment_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    payment = (
        db.session.get(
            SubscriptionPayment,
            payment_id,
        )
    )


    if not payment:

        abort(404)


    organizer = (
        payment.organizer
    )


    if (
        payment.payment_status
        != "pending"
    ):

        flash(
            (
                "Only pending subscription payments "
                "can be cancelled."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    payment.payment_status = (
        "cancelled"
    )

    payment.confirmed_at = (
        datetime.utcnow()
    )

    payment.confirmed_by = (
        "superadmin"
    )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Super Admin] Failed to cancel "
                "subscription payment payment_id=%s "
                "error=%s"
            ),
            payment.id,
            error,
        )


        flash(
            "Subscription payment cancellation failed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    flash(
        "Pending subscription payment cancelled.",
        "success",
    )


    return redirect(
        url_for(
            "superadmin_organizer_detail",
            organizer_id=
                organizer.id,
        )
    )


# ============================================================
# SUPER ADMIN - ACTIVATE / EXTEND SUBSCRIPTION
# ============================================================

@app.route(
    "/superadmin/organizers/<int:organizer_id>/activate",
    methods=[
        "POST",
    ],
)
def superadmin_activate_subscription(
    organizer_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if not organizer:

        abort(404)


    if (
        organizer.subscription_status
        == "suspended"
        or not organizer.active
    ):

        flash(
            (
                "Reactivate this organizer account "
                "before activating the subscription."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    days = request.form.get(
        "days",
        30,
        type=int,
    )


    if (
        not days
        or days < 1
        or days > 3650
    ):

        flash(
            (
                "Subscription extension must be "
                "between 1 and 3650 days."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    now = (
        datetime.utcnow()
    )


    if (
        organizer.subscription_expires_at
        and organizer.subscription_expires_at
        > now
    ):

        base_date = (
            organizer.subscription_expires_at
        )

    else:

        base_date = now


    if not organizer.subscription_started_at:

        organizer.subscription_started_at = (
            now
        )


    organizer.subscription_expires_at = (
        base_date
        + timedelta(
            days=days
        )
    )


    organizer.subscription_status = (
        "active"
    )


    organizer.active = True


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Super Admin] Failed to activate "
                "subscription organizer_id=%s error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            "Subscription update failed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    flash(
        (
            f"Subscription activated/extended "
            f"by {days} day(s)."
        ),
        "success",
    )


    return redirect(
        url_for(
            "superadmin_organizer_detail",
            organizer_id=
                organizer.id,
        )
    )


# ============================================================
# SUPER ADMIN - SET EXACT EXPIRY DATE
# ============================================================

@app.route(
    "/superadmin/organizers/<int:organizer_id>/set-expiry",
    methods=[
        "POST",
    ],
)
def superadmin_set_subscription_expiry(
    organizer_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if not organizer:

        abort(404)


    expiry_raw = (
        request.form.get(
            "subscription_expires_on",
            "",
        )
        .strip()
    )


    try:

        expiry_date = (
            datetime.strptime(
                expiry_raw,
                "%Y-%m-%d",
            )
        )


        expiry_at = (
            expiry_date.replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=0,
            )
        )


    except ValueError:

        flash(
            "Please enter a valid expiry date.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    organizer.subscription_expires_at = (
        expiry_at
    )


    now = (
        datetime.utcnow()
    )


    if (
        organizer.subscription_status
        != "suspended"
        and organizer.active
    ):

        if expiry_at > now:

            organizer.subscription_status = (
                "active"
            )


            if not organizer.subscription_started_at:

                organizer.subscription_started_at = (
                    now
                )

        else:

            organizer.subscription_status = (
                "expired"
            )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Super Admin] Failed to set "
                "subscription expiry organizer_id=%s "
                "error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            "Subscription expiry update failed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    flash(
        "Subscription expiry date updated.",
        "success",
    )


    return redirect(
        url_for(
            "superadmin_organizer_detail",
            organizer_id=
                organizer.id,
        )
    )


# ============================================================
# SUPER ADMIN - SUSPEND ORGANIZER
# ============================================================

@app.route(
    "/superadmin/organizers/<int:organizer_id>/suspend",
    methods=[
        "POST",
    ],
)
def superadmin_suspend_organizer(
    organizer_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if not organizer:

        abort(404)


    reason = (
        request.form.get(
            "reason",
            "",
        )
        .strip()
        or "Suspended by Kalxa Super Admin."
    )


    organizer.active = False

    organizer.subscription_status = (
        "suspended"
    )

    organizer.suspended_at = (
        datetime.utcnow()
    )

    organizer.suspension_reason = (
        reason
    )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Super Admin] Failed to suspend "
                "organizer_id=%s error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            "Organizer suspension failed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    flash(
        "Organizer suspended.",
        "success",
    )


    return redirect(
        url_for(
            "superadmin_organizer_detail",
            organizer_id=
                organizer.id,
        )
    )


# ============================================================
# SUPER ADMIN - REACTIVATE ORGANIZER
# ============================================================

@app.route(
    "/superadmin/organizers/<int:organizer_id>/reactivate",
    methods=[
        "POST",
    ],
)
def superadmin_reactivate_organizer(
    organizer_id,
):

    auth = (
        require_superadmin()
    )


    if auth:

        return auth


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if not organizer:

        abort(404)


    organizer.active = True

    organizer.suspended_at = None

    organizer.suspension_reason = None


    now = (
        datetime.utcnow()
    )


    if (
        organizer.subscription_expires_at
        and organizer.subscription_expires_at
        > now
    ):

        organizer.subscription_status = (
            "active"
        )

    elif organizer.subscription_expires_at:

        organizer.subscription_status = (
            "expired"
        )

    else:

        organizer.subscription_status = (
            "inactive"
        )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Super Admin] Failed to reactivate "
                "organizer_id=%s error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            "Organizer reactivation failed.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_organizer_detail",
                organizer_id=
                    organizer.id,
            )
        )


    flash(
        "Organizer account reactivated.",
        "success",
    )


    return redirect(
        url_for(
            "superadmin_organizer_detail",
            organizer_id=
                organizer.id,
        )
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    today = (
        date.today()
    )


    events = (
        TicketEvent.query

        .filter_by(
            active=True,
            status="published",
            organizer_deleted=False,
        )

        .filter(
            TicketEvent.event_date
            >= today
        )

        .order_by(
            TicketEvent.event_date.asc(),
            TicketEvent.created_at.desc(),
        )

        .all()
    )


    return render_template(
        "event.html",

        events=
            events,

        event=
            None,

        firebase_config=
            FIREBASE_WEB_CONFIG,

        firebase_vapid_key=
            FIREBASE_VAPID_KEY,

        firebase_push_configured=
            firebase_web_push_configured(),
    )


# ============================================================
# PUBLIC EVENT POSTER
# ============================================================

@app.route(
    "/event/<int:event_id>/poster"
)
def event_poster(
    event_id,
):

    event = (
        TicketEvent.query
        .filter_by(
            id=event_id
        )
        .first_or_404()
    )


    if (
        not event.poster_image_data
        or not event.poster_image_mimetype
    ):

        return (
            "Poster not found.",
            404,
        )


    response = Response(
        event.poster_image_data,
        mimetype=
            event.poster_image_mimetype,
    )

    response.headers[
        "Cache-Control"
    ] = "public, max-age=3600"

    return response


# ============================================================
# PUBLIC ATTENDEE - ENABLE PUSH FROM HOME PAGE
# ============================================================

@app.route(
    "/notifications/subscribe-public",
    methods=["POST"],
)
def notification_subscribe_public():

    if not firebase_web_push_configured():

        return {
            "ok": False,
            "error":
                "Firebase Web Push is not configured.",
        }, 503

    payload = request.get_json(silent=True) or {}

    installation_id = str(
        payload.get("installation_id", "")
    ).strip()

    home_area = str(
        payload.get("home_area", "")
    ).strip()

    if (
        not installation_id
        or len(installation_id) > 255
    ):
        return {
            "ok": False,
            "error":
                "Invalid Firebase installation ID.",
        }, 400

    if not home_area:
        return {
            "ok": False,
            "error":
                "Enter the area or town where you live.",
        }, 400

    try:
        location = geocode_area(home_area)

    except (ValueError, RuntimeError) as error:
        return {
            "ok": False,
            "error": str(error),
        }, 400

    now = datetime.utcnow()

    subscription = (
        PushSubscription.query
        .filter_by(
            firebase_installation_id=
                installation_id
        )
        .first()
    )

    if not subscription:

        subscription = PushSubscription(
            contact_id=None,
            firebase_installation_id=
                installation_id,
            active=True,
            registered_at=now,
            last_seen_at=now,
            disabled_at=None,
        )

        db.session.add(subscription)

    else:

        subscription.active = True
        subscription.last_seen_at = now
        subscription.disabled_at = None

    subscription.home_area = home_area
    subscription.home_location_display = (
        location.display_name
    )
    subscription.home_latitude = (
        location.latitude
    )
    subscription.home_longitude = (
        location.longitude
    )

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            "[Public Push Subscribe] "
            "Failed installation_id=%s error=%s",
            installation_id,
            error,
        )

        return {
            "ok": False,
            "error":
                "Notification subscription could not be saved.",
        }, 500

    return {
        "ok": True,
        "message": (
            "Kalxa notifications are enabled for "
            f"{home_area} and events within "
            f"{LOCAL_NOTIFICATION_RADIUS_KM:g} km."
        ),
        "home_area": home_area,
        "radius_km":
            LOCAL_NOTIFICATION_RADIUS_KM,
    }


# ============================================================
# PUBLIC ATTENDEE - DISABLE PUSH ON THIS DEVICE
# ============================================================

@app.route(
    "/notifications/unsubscribe-public",
    methods=["POST"],
)
def notification_unsubscribe_public():

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )

    installation_id = (
        str(
            payload.get(
                "installation_id",
                ""
            )
        )
        .strip()
    )


    if not installation_id:

        return {
            "ok": False,
            "error": "Installation ID is required.",
        }, 400


    subscription = (
        PushSubscription.query
        .filter_by(
            firebase_installation_id=
                installation_id
        )
        .first()
    )


    if not subscription:

        return {
            "ok": True,
            "message": "Notifications are already off.",
        }


    now = datetime.utcnow()

    subscription.active = False
    subscription.disabled_at = now

    contact = subscription.contact


    if contact:

        other_active = (
            PushSubscription.query
            .filter(
                PushSubscription.contact_id
                == contact.id,

                PushSubscription.id
                != subscription.id,

                PushSubscription.active
                .is_(True),

                PushSubscription.disabled_at
                .is_(None),
            )
            .first()
        )


        if not other_active:

            contact.notification_consent = False
            contact.opted_out_at = now


    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Public Push Unsubscribe] "
                "Failed installation_id=%s error=%s"
            ),
            installation_id,
            error,
        )

        return {
            "ok": False,
            "error": "Unable to turn notifications off.",
        }, 500


    return {
        "ok": True,
        "message": "Notifications are off on this device.",
    }


# ============================================================
# ORGANIZER SIGNUP
# ============================================================

@app.route(
    "/organizer/signup",
    methods=[
        "GET",
        "POST",
    ],
)
def organizer_signup():

    if get_current_organizer():

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    if request.method == "POST":

        name = (
            request.form.get(
                "name",
                "",
            )
            .strip()
        )


        business_name = (
            request.form.get(
                "business_name",
                "",
            )
            .strip()
            or None
        )


        email = normalize_email(
            request.form.get(
                "email",
                "",
            )
        )


        phone = (
            request.form.get(
                "phone",
                "",
            )
            .strip()
            or None
        )


        password = (
            request.form.get(
                "password",
                ""
            )
        )


        password_confirm = (
            request.form.get(
                "password_confirm",
                ""
            )
        )


        if (
            not name
            or not email
            or not password
        ):

            flash(
                (
                    "Name, email and password "
                    "are required."
                ),
                "error",
            )

            return render_template(
                "organizer/signup.html"
            )


        if (
            len(
                password
            )
            < 8
        ):

            flash(
                (
                    "Password must be at least "
                    "8 characters."
                ),
                "error",
            )

            return render_template(
                "organizer/signup.html"
            )


        if (
            password
            != password_confirm
        ):

            flash(
                "Passwords do not match.",
                "error",
            )

            return render_template(
                "organizer/signup.html"
            )


        existing = (
            Organizer.query
            .filter_by(
                email=email
            )
            .first()
        )


        if existing:

            flash(
                (
                    "An organizer account already "
                    "exists with that email."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "organizer_login"
                )
            )


        organizer = Organizer(

            name=
                name,

            business_name=
                business_name,

            email=
                email,

            phone=
                phone,

            active=
                True,
        )


        organizer.set_password(
            password
        )


        try:

            db.session.add(
                organizer
            )

            db.session.commit()


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Organizer Signup] "
                    "Unable to create organizer "
                    "email=%s error=%s"
                ),
                email,
                error,
            )


            flash(
                (
                    "Unable to create your account. "
                    "Please try again."
                ),
                "error",
            )

            return render_template(
                "organizer/signup.html"
            )


        session.clear()


        flash(
            (
                "Organizer account created successfully. "
                "Please sign in."
            ),
            "success",
        )


        return redirect(
            url_for(
                "organizer_login"
            )
        )


    return render_template(
        "organizer/signup.html"
    )


# ============================================================
# ORGANIZER LOGIN
# ============================================================

@app.route(
    "/organizer/login",
    methods=[
        "GET",
        "POST",
    ],
)
def organizer_login():

    if get_current_organizer():

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    if request.method == "POST":

        email = normalize_email(
            request.form.get(
                "email",
                "",
            )
        )


        password = (
            request.form.get(
                "password",
                ""
            )
        )


        organizer = (
            Organizer.query
            .filter_by(
                email=email
            )
            .first()
        )


        password_ok = (
            organizer is not None
            and organizer.active
            and organizer.check_password(
                password
            )
        )


        current_app.logger.info(
            (
                "[Organizer Login] attempt "
                "email=%s found=%s active=%s "
                "password_ok=%s"
            ),
            email,
            organizer is not None,
            (
                organizer.active
                if organizer
                else None
            ),
            password_ok,
        )


        if not password_ok:

            flash(
                "Invalid email or password.",
                "error",
            )

            return render_template(
                "organizer/login.html"
            )


        pending_kalxa_organizer_id = (
            session.get(
                "pending_kalxa_organizer_id"
            )
        )


        pending_content_item_id = (
            session.get(
                "pending_kalxa_content_item_id"
            )
        )


        session.clear()


        session[
            ORGANIZER_SESSION_KEY
        ] = organizer.id


        session.permanent = True


        current_app.logger.info(
            (
                "[Organizer Login] authenticated "
                "organizer_id=%s session_key=%s"
            ),
            organizer.id,
            session.get(
                ORGANIZER_SESSION_KEY
            ),
        )


        if pending_kalxa_organizer_id:

            session[
                "kalxa_organizer_id"
            ] = (
                pending_kalxa_organizer_id
            )


        if pending_content_item_id:

            session[
                "kalxa_content_item_id"
            ] = (
                pending_content_item_id
            )


        if (
            pending_kalxa_organizer_id
            and organizer.kalxa_discovery_organizer_id
            is None
        ):

            organizer.kalxa_discovery_organizer_id = (
                int(
                    pending_kalxa_organizer_id
                )
            )


            try:

                db.session.commit()


            except Exception:

                db.session.rollback()


        flash(
            (
                "Welcome back to "
                "Kalxa Ticketing."
            ),
            "success",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    return render_template(
        "organizer/login.html"
    )


# ============================================================
# ORGANIZER LOGOUT
# ============================================================

@app.route(
    "/organizer/logout"
)
def organizer_logout():

    session.clear()


    return redirect(
        url_for(
            "organizer_login"
        )
    )


# ============================================================
# LEGACY ADMIN LOGIN / LOGOUT URLS
# ============================================================
#
# These old URLs are kept so existing bookmarks do not break.
#
# They now redirect into the organizer account system.
# ============================================================

@app.route(
    "/admin/login"
)
def admin_login():

    return redirect(
        url_for(
            "organizer_login"
        )
    )


@app.route(
    "/admin/logout"
)
def admin_logout():

    return redirect(
        url_for(
            "organizer_logout"
        )
    )


# ============================================================
# EVENT PAGE
# ============================================================

@app.route(
    "/event/<int:event_id>"
)
def event_page(
    event_id,
):

    event = (
        TicketEvent.query
        .filter_by(
            id=event_id,
            active=True,
            status="published",
            organizer_deleted=False,
        )
        .first_or_404()
    )


    return render_template(
        "event.html",
        event=event,
        events=None,
    )


# ============================================================
# RESERVE TICKET
# ============================================================

@app.route(
    "/event/<int:event_id>/reserve",
    methods=[
        "GET",
        "POST",
    ],
)
def reserve_ticket(
    event_id,
):

    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            active=
                True,

            status=
                "published",

            organizer_deleted=
                False,
        )
        .first_or_404()
    )


    if not event.sales_open:

        flash(
            "Ticket sales are currently paused for this event.",
            "error",
        )

        return redirect(
            url_for(
                "event_page",
                event_id=
                    event.id,
            )
        )


    organizer = (
        event.organizer
    )


    if (
        not organizer
        or not organizer.is_payment_connected
    ):

        flash(
            "Secure Paystack payments are not connected for this event yet.",
            "error",
        )

        return redirect(
            url_for(
                "event_page",
                event_id=
                    event.id,
            )
        )


    if event.is_sold_out:

        flash(
            "This event is sold out.",
            "error",
        )

        return redirect(
            url_for(
                "event_page",
                event_id=
                    event.id,
            )
        )


    ticket_types = (
        event.active_ticket_types
    )


    if request.method == "POST":

        customer_name = (
            request.form.get(
                "customer_name",
                "",
            )
            .strip()
        )

        customer_phone = (
            request.form.get(
                "customer_phone",
                "",
            )
            .strip()
        )

        customer_email = (
            request.form.get(
                "customer_email",
                "",
            )
            .strip()
            .lower()
        )


        if (
            not customer_name
            or not customer_phone
            or not customer_email
        ):

            flash(
                "Name, phone number and email are required for secure checkout.",
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=
                    event,
                ticket_types=
                    ticket_types,
                processing_rate=
                    PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
            )


        if "@" not in customer_email:

            flash(
                "Enter a valid email address.",
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=
                    event,
                ticket_types=
                    ticket_types,
                processing_rate=
                    PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
            )


        basket = []


        if ticket_types:

            for ticket_type in ticket_types:

                quantity = (
                    request.form.get(
                        f"qty_{ticket_type.id}",
                        type=int,
                    )
                    or 0
                )


                if quantity < 0:

                    abort(400)


                if quantity == 0:

                    continue


                if (
                    ticket_type.capacity is not None
                    and quantity
                    > ticket_type.remaining_quantity
                ):

                    flash(
                        (
                            f"Only {ticket_type.remaining_quantity} "
                            f"{ticket_type.name} ticket(s) remain."
                        ),
                        "error",
                    )

                    return render_template(
                        "reserve_ticket.html",
                        event=
                            event,
                        ticket_types=
                            ticket_types,
                        processing_rate=
                            PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
                    )


                basket.append(
                    {
                        "ticket_type":
                            ticket_type,
                        "name":
                            ticket_type.name,
                        "price":
                            Decimal(
                                str(
                                    ticket_type.price
                                )
                            ),
                        "quantity":
                            quantity,
                    }
                )


        else:

            # Legacy single-price event fallback.
            quantity = (
                request.form.get(
                    "quantity",
                    type=int,
                )
                or 0
            )


            if quantity > 0:

                if (
                    event.ticket_capacity is not None
                    and quantity
                    > event.remaining_tickets
                ):

                    flash(
                        "There are not enough tickets remaining.",
                        "error",
                    )

                    return render_template(
                        "reserve_ticket.html",
                        event=
                            event,
                        ticket_types=
                            [],
                        processing_rate=
                            PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
                    )


                basket.append(
                    {
                        "ticket_type":
                            None,
                        "name":
                            "General",
                        "price":
                            Decimal(
                                str(
                                    event.ticket_price
                                    or 0
                                )
                            ),
                        "quantity":
                            quantity,
                    }
                )


        total_quantity = sum(
            item["quantity"]
            for item in basket
        )


        if (
            total_quantity < 1
            or total_quantity > 10
        ):

            flash(
                "Choose between 1 and 10 tickets in total.",
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=
                    event,
                ticket_types=
                    ticket_types,
                processing_rate=
                    PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
            )


        total_amount = sum(
            (
                item["price"]
                * item["quantity"]
            )
            for item in basket
        ).quantize(
            Decimal("0.01")
        )


        (
            checkout_amount,
            processing_fee,
        ) = (
            calculate_paystack_checkout_amount(
                total_amount
            )
        )


        reference = (
            generate_payment_reference()
        )


        order = TicketOrder(
            event_id=
                event.id,

            customer_name=
                customer_name,

            customer_phone=
                customer_phone,

            customer_email=
                customer_email,

            quantity=
                total_quantity,

            # Legacy summary field retained for compatibility.
            ticket_price=(
                (
                    total_amount
                    / total_quantity
                ).quantize(
                    Decimal("0.01")
                )
            ),

            total_amount=
                total_amount,

            processing_fee=
                processing_fee,

            checkout_amount=
                checkout_amount,

            payment_provider=
                "paystack",

            payment_reference=
                reference,

            payment_status=
                "pending",
        )


        try:

            db.session.add(
                order
            )

            db.session.flush()


            for item in basket:

                if item["ticket_type"] is None:
                    continue

                line_total = (
                    item["price"]
                    * item["quantity"]
                ).quantize(
                    Decimal("0.01")
                )

                db.session.add(
                    TicketOrderItem(
                        order_id=
                            order.id,

                        ticket_type_id=
                            item["ticket_type"].id,

                        ticket_name=
                            item["name"],

                        unit_price=
                            item["price"],

                        quantity=
                            item["quantity"],

                        line_total=
                            line_total,
                    )
                )


            db.session.commit()


            callback_url = url_for(
                "paystack_ticket_callback",
                _external=
                    True,
                _scheme=
                    "https",
            )

            cancel_url = url_for(
                "booking_status",
                reference=
                    reference,
                _external=
                    True,
                _scheme=
                    "https",
            )


            basket_metadata = [
                {
                    "name":
                        item["name"],
                    "quantity":
                        item["quantity"],
                    "unit_price":
                        str(
                            item["price"]
                        ),
                }
                for item in basket
            ]


            payload = {
                "email":
                    customer_email,

                "amount":
                    str(
                        int(
                            (
                                checkout_amount
                                * 100
                            )
                            .quantize(
                                Decimal("1"),
                                rounding=
                                    ROUND_UP,
                            )
                        )
                    ),

                "currency":
                    "ZAR",

                "reference":
                    reference,

                "callback_url":
                    callback_url,

                "channels": [
                    "eft",
                    "capitec_pay",
                ],

                "subaccount":
                    organizer.paystack_subaccount_code,

                "bearer":
                    "subaccount",

                "metadata":
                    json.dumps(
                        {
                            "kalxa_order_id":
                                order.id,
                            "event_id":
                                event.id,
                            "ticket_face_value":
                                str(
                                    total_amount
                                ),
                            "processing_fee":
                                str(
                                    processing_fee
                                ),
                            "ticket_types":
                                basket_metadata,
                            "cancel_action":
                                cancel_url,
                        }
                    ),
            }


            paystack_result = (
                paystack_api_request(
                    "POST",
                    "/transaction/initialize",
                    payload,
                )
            )


            data = (
                paystack_result.get(
                    "data"
                )
                or {}
            )

            authorization_url = (
                data.get(
                    "authorization_url"
                )
            )


            if not authorization_url:

                raise RuntimeError(
                    "Paystack did not return a checkout URL."
                )


            order.paystack_access_code = (
                data.get(
                    "access_code"
                )
                or None
            )

            order.paystack_authorization_url = (
                authorization_url
            )


            db.session.commit()


        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Paystack Ticket Checkout] "
                    "Unable to initialize payment "
                    "event_id=%s reference=%s error=%s"
                ),
                event.id,
                reference,
                error,
            )

            try:

                persisted_order = (
                    TicketOrder.query
                    .filter_by(
                        payment_reference=
                            reference
                    )
                    .first()
                )

                if persisted_order:

                    db.session.delete(
                        persisted_order
                    )

                    db.session.commit()

            except Exception:

                db.session.rollback()


            flash(
                "Secure checkout could not be started. Please try again.",
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=
                    event,
                ticket_types=
                    ticket_types,
                processing_rate=
                    PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
            )


        return redirect(
            authorization_url
        )


    return render_template(
        "reserve_ticket.html",
        event=
            event,
        ticket_types=
            ticket_types,
        processing_rate=
            PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
    )


# ============================================================
# PAYSTACK TICKET CALLBACK
# ============================================================

@app.route(
    "/payments/paystack/callback"
)
def paystack_ticket_callback():

    reference = (
        request.args.get(
            "reference",
            "",
        )
        .strip()
    )


    if not reference:

        abort(400)


    order = (
        TicketOrder.query
        .filter_by(
            payment_reference=
                reference
        )
        .first_or_404()
    )


    try:

        result = (
            paystack_api_request(
                "GET",
                (
                    "/transaction/verify/"
                    + urllib.parse.quote(
                        reference,
                        safe="",
                    )
                ),
            )
        )


        transaction_data = (
            result.get(
                "data"
            )
            or {}
        )


        finalize_paystack_ticket_order(
            order,
            transaction_data,
        )


        flash(
            (
                "Payment confirmed. "
                "Your Kalxa ticket is ready."
            ),
            "success",
        )


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Paystack Callback] Verification failed "
                "reference=%s error=%s"
            ),
            reference,
            error,
        )


        flash(
            (
                "Your payment is still being verified. "
                "Refresh this page shortly."
            ),
            "error",
        )


    return redirect(
        url_for(
            "booking_status",
            reference=
                reference,
        )
    )


# ============================================================
# PAYSTACK TICKET WEBHOOK
# ============================================================

@app.route(
    "/payments/paystack/webhook",
    methods=[
        "POST",
    ],
)
def paystack_ticket_webhook():

    if not PAYSTACK_SECRET_KEY:

        abort(503)


    raw_body = (
        request.get_data()
    )


    received_signature = (
        request.headers.get(
            "x-paystack-signature",
            "",
        )
        .strip()
    )


    expected_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode(
            "utf-8"
        ),
        raw_body,
        hashlib.sha512,
    ).hexdigest()


    if (
        not received_signature
        or not hmac.compare_digest(
            received_signature,
            expected_signature,
        )
    ):

        abort(400)


    try:

        payload = json.loads(
            raw_body.decode(
                "utf-8"
            )
        )


    except Exception:

        abort(400)


    if (
        payload.get(
            "event"
        )
        != "charge.success"
    ):

        return (
            "",
            200,
        )


    transaction_data = (
        payload.get(
            "data"
        )
        or {}
    )


    reference = (
        str(
            transaction_data.get(
                "reference",
                "",
            )
        )
        .strip()
    )


    if not reference:

        return (
            "",
            200,
        )


    order = (
        TicketOrder.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if not order:

        subscription_payment = (
            SubscriptionPayment.query
            .filter_by(
                payment_reference=
                    reference
            )
            .first()
        )


        if not subscription_payment:

            boost = (
                EventBoost.query
                .filter_by(
                    payment_reference=
                        reference
                )
                .first()
            )


            if not boost:

                return (
                    "",
                    200,
                )


            try:

                finalize_event_boost_payment(
                    boost,
                    transaction_data,
                )


            except Exception as error:

                db.session.rollback()

                current_app.logger.exception(
                    (
                        "[Paystack Event Boost Webhook] "
                        "Failed reference=%s error=%s"
                    ),
                    reference,
                    error,
                )

                return (
                    "",
                    500,
                )


            return (
                "",
                200,
            )


        try:

            finalize_paystack_subscription_payment(
                subscription_payment,
                transaction_data,
            )


        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Paystack Subscription Webhook] "
                    "Failed reference=%s error=%s"
                ),
                reference,
                error,
            )

            return (
                "",
                500,
            )


        return (
            "",
            200,
        )


    try:

        finalize_paystack_ticket_order(
            order,
            transaction_data,
        )


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Paystack Webhook] Failed "
                "reference=%s error=%s"
            ),
            reference,
            error,
        )


        return (
            "",
            500,
        )


    return (
        "",
        200,
    )


# ============================================================
# OPTIONAL KALXA DISCOVERY -> TICKETING BRIDGE
# ============================================================
#
# Ticketing is now standalone.
#
# The Discovery bridge remains available as an optional
# traffic / context integration.
#
# A Discovery organizer is NOT automatically authenticated
# as a Ticketing organizer anymore.
# ============================================================

def get_kalxa_bridge_serializer():

    bridge_secret = (
        os.environ.get(
            "KALXA_TICKETING_BRIDGE_SECRET"
        )
    )


    if not bridge_secret:

        raise RuntimeError(
            (
                "KALXA_TICKETING_BRIDGE_SECRET "
                "is not configured."
            )
        )


    return URLSafeTimedSerializer(
        secret_key=
            bridge_secret,

        salt=
            "kalxa-ticketing-bridge-v1",
    )


@app.route(
    "/auth/kalxa",
    methods=[
        "POST",
    ],
)
def kalxa_auth_bridge():

    token = (
        request.form.get(
            "token",
            "",
        )
        .strip()
    )


    if not token:

        abort(400)


    serializer = (
        get_kalxa_bridge_serializer()
    )


    try:

        payload = serializer.loads(
            token,
            max_age=90,
        )


    except SignatureExpired:

        flash(
            (
                "Your secure Kalxa Ticketing link "
                "expired. Please open it again."
            ),
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    except BadSignature:

        abort(403)


    if (
        payload.get("aud")
        != "kalxa-ticketing"
    ):

        abort(403)


    if (
        payload.get("purpose")
        != "organizer-login"
    ):

        abort(403)


    bridge_id = (
        payload.get(
            "bridge_id"
        )
    )


    kalxa_organizer_id = (
        payload.get(
            "organizer_id"
        )
    )


    content_item_id = (
        payload.get(
            "content_item_id"
        )
    )


    if (
        not bridge_id
        or kalxa_organizer_id is None
        or content_item_id is None
    ):

        abort(403)


    try:

        kalxa_organizer_id = int(
            kalxa_organizer_id
        )

        content_item_id = int(
            content_item_id
        )


    except (
        TypeError,
        ValueError,
    ):

        abort(403)


    already_used = (
        KalxaBridgeTokenUse.query
        .filter_by(
            bridge_id=
                bridge_id
        )
        .first()
    )


    if already_used:

        abort(403)


    token_use = KalxaBridgeTokenUse(

        bridge_id=
            bridge_id,

        kalxa_organizer_id=
            kalxa_organizer_id,

        kalxa_content_item_id=
            content_item_id,
    )


    try:

        db.session.add(
            token_use
        )

        db.session.commit()


    except Exception:

        db.session.rollback()

        abort(403)


    # ========================================================
    # STORE TEMPORARY DISCOVERY CONTEXT
    # ========================================================

    session[
        "pending_kalxa_organizer_id"
    ] = kalxa_organizer_id


    session[
        "pending_kalxa_content_item_id"
    ] = content_item_id


    organizer = (
        get_current_organizer()
    )


    if organizer:

        session[
            "kalxa_organizer_id"
        ] = kalxa_organizer_id


        session[
            "kalxa_content_item_id"
        ] = content_item_id


        if (
            organizer.kalxa_discovery_organizer_id
            is None
        ):

            organizer.kalxa_discovery_organizer_id = (
                kalxa_organizer_id
            )


            try:

                db.session.commit()


            except Exception:

                db.session.rollback()


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    flash(
        (
            "Sign in to your Kalxa Ticketing "
            "organizer account to continue."
        ),
        "success",
    )


    return redirect(
        url_for(
            "organizer_login"
        )
    )


# ============================================================
# ORGANIZER DASHBOARD COMPATIBILITY URL
# ============================================================

@app.route(
    "/organizer/dashboard"
)
def organizer_ticketing_dashboard():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# TRACK MY TICKET
# ============================================================

@app.route(
    "/track",
    methods=[
        "GET",
        "POST",
    ],
)
def track_ticket():

    if request.method == "POST":

        reference = (
            request.form.get(
                "reference",
                "",
            )
            .strip()
            .upper()
        )


        if not reference:

            flash(
                "Please enter your booking reference.",
                "error",
            )

            return render_template(
                "track_ticket.html"
            )


        order = (
            TicketOrder.query
            .filter_by(
                payment_reference=
                    reference
            )
            .first()
        )


        if not order:

            flash(
                (
                    "We could not find a booking with "
                    "that reference. Please check it "
                    "and try again."
                ),
                "error",
            )

            return render_template(
                "track_ticket.html"
            )


        return redirect(
            url_for(
                "booking_status",
                reference=
                    order.payment_reference,
            )
        )


    return render_template(
        "track_ticket.html"
    )


# ============================================================
# BOOKING STATUS
# ============================================================

@app.route(
    "/booking/<reference>"
)
def booking_status(
    reference,
):

    order = (
        TicketOrder.query
        .filter_by(
            payment_reference=
                reference
        )
        .first_or_404()
    )


    return render_template(
        "booking_status.html",

        order=
            order,

        firebase_config=
            FIREBASE_WEB_CONFIG,

        firebase_vapid_key=
            FIREBASE_VAPID_KEY,

        firebase_push_configured=
            firebase_web_push_configured(),
    )


# ============================================================
# PWA MANIFEST
# ============================================================

@app.route(
    "/manifest.webmanifest"
)
def pwa_manifest():

    manifest = {
        "name":
            "Kalxa Ticketing",

        "short_name":
            "Kalxa",

        "description":
            (
                "Discover events, buy tickets, "
                "receive event updates and manage "
                "your Kalxa tickets."
            ),

        "id":
            "/",

        "start_url":
            "/",

        "scope":
            "/",

        "display":
            "standalone",

        "background_color":
            "#0b0c0e",

        "theme_color":
            "#0b0c0e",

        "orientation":
            "portrait-primary",

        "prefer_related_applications":
            False,

        "icons": [
            {
                "src":
                    "/static/icons/kalxa-192.png",

                "sizes":
                    "192x192",

                "type":
                    "image/png",

                "purpose":
                    "any",
            },
            {
                "src":
                    "/static/icons/kalxa-512.png",

                "sizes":
                    "512x512",

                "type":
                    "image/png",

                "purpose":
                    "any",
            },
            {
                "src":
                    "/static/icons/kalxa-maskable-512.png",

                "sizes":
                    "512x512",

                "type":
                    "image/png",

                "purpose":
                    "maskable",
            },
        ],
    }


    return Response(
        json.dumps(
            manifest
        ),
        mimetype=
            "application/manifest+json",
    )


# ============================================================
# PWA OFFLINE FALLBACK
# ============================================================

@app.route(
    "/offline"
)
def pwa_offline():

    return render_template(
        "offline.html"
    )


# ============================================================
# FIREBASE MESSAGING SERVICE WORKER
# ============================================================
#
# Served at the root of the domain so the service worker can
# control the whole Kalxa Ticketing origin.
# ============================================================

@app.route(
    "/firebase-messaging-sw.js"
)
def firebase_messaging_service_worker():

    if not firebase_web_push_configured():

        return Response(
            (
                "// Firebase Web Push is not configured.\n"
            ),
            mimetype=
                "application/javascript",
        )


    config_json = json.dumps(
        FIREBASE_WEB_CONFIG
    )


    service_worker = f"""
importScripts(
    "https://www.gstatic.com/firebasejs/12.19.0/firebase-app-compat.js"
);

importScripts(
    "https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging-compat.js"
);

firebase.initializeApp(
    {config_json}
);

const messaging =
    firebase.messaging();


// IMPORTANT:
//
// Do not manually call showNotification() here.
//
// The server sends an FCM notification payload, so Firebase
// displays the browser notification automatically in the
// background.
//
// Click navigation is handled by webpush.fcm_options.link.


// ==========================================================
// KALXA PWA APP SHELL
// ==========================================================

const KALXA_CACHE =
    "kalxa-ticketing-pwa-v3";

const KALXA_APP_SHELL = [
    "/offline",
    "/manifest.webmanifest",
    "/static/icons/kalxa-192.png",
    "/static/icons/kalxa-512.png",
    "/static/icons/kalxa-maskable-512.png"
];


self.addEventListener(
    "install",
    (event) => {{

        event.waitUntil(
            caches
                .open(
                    KALXA_CACHE
                )
                .then(
                    async (cache) => {{

                        // Cache each asset independently.
                        //
                        // One missing optional asset should NOT
                        // prevent the whole service worker from
                        // installing.
                        await Promise.allSettled(
                            KALXA_APP_SHELL.map(
                                (url) =>
                                    cache.add(url)
                            )
                        );
                    }}
                )
        );

        self.skipWaiting();
    }}
);


self.addEventListener(
    "activate",
    (event) => {{

        event.waitUntil(
            caches
                .keys()
                .then(
                    (keys) =>
                        Promise.all(
                            keys
                                .filter(
                                    (key) =>
                                        key.startsWith(
                                            "kalxa-ticketing-pwa-"
                                        )
                                        &&
                                        key !== KALXA_CACHE
                                )
                                .map(
                                    (key) =>
                                        caches.delete(
                                            key
                                        )
                                )
                        )
                )
        );

        self.clients.claim();
    }}
);


self.addEventListener(
    "fetch",
    (event) => {{

        if (
            event.request.method
            !== "GET"
        ) {{
            return;
        }}


        const requestUrl =
            new URL(
                event.request.url
            );


        if (
            requestUrl.origin
            !== self.location.origin
        ) {{
            return;
        }}


        if (
            event.request.mode
            === "navigate"
        ) {{

            event.respondWith(
                fetch(
                    event.request
                )
                .catch(
                    () =>
                        caches.match(
                            "/offline"
                        )
                )
            );

            return;
        }}


        if (
            requestUrl.pathname.startsWith(
                "/static/icons/"
            )
            ||
            requestUrl.pathname
            === "/manifest.webmanifest"
        ) {{

            event.respondWith(
                caches.match(
                    event.request
                )
                .then(
                    (cached) =>
                        cached
                        ||
                        fetch(
                            event.request
                        )
                )
            );
        }}
    }}
);
"""


    response = Response(
        service_worker,
        mimetype=
            "application/javascript",
    )


    response.headers[
        "Cache-Control"
    ] = (
        "no-cache, no-store, must-revalidate"
    )


    return response


# ============================================================
# ATTENDEE - ENABLE PUSH NOTIFICATIONS
# ============================================================

@app.route(
    "/notifications/subscribe",
    methods=["POST"],
)
def notification_subscribe():

    if not firebase_web_push_configured():

        return {
            "ok": False,
            "error":
                "Firebase Web Push is not configured.",
        }, 503

    payload = request.get_json(silent=True) or {}

    reference = str(
        payload.get("reference", "")
    ).strip().upper()

    installation_id = str(
        payload.get("installation_id", "")
    ).strip()

    home_area = str(
        payload.get("home_area", "")
    ).strip()

    if not reference or not installation_id:
        return {
            "ok": False,
            "error":
                "Booking reference and installation ID are required.",
        }, 400

    if not home_area:
        return {
            "ok": False,
            "error":
                "Enter the area or town where you live.",
        }, 400

    if len(installation_id) > 255:
        return {
            "ok": False,
            "error":
                "Invalid Firebase installation ID.",
        }, 400

    order = (
        TicketOrder.query
        .filter_by(
            payment_reference=reference
        )
        .first()
    )

    if not order:
        return {
            "ok": False,
            "error":
                "Booking could not be found.",
        }, 404

    try:
        location = geocode_area(home_area)

    except (ValueError, RuntimeError) as error:
        return {
            "ok": False,
            "error": str(error),
        }, 400

    phone_normalized = normalize_attendee_phone(
        order.customer_phone
    )

    if not phone_normalized:
        return {
            "ok": False,
            "error":
                "A valid attendee phone number is required.",
        }, 400

    now = datetime.utcnow()

    contact = (
        AttendeeContact.query
        .filter_by(
            phone_normalized=
                phone_normalized
        )
        .first()
    )

    if not contact:

        contact = AttendeeContact(
            name=order.customer_name,
            phone=order.customer_phone,
            phone_normalized=
                phone_normalized,
            email=order.customer_email,
            notification_consent=True,
            consented_at=now,
            opted_out_at=None,
        )

        db.session.add(contact)
        db.session.flush()

    else:

        contact.name = (
            order.customer_name
            or contact.name
        )
        contact.phone = (
            order.customer_phone
            or contact.phone
        )
        contact.email = (
            order.customer_email
            or contact.email
        )
        contact.notification_consent = True
        contact.consented_at = now
        contact.opted_out_at = None

    subscription = (
        PushSubscription.query
        .filter_by(
            firebase_installation_id=
                installation_id
        )
        .first()
    )

    if not subscription:

        subscription = PushSubscription(
            contact_id=contact.id,
            firebase_installation_id=
                installation_id,
            active=True,
            registered_at=now,
            last_seen_at=now,
            disabled_at=None,
        )

        db.session.add(subscription)

    else:

        subscription.contact_id = contact.id
        subscription.active = True
        subscription.last_seen_at = now
        subscription.disabled_at = None

    subscription.home_area = home_area
    subscription.home_location_display = (
        location.display_name
    )
    subscription.home_latitude = (
        location.latitude
    )
    subscription.home_longitude = (
        location.longitude
    )

    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            "[Push Subscribe] Failed "
            "reference=%s error=%s",
            reference,
            error,
        )

        return {
            "ok": False,
            "error":
                "Notification subscription could not be saved.",
        }, 500

    return {
        "ok": True,
        "message": (
            "Future-event notifications are enabled "
            f"for {home_area} and events within "
            f"{LOCAL_NOTIFICATION_RADIUS_KM:g} km."
        ),
        "home_area": home_area,
        "radius_km":
            LOCAL_NOTIFICATION_RADIUS_KM,
    }


# ============================================================
# ATTENDEE - DISABLE PUSH NOTIFICATIONS
# ============================================================

@app.route(
    "/notifications/unsubscribe",
    methods=[
        "POST",
    ],
)
def notification_unsubscribe():

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )


    reference = (
        str(
            payload.get(
                "reference",
                ""
            )
        )
        .strip()
        .upper()
    )


    installation_id = (
        str(
            payload.get(
                "installation_id",
                ""
            )
        )
        .strip()
    )


    if (
        not reference
        or not installation_id
    ):

        return {
            "ok": False,
            "error": (
                "Booking reference and installation ID "
                "are required."
            ),
        }, 400


    order = (
        TicketOrder.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if not order:

        return {
            "ok": False,
            "error": (
                "Booking could not be found."
            ),
        }, 404


    phone_normalized = (
        normalize_attendee_phone(
            order.customer_phone
        )
    )


    subscription = (
        PushSubscription.query
        .filter_by(
            firebase_installation_id=
                installation_id
        )
        .first()
    )


    now = (
        datetime.utcnow()
    )


    if subscription:

        subscription.active = (
            False
        )

        subscription.disabled_at = (
            now
        )


    contact = None


    if phone_normalized:

        contact = (
            AttendeeContact.query
            .filter_by(
                phone_normalized=
                    phone_normalized
            )
            .first()
        )


    if contact:

        contact.notification_consent = (
            False
        )

        contact.opted_out_at = (
            now
        )


        for device in (
            contact.push_subscriptions
        ):

            device.active = (
                False
            )

            device.disabled_at = (
                now
            )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Push Unsubscribe] Failed "
                "reference=%s error=%s"
            ),
            reference,
            error,
        )


        return {
            "ok": False,
            "error": (
                "Notification preference could "
                "not be updated."
            ),
        }, 500


    return {
        "ok": True,
        "message": (
            "Future-event notifications are turned off."
        ),
    }


# ============================================================
# ENTRY PASS
# ============================================================

@app.route(
    "/ticket/<entry_code>"
)
def ticket_page(
    entry_code,
):

    entry_pass = (
        EntryPass.query
        .filter_by(
            entry_code=
                entry_code
        )
        .first_or_404()
    )


    return render_template(
        "ticket.html",
        entry_pass=
            entry_pass,
    )


# ============================================================
# QR IMAGE
# ============================================================

@app.route(
    "/ticket/<entry_code>/qr"
)
def ticket_qr(
    entry_code,
):

    entry_pass = (
        EntryPass.query
        .filter_by(
            entry_code=
                entry_code
        )
        .first_or_404()
    )


    order = (
        entry_pass.order
    )


    if not order:

        abort(404)


    if (
        order.payment_status
        != "paid"
    ):

        abort(403)


    qr_value = (
        entry_pass.entry_code
    )


    image = qrcode.make(
        qr_value
    )


    buffer = io.BytesIO()


    image.save(
        buffer,
        format="PNG",
    )


    buffer.seek(
        0
    )


    return Response(
        buffer.getvalue(),
        mimetype="image/png",
    )


# ============================================================
# ORGANIZER ADMIN COMPATIBILITY ROUTE
# ============================================================

@app.route(
    "/organizer/admin"
)
def organizer_admin_redirect():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# ORGANIZER SUBSCRIPTION
# ============================================================

@app.route(
    "/admin/subscription"
)
def admin_subscription():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    payments = (
        SubscriptionPayment.query
        .filter_by(
            organizer_id=
                organizer.id
        )
        .order_by(
            SubscriptionPayment.created_at.desc()
        )
        .all()
    )


    pending_payment = (
        SubscriptionPayment.query
        .filter_by(
            organizer_id=
                organizer.id,

            payment_status=
                "pending",
        )
        .order_by(
            SubscriptionPayment.created_at.desc()
        )
        .first()
    )


    return render_template(
        "admin/subscription.html",

        organizer=
            organizer,

        payments=
            payments,

        pending_payment=
            pending_payment,

        subscription_active=
            organizer.is_subscription_active,

        subscription_status=
            organizer.effective_subscription_status,

        subscription_expires_at=
            organizer.subscription_expires_at,

        subscription_plan_name=
            KALXA_SUBSCRIPTION_PLAN_NAME,

        subscription_price=
            KALXA_SUBSCRIPTION_PRICE,

        subscription_period_days=
            KALXA_SUBSCRIPTION_PERIOD_DAYS,

        bank_details=
            KALXA_SUBSCRIPTION_BANK,
    )


# ============================================================
# ORGANIZER - PAY SUBSCRIPTION WITH PAYSTACK
# ============================================================

@app.route(
    "/admin/subscription/request",
    methods=[
        "POST",
    ],
)
def admin_request_subscription_payment():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    if organizer.is_suspended:

        flash(
            (
                "Your organizer account is suspended. "
                "Contact Kalxa before renewing."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_subscription"
            )
        )


    if not paystack_is_configured():

        flash(
            "Paystack is not configured on Kalxa yet.",
            "error",
        )

        return redirect(
            url_for(
                "admin_subscription"
            )
        )


    payment = (
        SubscriptionPayment.query
        .filter_by(
            organizer_id=
                organizer.id,

            payment_status=
                "pending",
        )
        .order_by(
            SubscriptionPayment.created_at.desc()
        )
        .first()
    )


    if (
        payment
        and payment.paystack_authorization_url
    ):

        return redirect(
            payment.paystack_authorization_url
        )


    if not payment:

        payment = SubscriptionPayment(

            organizer_id=
                organizer.id,

            plan_name=
                KALXA_SUBSCRIPTION_PLAN_NAME,

            amount=
                KALXA_SUBSCRIPTION_PRICE,

            period_days=
                KALXA_SUBSCRIPTION_PERIOD_DAYS,

            payment_reference=
                generate_subscription_payment_reference(),

            payment_method=
                "paystack",

            payment_status=
                "pending",
        )


        try:

            db.session.add(
                payment
            )

            db.session.commit()


        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Subscription Paystack] "
                    "Failed to create payment record "
                    "organizer_id=%s error=%s"
                ),
                organizer.id,
                error,
            )

            flash(
                (
                    "Unable to start subscription payment. "
                    "Please try again."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_subscription"
                )
            )


    callback_url = url_for(
        "paystack_subscription_callback",
        _external=
            True,
        _scheme=
            "https",
    )


    payload = {
        "email":
            organizer.email,

        "amount":
            str(
                int(
                    (
                        Decimal(
                            str(
                                payment.amount
                            )
                        )
                        * 100
                    )
                    .quantize(
                        Decimal("1"),
                        rounding=
                            ROUND_UP,
                    )
                )
            ),

        "currency":
            "ZAR",

        "reference":
            payment.payment_reference,

        "callback_url":
            callback_url,

        # Use Kalxa's main Paystack merchant account.
        # No organizer subaccount is supplied here.
        "channels": [
            "eft",
            "capitec_pay",
        ],

        "metadata":
            json.dumps(
                {
                    "payment_type":
                        "kalxa_subscription",

                    "subscription_payment_id":
                        payment.id,

                    "organizer_id":
                        organizer.id,

                    "plan_name":
                        payment.plan_name,

                    "period_days":
                        payment.period_days,
                }
            ),
    }


    try:

        result = (
            paystack_api_request(
                "POST",
                "/transaction/initialize",
                payload,
            )
        )


        data = (
            result.get(
                "data"
            )
            or {}
        )


        authorization_url = (
            data.get(
                "authorization_url"
            )
        )


        if not authorization_url:

            raise RuntimeError(
                "Paystack did not return a subscription checkout URL."
            )


        payment.paystack_access_code = (
            data.get(
                "access_code"
            )
            or None
        )

        payment.paystack_authorization_url = (
            authorization_url
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Subscription Paystack] "
                "Checkout initialization failed "
                "organizer_id=%s payment_id=%s error=%s"
            ),
            organizer.id,
            payment.id,
            error,
        )

        flash(
            (
                "Secure Paystack checkout could not be started. "
                "Please try again."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_subscription"
            )
        )


    return redirect(
        authorization_url
    )


# ============================================================
# PAYSTACK SUBSCRIPTION CALLBACK
# ============================================================

@app.route(
    "/payments/paystack/subscription/callback"
)
def paystack_subscription_callback():

    reference = (
        request.args.get(
            "reference",
            "",
        )
        .strip()
    )


    if not reference:

        abort(400)


    payment = (
        SubscriptionPayment.query
        .filter_by(
            payment_reference=
                reference
        )
        .first_or_404()
    )


    try:

        result = (
            paystack_api_request(
                "GET",
                (
                    "/transaction/verify/"
                    + urllib.parse.quote(
                        reference,
                        safe="",
                    )
                ),
            )
        )


        transaction_data = (
            result.get(
                "data"
            )
            or {}
        )


        finalize_paystack_subscription_payment(
            payment,
            transaction_data,
        )


        flash(
            (
                "Subscription payment confirmed. "
                "Your Kalxa organizer access is now active."
            ),
            "success",
        )


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Subscription Paystack Callback] "
                "Verification failed reference=%s error=%s"
            ),
            reference,
            error,
        )

        flash(
            (
                "Your subscription payment is still being "
                "verified. Please refresh shortly."
            ),
            "error",
        )


    return redirect(
        url_for(
            "admin_subscription"
        )
    )


# ============================================================
# ORGANIZER PAYSTACK SETUP
# ============================================================

@app.route(
    "/admin/payments",
    methods=["GET", "POST"],
)
def admin_payments():

    auth = require_ticketing_organizer()

    if auth:
        return auth

    organizer = get_current_organizer()

    banks = []

    if paystack_is_configured():

        try:
            banks = get_paystack_za_banks()

        except Exception as error:

            current_app.logger.exception(
                "[Paystack] Bank list failed: %s",
                error,
            )

            flash(
                (
                    "Could not load Paystack banks: "
                    f"{error}"
                ),
                "error",
            )

    if request.method == "POST":

        if not organizer.is_subscription_active:

            flash(
                "Activate your Kalxa Ticketing subscription first.",
                "error",
            )

            return redirect(
                url_for("admin_payments")
            )

        if not paystack_is_configured():

            flash(
                "Paystack is not configured yet.",
                "error",
            )

            return redirect(
                url_for("admin_payments")
            )

        bank_code = (
            request.form.get("bank_code", "")
            .strip()
        )

        bank_name = (
            request.form.get("bank_name", "")
            .strip()
        )

        account_number = (
            request.form.get("account_number", "")
            .strip()
            .replace(" ", "")
        )

        account_name = (
            request.form.get("account_name", "")
            .strip()
        )

        if (
            not bank_code
            or not account_number
            or not account_name
        ):

            flash(
                "Bank, account holder and account number are required.",
                "error",
            )

            return render_template(
                "admin/payments.html",
                organizer=organizer,
                banks=banks,
                paystack_configured=
                    paystack_is_configured(),
            )

        if not account_number.isdigit():

            flash(
                "Account number must contain digits only.",
                "error",
            )

            return render_template(
                "admin/payments.html",
                organizer=organizer,
                banks=banks,
                paystack_configured=
                    paystack_is_configured(),
            )

        payload = {
            "business_name":
                organizer.display_name,

            "settlement_bank":
                bank_code,

            "account_number":
                account_number,

            # Kalxa commission is 0%.
            "percentage_charge":
                0,

            "description":
                f"Kalxa Ticketing organizer #{organizer.id}",

            "primary_contact_email":
                organizer.email,

            "primary_contact_name":
                organizer.name,

            "primary_contact_phone":
                organizer.phone,
        }

        payload = {
            key: value
            for key, value in payload.items()
            if value not in (None, "")
        }

        try:

            result = paystack_api_request(
                "POST",
                "/subaccount",
                payload,
            )

            data = result.get("data") or {}

            subaccount_code = str(
                data.get("subaccount_code", "")
            ).strip()

            if not subaccount_code:
                raise RuntimeError(
                    "Paystack did not return a subaccount code."
                )

            organizer.payment_provider = "paystack"
            organizer.payment_setup_status = "connected"
            organizer.paystack_subaccount_code = (
                subaccount_code
            )
            organizer.paystack_subaccount_id = (
                str(data.get("id", "")) or None
            )
            organizer.payment_bank_name = (
                data.get("settlement_bank")
                or bank_name
                or None
            )
            organizer.payment_bank_code = (
                bank_code
            )
            organizer.payment_account_name = (
                data.get("account_name")
                or account_name
            )
            organizer.payment_account_last4 = (
                account_number[-4:]
            )
            organizer.payment_connected_at = (
                datetime.utcnow()
            )

            db.session.commit()

        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Paystack] Connection failed "
                    "organizer_id=%s error=%s"
                ),
                organizer.id,
                error,
            )

            flash(str(error), "error")

            return render_template(
                "admin/payments.html",
                organizer=organizer,
                banks=banks,
                paystack_configured=
                    paystack_is_configured(),
            )

        flash(
            "Paystack payments connected successfully.",
            "success",
        )

        return redirect(
            url_for("admin_payments")
        )

    return render_template(
        "admin/payments.html",
        organizer=organizer,
        banks=banks,
        paystack_configured=
            paystack_is_configured(),
    )


# ============================================================
# ORGANIZER DASHBOARD
# ============================================================

@app.route(
    "/admin"
)
def admin_dashboard():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    current_app.logger.info(
        (
            "[Organizer Dashboard] session organizer_id=%s"
        ),
        (
            organizer.id
            if organizer
            else None
        ),
    )


    active_content_item_id = (
        get_ticketing_content_item_id()
    )


    current_ticket_event = None


    if active_content_item_id:

        current_ticket_event = (
            TicketEvent.query
            .filter_by(

                organizer_id=
                    organizer.id,

                kalxa_content_item_id=
                    active_content_item_id,

                organizer_deleted=
                    False,
            )
            .first()
        )


    events = (
        TicketEvent.query
        .filter_by(
            organizer_id=
                organizer.id,

            organizer_deleted=
                False,
        )
        .order_by(
            TicketEvent.created_at.desc()
        )
        .all()
    )


    organizer_orders = (
        TicketOrder.query

        .join(
            TicketEvent,
            TicketOrder.event_id
            == TicketEvent.id,
        )

        .filter(
            TicketEvent.organizer_id
            == organizer.id
        )
    )


    total_orders = (
        organizer_orders.count()
    )


    paid_orders = (
        organizer_orders

        .filter(
            TicketOrder.payment_status
            == "paid"
        )

        .count()
    )


    checked_in = (
        EntryPass.query

        .join(
            TicketOrder,
            EntryPass.order_id
            == TicketOrder.id,
        )

        .join(
            TicketEvent,
            TicketOrder.event_id
            == TicketEvent.id,
        )

        .filter(
            TicketEvent.organizer_id
            == organizer.id
        )

        .filter(
            EntryPass.status
            == "used"
        )

        .count()
    )


    pending_subscription_payment = (
        SubscriptionPayment.query
        .filter_by(
            organizer_id=
                organizer.id,

            payment_status=
                "pending",
        )
        .order_by(
            SubscriptionPayment.created_at.desc()
        )
        .first()
    )


    return render_template(
        "admin/dashboard.html",

        events=
            events,

        total_orders=
            total_orders,

        paid_orders=
            paid_orders,

        checked_in=
            checked_in,

        organizer=
            organizer,

        organizer_id=
            organizer.id,

        active_content_item_id=
            active_content_item_id,

        current_ticket_event=
            current_ticket_event,

        subscription_active=
            organizer.is_subscription_active,

        subscription_status=
            organizer.effective_subscription_status,

        subscription_expires_at=
            organizer.subscription_expires_at,

        pending_subscription_payment=
            pending_subscription_payment,

        subscription_plan_name=
            KALXA_SUBSCRIPTION_PLAN_NAME,

        subscription_price=
            KALXA_SUBSCRIPTION_PRICE,
    )


# ============================================================
# CREATE EVENT
# ============================================================

@app.route(
    "/admin/events/new",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_new_event():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    subscription_auth = (
        require_active_subscription(
            organizer
        )
    )


    if subscription_auth:

        return subscription_auth


    if request.method == "GET":

        active_content_item_id = (
            get_ticketing_content_item_id()
        )

        current_ticket_event = None


        if active_content_item_id:

            current_ticket_event = (
                TicketEvent.query
                .filter_by(
                    organizer_id=
                        organizer.id,

                    kalxa_content_item_id=
                        active_content_item_id,
                )
                .first()
            )


        return render_template(
            "admin/new_event.html",

            organizer=
                organizer,

            active_content_item_id=
                active_content_item_id,

            current_ticket_event=
                current_ticket_event,
        )


    kalxa_content_item_id = (
        get_ticketing_content_item_id()
    )


    kalxa_organizer_id = (
        get_ticketing_legacy_kalxa_organizer_id()
    )


    # ========================================================
    # DUPLICATE DISCOVERY LINK PROTECTION
    # ========================================================

    if kalxa_content_item_id:

        existing_event = (
            TicketEvent.query
            .filter_by(
                kalxa_content_item_id=
                    kalxa_content_item_id
            )
            .first()
        )


        if existing_event:

            if (
                existing_event.organizer_id
                != organizer.id
            ):

                abort(403)


            flash(
                (
                    "Ticketing has already been created "
                    "for this linked Kalxa event."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


    # ========================================================
    # TITLE
    # ========================================================

    title = (
        request.form.get(
            "title",
            "",
        )
        .strip()
    )


    if not title:

        flash(
            "Event title is required.",
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # EVENT DATE / TIME
    # ========================================================

    event_date = None
    event_time = None


    event_date_raw = (
        request.form.get(
            "event_date",
            "",
        )
        .strip()
    )


    event_time_raw = (
        request.form.get(
            "event_time",
            "",
        )
        .strip()
    )


    if event_date_raw:

        try:

            event_date = (
                datetime.strptime(
                    event_date_raw,
                    "%Y-%m-%d",
                )
                .date()
            )


        except ValueError:

            flash(
                "Invalid event date.",
                "error",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


    if event_time_raw:

        try:

            event_time = (
                datetime.strptime(
                    event_time_raw,
                    "%H:%M",
                )
                .time()
            )


        except ValueError:

            flash(
                "Invalid event time.",
                "error",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


    # ========================================================
    # EVENT NOTIFICATION AREA
    # ========================================================

    event_area = (
        request.form.get(
            "notification_area",
            "",
        )
        .strip()
    )

    if not event_area:

        flash(
            "Event area or town is required so Kalxa "
            "can target nearby notification subscribers.",
            "error",
        )

        return redirect(
            url_for("admin_new_event")
        )

    try:
        event_location = geocode_area(
            event_area
        )

    except (ValueError, RuntimeError) as error:

        flash(str(error), "error")

        return redirect(
            url_for("admin_new_event")
        )


    # ========================================================
    # TICKET TYPES
    # ========================================================

    try:

        ticket_rows = (
            parse_ticket_type_form(
                request.form
            )
        )


    except ValueError as error:

        flash(
            str(
                error
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_new_event"
            )
        )


    # ========================================================
    # EVENT POSTER
    # ========================================================
    #
    # Store poster bytes in PostgreSQL so the image survives
    # Render deploys and restarts.
    # ========================================================

    poster_image = (
        request.files.get(
            "poster_image"
        )
    )


    poster_image_data = None
    poster_image_mimetype = None
    poster_image_filename = None

    # Kept as None so the existing exception cleanup remains
    # safe even though local-disk storage is no longer used.
    poster_path = None


    if (
        poster_image
        and poster_image.filename
    ):

        original_filename = (
            secure_filename(
                poster_image.filename
            )
        )


        if "." not in original_filename:

            flash(
                "Poster must be a JPG, JPEG, PNG or WEBP image.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        extension = (
            original_filename
            .rsplit(
                ".",
                1,
            )[1]
            .lower()
        )


        mimetype_lookup = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }


        if extension not in mimetype_lookup:

            flash(
                "Poster must be a JPG, JPEG, PNG or WEBP image.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        poster_image_data = poster_image.read()


        if not poster_image_data:

            flash(
                "The poster image is empty.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        if (
            len(
                poster_image_data
            )
            > (
                5
                * 1024
                * 1024
            )
        ):

            flash(
                "Poster must be 5 MB or smaller.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        poster_image_mimetype = (
            mimetype_lookup[
                extension
            ]
        )

        poster_image_filename = (
            original_filename
        )


    # ========================================================
    # PAYMENT SETUP
    # ========================================================
    #
    # Bank details no longer belong to individual events.
    # Settlement is configured once on the Organizer through
    # the Paystack connection in /admin/payments.
    # ========================================================


    # ========================================================
    # CREATE EVENT
    # ========================================================
    #
    # SECURITY:
    #
    # organizer_id comes only from the authenticated local
    # organizer session.
    #
    # Optional Discovery IDs are metadata only.
    # ========================================================

    event = TicketEvent(

        organizer_id=
            organizer.id,

        kalxa_organizer_id=
            kalxa_organizer_id,

        kalxa_content_item_id=
            kalxa_content_item_id,

        title=
            title,

        description=(
            request.form.get(
                "description",
                "",
            )
            .strip()
            or None
        ),

        venue=(
            request.form.get(
                "venue",
                "",
            )
            .strip()
            or None
        ),

        notification_area=
            event_area,

        notification_location_display=
            event_location.display_name,

        notification_latitude=
            event_location.latitude,

        notification_longitude=
            event_location.longitude,

        event_date=
            event_date,

        event_time=
            event_time,

        organizer_name=
            organizer.display_name,

        organizer_phone=
            organizer.phone,

        image_url=
            None,

        poster_image_data=
            poster_image_data,

        poster_image_mimetype=
            poster_image_mimetype,

        poster_image_filename=
            poster_image_filename,

        ticket_price=
            min(
                row["price"]
                for row in ticket_rows
            ),

        ticket_capacity=(
            sum(
                row["capacity"]
                for row in ticket_rows
            )
            if all(
                row["capacity"] is not None
                for row in ticket_rows
            )
            else None
        ),

        active=
            False,

        status=
            "draft",

        sales_open=
            False,
    )


    try:

        db.session.add(
            event
        )

        db.session.flush()


        for row in ticket_rows:

            db.session.add(
                TicketType(
                    event_id=
                        event.id,

                    name=
                        row["name"],

                    price=
                        row["price"],

                    capacity=
                        row["capacity"],

                    active=
                        True,

                    sort_order=
                        row["sort_order"],
                )
            )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        if (
            poster_path
            and os.path.exists(
                poster_path
            )
        ):

            try:

                os.remove(
                    poster_path
                )


            except Exception:

                current_app.logger.exception(
                    (
                        "[Ticketing] Failed to remove "
                        "poster after event save failure."
                    )
                )


        current_app.logger.exception(
            (
                "[Ticketing] Failed to create event "
                "organizer_id=%s "
                "title=%s "
                "error=%s"
            ),
            organizer.id,
            title,
            error,
        )


        flash(
            (
                "Ticket event could not be created. "
                "Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    flash(
        (
            "Ticket event created as a draft. "
            "Review it, then publish when ready."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_event_control",
            event_id=event.id,
        )
    )


# ============================================================
# ORGANIZER - DELETE EVENT
# ============================================================
#
# SAFE DELETE:
#
# We intentionally do NOT call db.session.delete(event).
#
# TicketEvent.orders uses cascading relationships, so a hard
# delete could also destroy order/ticket history.
#
# Instead:
# - remove event from organizer dashboard
# - remove event from public ticketing
# - stop sales
# - preserve orders, payments, passes and check-ins
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/delete",
    methods=[
        "POST",
    ],
)
def admin_delete_event(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,

            organizer_deleted=
                False,
        )
        .first_or_404()
    )


    now = (
        datetime.utcnow()
    )


    event.organizer_deleted = (
        True
    )

    event.deleted_at = (
        now
    )

    event.active = (
        False
    )

    event.sales_open = (
        False
    )


    if (
        event.status
        != "closed"
    ):

        event.status = (
            "closed"
        )


    if (
        event.closed_at
        is None
    ):

        event.closed_at = (
            now
        )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Organizer Delete Event] "
                "Failed organizer_id=%s "
                "event_id=%s error=%s"
            ),
            organizer.id,
            event.id,
            error,
        )


        flash(
            (
                "Event could not be deleted. "
                "Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    current_app.logger.info(
        (
            "[Organizer Delete Event] "
            "Safe-deleted organizer_id=%s event_id=%s"
        ),
        organizer.id,
        event.id,
    )


    flash(
        (
            "Event deleted from your dashboard. "
            "Ticket and order history was kept safely."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# EVENT CONTROL CENTRE
# ============================================================

@app.route(
    "/admin/events/<int:event_id>"
)
def admin_event_control(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth

    organizer = (
        get_current_organizer()
    )

    event = (
        TicketEvent.query
        .filter_by(
            id=event_id,
            organizer_id=organizer.id,
        )
        .first_or_404()
    )

    orders = (
        TicketOrder.query
        .filter_by(
            event_id=event.id
        )
        .order_by(
            TicketOrder.created_at.desc()
        )
        .all()
    )

    recent_orders = orders[:8]

    total_orders = len(orders)

    paid_orders = sum(
        1
        for order in orders
        if order.payment_status == "paid"
    )

    pending_orders = sum(
        1
        for order in orders
        if order.payment_status == "pending"
    )

    cancelled_orders = sum(
        1
        for order in orders
        if order.payment_status == "cancelled"
    )

    return render_template(
        "admin/event_control.html",
        organizer=organizer,
        event=event,
        recent_orders=recent_orders,
        total_orders=total_orders,
        paid_orders=paid_orders,
        pending_orders=pending_orders,
        cancelled_orders=cancelled_orders,
        paid_tickets=event.paid_ticket_count,
        checked_in=event.checked_in_ticket_count,
        revenue=event.paid_revenue,
        remaining_tickets=event.remaining_tickets,
        event_boost=(
            EventBoost.query
            .filter_by(
                event_id=event.id
            )
            .first()
        ),
        boost_audience_count=(
            len(
                get_local_push_subscriptions(
                    event,
                    float(
                        EVENT_BOOST_RADIUS_KM
                    ),
                )
            )
            if (
                event.notification_latitude
                is not None
                and event.notification_longitude
                is not None
            )
            else 0
        ),
    )


# ============================================================
# ORGANIZER - EVENT BOOST
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/boost"
)
def admin_event_boost(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    boost = (
        EventBoost.query
        .filter_by(
            event_id=
                event.id
        )
        .first()
    )


    audience_count = 0


    if (
        event.notification_latitude
        is not None
        and event.notification_longitude
        is not None
    ):

        audience_count = len(
            get_local_push_subscriptions(
                event,
                float(
                    EVENT_BOOST_RADIUS_KM
                ),
            )
        )


    if (
        boost
        and boost.status
        == "active"
        and boost.plan_code
        == "pro"
    ):

        build_event_boost_schedule(
            boost
        )

        db.session.commit()


    reminders = (
        boost.reminders
        if boost
        else []
    )


    sent_campaigns = [
        reminder.campaign
        for reminder in reminders
        if reminder.campaign
    ]


    performance = {
        "campaigns_sent":
            len(
                [
                    campaign
                    for campaign in sent_campaigns
                    if campaign.sent_at
                ]
            ),

        "recipients":
            sum(
                campaign.recipient_count
                or 0
                for campaign in sent_campaigns
            ),

        "success":
            sum(
                campaign.success_count
                or 0
                for campaign in sent_campaigns
            ),

        "failed":
            sum(
                campaign.failure_count
                or 0
                for campaign in sent_campaigns
            ),
    }


    performance[
        "delivery_rate"
    ] = (
        round(
            (
                performance[
                    "success"
                ]
                /
                performance[
                    "recipients"
                ]
                * 100
            ),
            1,
        )
        if performance[
            "recipients"
        ]
        else 0
    )


    audience_analytics = (
        build_local_audience_analytics(
            event,
            EVENT_BOOST_RADIUS_KM,
        )
    )


    reminder_rows = []


    for reminder in reminders:

        campaign = (
            reminder.campaign
        )


        recipient_count = (
            campaign.recipient_count
            if campaign
            else 0
        ) or 0

        success_count = (
            campaign.success_count
            if campaign
            else 0
        ) or 0

        failure_count = (
            campaign.failure_count
            if campaign
            else 0
        ) or 0


        reminder_rows.append(
            {
                "reminder":
                    reminder,

                "scheduled_display":
                    format_boost_schedule_sast(
                        reminder.scheduled_for
                    ),

                "campaign":
                    campaign,

                "recipient_count":
                    recipient_count,

                "success_count":
                    success_count,

                "failure_count":
                    failure_count,

                "delivery_rate":
                    (
                        round(
                            (
                                success_count
                                /
                                recipient_count
                                * 100
                            ),
                            1,
                        )
                        if recipient_count
                        else 0
                    ),
            }
        )


    return render_template(
        "admin/event_boost.html",

        organizer=
            organizer,

        event=
            event,

        boost=
            boost,

        reminders=
            reminders,

        reminder_rows=
            reminder_rows,

        audience_count=
            audience_count,

        audience_analytics=
            audience_analytics,

        performance=
            performance,

        basic_price=
            EVENT_BOOST_BASIC_PRICE,

        pro_price=
            EVENT_BOOST_PRO_PRICE,

        radius_km=
            EVENT_BOOST_RADIUS_KM,
    )


# ============================================================
# ORGANIZER - BUY EVENT BOOST
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/boost/purchase/<plan_code>",
    methods=[
        "POST",
    ],
)
def admin_purchase_event_boost(
    event_id,
    plan_code,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    subscription_auth = (
        require_active_subscription(
            organizer
        )
    )


    if subscription_auth:

        return subscription_auth


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    try:

        plan = (
            event_boost_plan(
                plan_code
            )
        )


    except ValueError:

        abort(
            400
        )


    if (
        event.status
        != "published"
        or not event.active
    ):

        flash(
            "Publish the event before buying an Event Boost.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    if (
        event.notification_latitude
        is None
        or event.notification_longitude
        is None
    ):

        flash(
            "Edit the event and save its Event Area / Town first.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    if (
        event.event_date
        and event.event_date
        < date.today()
    ):

        flash(
            "Past events cannot be boosted.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    if (
        plan_code
        == "pro"
        and (
            not event.event_date
            or not event.event_time
        )
    ):

        flash(
            (
                "Event Boost Pro needs both an event date "
                "and event time so Kalxa can schedule the "
                "3-day, tomorrow and Happening Now reminders."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    audience = (
        get_local_push_subscriptions(
            event,
            float(
                EVENT_BOOST_RADIUS_KM
            ),
        )
    )


    if not audience:

        flash(
            (
                "There are currently no opted-in users "
                f"within {EVENT_BOOST_RADIUS_KM:g} km "
                "of this event, so Kalxa will not charge "
                "you for a boost yet."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    boost = (
        EventBoost.query
        .filter_by(
            event_id=
                event.id
        )
        .first()
    )


    if (
        boost
        and boost.status
        == "active"
    ):

        flash(
            "This event already has an active paid boost.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    if (
        boost
        and boost.status
        == "pending"
        and boost.plan_code
        != plan_code
    ):

        db.session.delete(
            boost
        )

        db.session.commit()

        boost = None


    if not boost:

        boost = EventBoost(

            event_id=
                event.id,

            plan_code=
                plan_code,

            plan_name=
                plan[
                    "name"
                ],

            price=
                plan[
                    "price"
                ],

            radius_km=
                EVENT_BOOST_RADIUS_KM,

            campaign_limit=
                plan[
                    "campaign_limit"
                ],

            status=
                "pending",

            payment_reference=
                generate_event_boost_reference(),

            payment_provider=
                "paystack",

            audience_count_at_purchase=
                len(
                    audience
                ),
        )


        db.session.add(
            boost
        )

        db.session.commit()


    if (
        boost.paystack_authorization_url
        and boost.plan_code
        == plan_code
    ):

        return redirect(
            boost.paystack_authorization_url
        )


    callback_url = url_for(
        "paystack_event_boost_callback",
        _external=
            True,
        _scheme=
            "https",
    )


    payload = {
        "email":
            organizer.email,

        "amount":
            str(
                int(
                    (
                        Decimal(
                            str(
                                boost.price
                            )
                        )
                        * 100
                    )
                    .quantize(
                        Decimal("1"),
                        rounding=
                            ROUND_UP,
                    )
                )
            ),

        "currency":
            "ZAR",

        "reference":
            boost.payment_reference,

        "callback_url":
            callback_url,

        # Boost revenue belongs to Kalxa, not the event
        # organizer settlement subaccount.
        "channels": [
            "eft",
            "capitec_pay",
        ],

        "metadata":
            json.dumps(
                {
                    "payment_type":
                        "kalxa_event_boost",

                    "event_boost_id":
                        boost.id,

                    "event_id":
                        event.id,

                    "organizer_id":
                        organizer.id,

                    "plan_code":
                        boost.plan_code,

                    "radius_km":
                        str(
                            boost.radius_km
                        ),
                }
            ),
    }


    try:

        result = (
            paystack_api_request(
                "POST",
                "/transaction/initialize",
                payload,
            )
        )


        data = (
            result.get(
                "data"
            )
            or {}
        )


        authorization_url = (
            data.get(
                "authorization_url"
            )
        )


        if not authorization_url:

            raise RuntimeError(
                "Paystack did not return a boost checkout URL."
            )


        boost.paystack_access_code = (
            data.get(
                "access_code"
            )
            or None
        )

        boost.paystack_authorization_url = (
            authorization_url
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Event Boost Paystack] "
                "Checkout initialization failed "
                "boost_id=%s event_id=%s error=%s"
            ),
            boost.id,
            event.id,
            error,
        )


        flash(
            (
                "Event Boost checkout could not be started. "
                "Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_event_boost",
                event_id=
                    event.id,
            )
        )


    return redirect(
        authorization_url
    )


# ============================================================
# PAYSTACK EVENT BOOST CALLBACK
# ============================================================

@app.route(
    "/payments/paystack/boost/callback"
)
def paystack_event_boost_callback():

    reference = (
        request.args.get(
            "reference",
            "",
        )
        .strip()
    )


    if not reference:

        abort(
            400
        )


    boost = (
        EventBoost.query
        .filter_by(
            payment_reference=
                reference
        )
        .first_or_404()
    )


    try:

        result = (
            paystack_api_request(
                "GET",
                (
                    "/transaction/verify/"
                    + urllib.parse.quote(
                        reference,
                        safe="",
                    )
                ),
            )
        )


        transaction_data = (
            result.get(
                "data"
            )
            or {}
        )


        finalize_event_boost_payment(
            boost,
            transaction_data,
        )


        # Launch campaigns are due immediately.
        # If sending fails here, the cron processor can retry
        # pending future work without duplicating sent reminders.
        try:

            process_due_event_boost_reminders(
                boost_id=
                    boost.id,
                limit=
                    4,
            )


        except Exception:

            current_app.logger.exception(
                (
                    "[Event Boost] Immediate launch processing "
                    "failed boost_id=%s"
                ),
                boost.id,
            )


        flash(
            (
                f"{boost.plan_name} activated successfully. "
                "Kalxa will use your local 80 km audience."
            ),
            "success",
        )


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Event Boost Paystack Callback] "
                "Verification failed reference=%s error=%s"
            ),
            reference,
            error,
        )


        flash(
            (
                "Your Event Boost payment is still being "
                "verified. Please refresh shortly."
            ),
            "error",
        )


    return redirect(
        url_for(
            "admin_event_boost",
            event_id=
                boost.event_id,
        )
    )


# ============================================================
# EVENT BOOST TRAFFIC-BASED FALLBACK
# ============================================================
#
# The secured cron endpoint remains the reliable scheduler.
# This fallback checks at most once every 10 minutes per
# Gunicorn process whenever Kalxa receives traffic. Atomic
# reminder claiming prevents duplicate sends across workers.
# ============================================================

_boost_fallback_lock = (
    threading.Lock()
)

_boost_fallback_last_run = 0.0


@app.before_request
def process_due_boosts_on_traffic():

    global _boost_fallback_last_run


    if (
        request.endpoint
        == "process_event_boost_cron"
    ):

        return None


    now_monotonic = (
        time.monotonic()
    )


    if (
        now_monotonic
        - _boost_fallback_last_run
        < 600
    ):

        return None


    if not _boost_fallback_lock.acquire(
        blocking=False
    ):

        return None


    try:

        now_monotonic = (
            time.monotonic()
        )


        if (
            now_monotonic
            - _boost_fallback_last_run
            < 600
        ):

            return None


        _boost_fallback_last_run = (
            now_monotonic
        )


        try:

            process_due_event_boost_reminders(
                limit=
                    10
            )


        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Event Boost Fallback] "
                    "Due reminder processing failed error=%s"
                ),
                error,
            )


    finally:

        _boost_fallback_lock.release()


    return None


# ============================================================
# EVENT BOOST CRON PROCESSOR
# ============================================================

@app.route(
    "/tasks/event-boosts/process",
    methods=[
        "GET",
        "POST",
    ],
)
def process_event_boost_cron():

    if not BOOST_CRON_SECRET:

        abort(
            503
        )


    supplied_secret = (
        request.headers.get(
            "X-Cron-Secret",
            "",
        )
        .strip()
        or
        request.args.get(
            "token",
            "",
        )
        .strip()
    )


    if (
        not supplied_secret
        or not hmac.compare_digest(
            supplied_secret,
            BOOST_CRON_SECRET,
        )
    ):

        abort(
            403
        )


    result = (
        process_due_event_boost_reminders(
            limit=
                50
        )
    )


    return {
        "ok":
            True,
        **result,
    }


# ============================================================
# ORGANIZER - EDIT EVENT
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/edit",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_edit_event(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    if event.is_closed:

        flash(
            (
                "Closed events are read-only. "
                "Orders and check-in history remain available."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    if request.method == "POST":

        title = (
            request.form.get(
                "title",
                "",
            )
            .strip()
        )


        if not title:

            flash(
                "Event title is required.",
                "error",
            )

            return render_template(
                "admin/edit_event.html",
                event=
                    event,
            )


        event_date = None
        event_time = None


        event_date_raw = (
            request.form.get(
                "event_date",
                "",
            )
            .strip()
        )


        event_time_raw = (
            request.form.get(
                "event_time",
                "",
            )
            .strip()
        )


        if event_date_raw:

            try:

                event_date = (
                    datetime.strptime(
                        event_date_raw,
                        "%Y-%m-%d",
                    )
                    .date()
                )

            except ValueError:

                flash(
                    "Invalid event date.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


        if event_time_raw:

            try:

                event_time = (
                    datetime.strptime(
                        event_time_raw,
                        "%H:%M",
                    )
                    .time()
                )

            except ValueError:

                flash(
                    "Invalid event time.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


        event_area = (
            request.form.get(
                "notification_area",
                "",
            )
            .strip()
        )

        if not event_area:

            flash(
                "Event area or town is required for "
                "local notification targeting.",
                "error",
            )

            return render_template(
                "admin/edit_event.html",
                event=event,
            )

        try:
            event_location = geocode_area(
                event_area
            )

        except (ValueError, RuntimeError) as error:

            flash(str(error), "error")

            return render_template(
                "admin/edit_event.html",
                event=event,
            )


        try:

            ticket_rows = (
                parse_ticket_type_form(
                    request.form
                )
            )


        except ValueError as error:

            flash(
                str(
                    error
                ),
                "error",
            )


            return render_template(
                "admin/edit_event.html",
                event=
                    event,
            )


        existing_types_by_id = {
            ticket_type.id:
                ticket_type
            for ticket_type
            in event.ticket_types
        }


        for row in ticket_rows:

            if (
                row["id"] is not None
                and row["id"] not in existing_types_by_id
            ):

                abort(400)


            if row["id"] is not None:

                ticket_type = (
                    existing_types_by_id[
                        row["id"]
                    ]
                )


                if (
                    row["capacity"] is not None
                    and row["capacity"]
                    < ticket_type.sold_quantity
                ):

                    flash(
                        (
                            f"{ticket_type.name} capacity "
                            "cannot be lower than tickets "
                            "already sold."
                        ),
                        "error",
                    )


                    return render_template(
                        "admin/edit_event.html",
                        event=
                            event,
                    )


        poster_image = (
            request.files.get(
                "poster_image"
            )
        )


        new_poster_image_data = None
        new_poster_image_mimetype = None
        new_poster_image_filename = None

        # Keep old cleanup code safe.
        new_poster_path = None
        new_image_url = None


        if (
            poster_image
            and poster_image.filename
        ):

            original_filename = (
                secure_filename(
                    poster_image.filename
                )
            )


            if "." not in original_filename:

                flash(
                    "Poster must be a JPG, JPEG, PNG or WEBP image.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


            extension = (
                original_filename
                .rsplit(
                    ".",
                    1,
                )[1]
                .lower()
            )


            mimetype_lookup = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
            }


            if extension not in mimetype_lookup:

                flash(
                    "Poster must be a JPG, JPEG, PNG or WEBP image.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


            new_poster_image_data = (
                poster_image.read()
            )


            if not new_poster_image_data:

                flash(
                    "The poster image is empty.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


            if (
                len(
                    new_poster_image_data
                )
                > (
                    5
                    * 1024
                    * 1024
                )
            ):

                flash(
                    "Poster must be 5 MB or smaller.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


            new_poster_image_mimetype = (
                mimetype_lookup[
                    extension
                ]
            )

            new_poster_image_filename = (
                original_filename
            )


        event.title = title

        event.description = (
            request.form.get(
                "description",
                "",
            )
            .strip()
            or None
        )

        event.venue = (
            request.form.get(
                "venue",
                "",
            )
            .strip()
            or None
        )

        event.notification_area = (
            event_area
        )

        event.notification_location_display = (
            event_location.display_name
        )

        event.notification_latitude = (
            event_location.latitude
        )

        event.notification_longitude = (
            event_location.longitude
        )

        event.event_date = (
            event_date
        )

        event.event_time = (
            event_time
        )

        sync_event_legacy_ticket_summary(
            event,
            ticket_rows,
        )


        submitted_ids = set()


        for row in ticket_rows:

            if row["id"] is not None:

                ticket_type = (
                    existing_types_by_id[
                        row["id"]
                    ]
                )

                submitted_ids.add(
                    ticket_type.id
                )

                ticket_type.name = (
                    row["name"]
                )

                ticket_type.price = (
                    row["price"]
                )

                ticket_type.capacity = (
                    row["capacity"]
                )

                ticket_type.sort_order = (
                    row["sort_order"]
                )

                ticket_type.active = (
                    True
                )


            else:

                db.session.add(
                    TicketType(
                        event_id=
                            event.id,

                        name=
                            row["name"],

                        price=
                            row["price"],

                        capacity=
                            row["capacity"],

                        active=
                            True,

                        sort_order=
                            row["sort_order"],
                    )
                )


        for ticket_type in event.ticket_types:

            if (
                ticket_type.id
                and ticket_type.id
                not in submitted_ids
            ):

                if ticket_type.sold_quantity > 0:

                    ticket_type.active = (
                        False
                    )

                else:

                    db.session.delete(
                        ticket_type
                    )


        # Payment settlement is organizer-level through
        # Paystack. Event-level bank details are intentionally
        # no longer edited or collected.


        try:

            db.session.commit()

        except Exception as error:

            db.session.rollback()


            if (
                new_poster_path
                and os.path.exists(
                    new_poster_path
                )
            ):

                try:

                    os.remove(
                        new_poster_path
                    )

                except Exception:

                    pass


            current_app.logger.exception(
                (
                    "[Ticketing] Failed to update event "
                    "event_id=%s organizer_id=%s error=%s"
                ),
                event.id,
                organizer.id,
                error,
            )


            flash(
                "Event update failed.",
                "error",
            )

            return render_template(
                "admin/edit_event.html",
                event=
                    event,
            )


        flash(
            "Event details updated.",
            "success",
        )


        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    return render_template(
        "admin/edit_event.html",
        event=
            event,
    )


# ============================================================
# ORGANIZER - PUBLISH EVENT
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/publish",
    methods=[
        "POST",
    ],
)
def admin_publish_event(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    if event.is_closed:

        flash(
            "Closed events cannot be published again.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    event.status = (
        "published"
    )

    event.active = True

    event.published_at = (
        event.published_at
        or datetime.utcnow()
    )


    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Ticketing] Failed to publish event "
                "event_id=%s error=%s"
            ),
            event.id,
            error,
        )

        flash(
            "Unable to publish the event.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    flash(
        (
            "Event published. "
            "Ticket sales are still paused until you open them."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# ORGANIZER - OPEN TICKET SALES
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/sales/open",
    methods=[
        "POST",
    ],
)
def admin_open_event_sales(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    if not event.is_published:

        flash(
            "Publish the event before opening ticket sales.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    if event.is_sold_out:

        flash(
            "Ticket sales cannot open because the event is sold out.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    if not organizer.is_payment_connected:

        flash(
            (
                "Connect Paystack before opening ticket sales."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_payments"
            )
        )


    event.sales_open = True


    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Ticketing] Failed to open sales "
                "event_id=%s error=%s"
            ),
            event.id,
            error,
        )

        flash(
            "Unable to open ticket sales.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    flash(
        "Ticket sales are now open.",
        "success",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# ORGANIZER - PAUSE TICKET SALES
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/sales/pause",
    methods=[
        "POST",
    ],
)
def admin_pause_event_sales(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    event.sales_open = False


    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Ticketing] Failed to pause sales "
                "event_id=%s error=%s"
            ),
            event.id,
            error,
        )

        flash(
            "Unable to pause ticket sales.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    flash(
        "Ticket sales paused.",
        "success",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# ORGANIZER - CLOSE EVENT
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/close",
    methods=[
        "POST",
    ],
)
def admin_close_event(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    if event.is_closed:

        flash(
            "This event is already closed.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    event.status = (
        "closed"
    )

    event.sales_open = False

    event.active = False

    event.closed_at = (
        datetime.utcnow()
    )


    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Ticketing] Failed to close event "
                "event_id=%s error=%s"
            ),
            event.id,
            error,
        )

        flash(
            "Unable to close the event.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_control",
                event_id=event.id,
            )
        )


    flash(
        (
            "Event closed. "
            "Orders and check-in history have been preserved."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )


# ============================================================
# ORGANIZER ORDERS
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/orders"
)
def admin_orders(
    event_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    event = (
        TicketEvent.query
        .filter_by(
            id=
                event_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    orders = (
        TicketOrder.query
        .filter_by(
            event_id=
                event.id
        )
        .order_by(
            TicketOrder.created_at.desc()
        )
        .all()
    )


    total_orders = len(
        orders
    )

    paid_orders = sum(
        1
        for order in orders
        if order.payment_status == "paid"
    )

    pending_orders = sum(
        1
        for order in orders
        if order.payment_status == "pending"
    )

    cancelled_orders = sum(
        1
        for order in orders
        if order.payment_status == "cancelled"
    )

    ticket_revenue = sum(
        (
            Decimal(
                str(
                    order.total_amount
                    or 0
                )
            )
            for order in orders
            if order.payment_status == "paid"
        ),
        Decimal("0.00"),
    )

    processing_total = sum(
        (
            Decimal(
                str(
                    order.processing_fee
                    or 0
                )
            )
            for order in orders
            if order.payment_status == "paid"
        ),
        Decimal("0.00"),
    )

    checkout_total = sum(
        (
            Decimal(
                str(
                    order.checkout_amount
                    or order.total_amount
                    or 0
                )
            )
            for order in orders
            if order.payment_status == "paid"
        ),
        Decimal("0.00"),
    )


    return render_template(
        "admin/orders.html",

        organizer=
            organizer,

        event=
            event,

        orders=
            orders,

        total_orders=
            total_orders,

        paid_orders=
            paid_orders,

        pending_orders=
            pending_orders,

        cancelled_orders=
            cancelled_orders,

        ticket_revenue=
            ticket_revenue,

        processing_total=
            processing_total,

        checkout_total=
            checkout_total,
    )


# ============================================================
# VERIFY PAYSTACK ORDER
# ============================================================

@app.route(
    "/admin/orders/<int:order_id>/verify-paystack",
    methods=[
        "POST",
    ],
)
def admin_verify_paystack_order(
    order_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    order = (
        TicketOrder.query

        .join(
            TicketEvent,
            TicketOrder.event_id
            == TicketEvent.id,
        )

        .filter(
            TicketOrder.id
            == order_id
        )

        .filter(
            TicketEvent.organizer_id
            == organizer.id
        )

        .first_or_404()
    )


    event = (
        order.event
    )


    if (
        order.payment_provider
        != "paystack"
    ):

        flash(
            (
                "This order is not a Paystack order."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_orders",
                event_id=
                    event.id,
            )
        )


    if (
        order.payment_status
        == "paid"
    ):

        flash(
            (
                "This Paystack order is already verified "
                "and marked paid."
            ),
            "success",
        )


        return redirect(
            url_for(
                "admin_orders",
                event_id=
                    event.id,
            )
        )


    try:

        result = (
            paystack_api_request(
                "GET",
                (
                    "/transaction/verify/"
                    + urllib.parse.quote(
                        order.payment_reference,
                        safe="",
                    )
                ),
            )
        )


        transaction_data = (
            result.get(
                "data"
            )
            or {}
        )


        if (
            transaction_data.get(
                "status"
            )
            != "success"
        ):

            flash(
                (
                    "Paystack has not confirmed this "
                    "payment as successful yet."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_orders",
                    event_id=
                        event.id,
                )
            )


        finalize_paystack_ticket_order(
            order,
            transaction_data,
        )


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Paystack Audit Verify] "
                "Verification failed organizer_id=%s "
                "order_id=%s reference=%s error=%s"
            ),
            organizer.id,
            order.id,
            order.payment_reference,
            error,
        )


        flash(
            (
                "Paystack verification could not be completed. "
                "The order was not changed."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_orders",
                event_id=
                    event.id,
            )
        )


    flash(
        (
            "Paystack payment verified. "
            "The order is confirmed and its ticket is available."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_orders",
            event_id=
                event.id,
        )
    )


# ============================================================
# TICKET PAYMENT POLICY
# ============================================================
#
# Ticket payments are Paystack-only.
#
# There is intentionally no organizer "mark paid" route.
# A ticket order becomes paid only after:
#   1. Paystack callback verification,
#   2. signed Paystack webhook confirmation, or
#   3. organizer-triggered server-side Paystack verification.
#
# This prevents manual payment confirmation from bypassing
# Paystack's reference / amount / currency checks.
# ============================================================


# ============================================================
# CHECK-IN PAGE
# ============================================================

@app.route(
    "/admin/checkin",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_checkin():

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    entry_pass = None
    message = None


    if (
        request.method
        == "POST"
    ):

        raw_value = (
            request.form.get(
                "entry_code",
                "",
            )
            .strip()
        )


        if not raw_value:

            message = (
                "No ticket code was provided."
            )


            return render_template(
                "admin/checkin.html",

                entry_pass=None,

                message=
                    message,
            )


        entry_code = (
            raw_value
            .strip()
            .upper()
        )


        if (
            "/TICKET/"
            in entry_code
        ):

            entry_code = (
                entry_code
                .split(
                    "/TICKET/",
                    1,
                )[1]
                .split(
                    "?",
                    1,
                )[0]
                .split(
                    "#",
                    1,
                )[0]
                .strip()
            )


        entry_pass = (
            EntryPass.query

            .join(
                TicketOrder,
                EntryPass.order_id
                == TicketOrder.id,
            )

            .join(
                TicketEvent,
                TicketOrder.event_id
                == TicketEvent.id,
            )

            .filter(
                EntryPass.entry_code
                == entry_code
            )

            .filter(
                TicketEvent.organizer_id
                == organizer.id
            )

            .first()
        )


        if not entry_pass:

            message = (
                "Ticket not found for your events."
            )


        elif (
            not entry_pass.order
            or not entry_pass.order.event
        ):

            message = (
                "This ticket record is incomplete."
            )


        elif (
            entry_pass.order.payment_status
            != "paid"
        ):

            message = (
                "Payment has not been confirmed "
                "for this ticket."
            )


        elif (
            entry_pass.status
            == "used"
        ):

            message = (
                "This ticket has already been used."
            )


        elif (
            entry_pass.status
            != "valid"
        ):

            message = (
                "This ticket is not valid."
            )


    return render_template(
        "admin/checkin.html",

        entry_pass=
            entry_pass,

        message=
            message,
    )


# ============================================================
# CONFIRM CHECK-IN
# ============================================================

@app.route(
    "/admin/checkin/<int:pass_id>",
    methods=[
        "POST",
    ],
)
def admin_confirm_checkin(
    pass_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    entry_pass = (
        EntryPass.query

        .join(
            TicketOrder,
            EntryPass.order_id
            == TicketOrder.id,
        )

        .join(
            TicketEvent,
            TicketOrder.event_id
            == TicketEvent.id,
        )

        .filter(
            EntryPass.id
            == pass_id
        )

        .filter(
            TicketEvent.organizer_id
            == organizer.id
        )

        .first_or_404()
    )


    if (
        not entry_pass.order
        or not entry_pass.order.event
    ):

        flash(
            (
                "This ticket record is incomplete "
                "and cannot be checked in."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_checkin"
            )
        )


    if (
        entry_pass.order.payment_status
        != "paid"
    ):

        flash(
            (
                "This ticket cannot be checked in "
                "because payment has not been confirmed."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_checkin"
            )
        )


    if (
        entry_pass.status
        != "valid"
    ):

        flash(
            (
                "Ticket cannot be checked in. "
                "It may already have been used."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_checkin"
            )
        )


    existing_checkin = (
        CheckIn.query
        .filter_by(
            entry_pass_id=
                entry_pass.id
        )
        .first()
    )


    if existing_checkin:

        flash(
            (
                "This ticket has already "
                "been checked in."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_checkin"
            )
        )


    now = (
        datetime.utcnow()
    )


    entry_pass.status = (
        "used"
    )


    entry_pass.checked_in_at = (
        now
    )


    checkin = CheckIn(

        entry_pass_id=
            entry_pass.id,

        checked_in_at=
            now,

        checked_in_by=(
            f"organizer:{organizer.id}"
        ),
    )


    db.session.add(
        checkin
    )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Ticketing Check-In] "
                "Ticket check-in failed "
                "organizer_id=%s "
                "entry_pass_id=%s "
                "error=%s"
            ),
            organizer.id,
            entry_pass.id,
            error,
        )


        flash(
            (
                "Ticket check-in failed. "
                "Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_checkin"
            )
        )


    flash(
        "Ticket checked in successfully.",
        "success",
    )


    return redirect(
        url_for(
            "admin_checkin"
        )
    )


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health"
)
def health():

    return {
        "status": "ok",
        "service": "kalxa-ticketing",
    }


# ============================================================
# LOCAL RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
