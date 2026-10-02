# ============================================================
# KALXA TICKETING - APP
# ============================================================

import csv
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
import smtplib
import qrcode
from email.message import EmailMessage
from datetime import datetime, timedelta, date, timezone
from decimal import Decimal, InvalidOperation, ROUND_UP
from zoneinfo import ZoneInfo
import cloudinary
import cloudinary.uploader
import qrcode
import cloudinary
import cloudinary.uploader
from openpyxl import Workbook
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import firebase_admin
from firebase_admin import (
    credentials,
    messaging,
)

from dotenv import load_dotenv
from uuid import uuid4
from flask import (
    Flask,
    jsonify,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    send_file,
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
    FeaturedListing,
    FeaturedListingImage,
    GeocodedArea,
    KalxaBridgeTokenUse,
    Organizer,
    PushCampaign,
    PushDelivery,
    PushSubscription,
    StaffAccount,
    StaffEventAccess,
    SubscriptionPayment,
    TicketEvent,
    TicketOrder,
    TicketOrderItem,
    TicketType,
    TicketSalePhase,
    db,
    EventReel,
    EventReelAnalytics,
    RestaurantAdvert,
    RestaurantReel,
    RestaurantExperiencePost,
    RestaurantExperienceLove,
    RestaurantExperienceMedia,
    RestaurantOpeningHour,
    RestaurantGalleryImage,
    RestaurantRatingQRCode,
    RestaurantAnalyticsEvent,
    RestaurantSubscriptionPayment,
    RESTAURANT_PLAN_FREE,
    RESTAURANT_PLAN_STANDARD,
    RESTAURANT_PLAN_PREMIUM,
    RESTAURANT_PLAN_PRICES,
    RESTAURANT_PLAN_NAMES,
    RESTAURANT_PLAN_FEATURES,
    RESTAURANT_SUBSCRIPTION_GRACE_DAYS,
   
)

# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()






# ============================================================
# CLOUDINARY / EVENT REELS
# ============================================================

CLOUDINARY_CLOUD_NAME = (
    os.environ.get(
        "CLOUDINARY_CLOUD_NAME",
        "",
    )
    .strip()
)

CLOUDINARY_API_KEY = (
    os.environ.get(
        "CLOUDINARY_API_KEY",
        "",
    )
    .strip()
)

CLOUDINARY_API_SECRET = (
    os.environ.get(
        "CLOUDINARY_API_SECRET",
        "",
    )
    .strip()
)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)


EVENT_REEL_MAX_DURATION_SECONDS = 30
EVENT_REEL_MAX_FILE_BYTES = 80 * 1024 * 1024

EVENT_REEL_ALLOWED_EXTENSIONS = {
    "mp4",
    "mov",
    "webm",
    "m4v",
}



RESTAURANT_EXPERIENCE_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}


RESTAURANT_EXPERIENCE_VIDEO_EXTENSIONS = {
    "mp4",
    "mov",
    "m4v",
    "webm",
}

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
# RESTAURANT ANALYTICS
# ============================================================

RESTAURANT_ANALYTICS_SESSION_KEY = (
    "kalxa_restaurant_analytics_session"
)

RESTAURANT_ATTRIBUTION_SESSION_KEY = (
    "kalxa_restaurant_attribution"
)


# ============================================================
# RESTAURANT SUBSCRIPTION PAYMENT SETTINGS
# ============================================================

RESTAURANT_SUBSCRIPTION_PERIOD_DAYS = 30

# ============================================================
# RESTAURANT SUBSCRIPTION PLANS
# ============================================================

RESTAURANT_PLAN_FREE = "free"

RESTAURANT_PLAN_STANDARD = "standard"

RESTAURANT_PLAN_PREMIUM = "premium"


# ============================================================
# RESTAURANT PLAN PRICES
# ============================================================

RESTAURANT_PLAN_PRICES = {

    RESTAURANT_PLAN_FREE:
        0,

    RESTAURANT_PLAN_STANDARD:
        219,

    RESTAURANT_PLAN_PREMIUM:
        299,
}


# ============================================================
# RESTAURANT PLAN NAMES
# ============================================================

RESTAURANT_PLAN_NAMES = {

    RESTAURANT_PLAN_FREE:
        "Free",

    RESTAURANT_PLAN_STANDARD:
        "Standard",

    RESTAURANT_PLAN_PREMIUM:
        "Premium",
}


# ============================================================
# RESTAURANT PLAN FEATURES
# ============================================================

RESTAURANT_PLAN_FEATURES = {

    RESTAURANT_PLAN_FREE: {

        "profile":
            True,

        "reel":
            True,

        "gallery":
            False,

        "opening_hours":
            False,

        "customer_experiences":
            False,

        "stories":
            False,

        "analytics":
            False,
    },


    RESTAURANT_PLAN_STANDARD: {

        "profile":
            True,

        "reel":
            True,

        "gallery":
            True,

        "opening_hours":
            True,

        "customer_experiences":
            True,

        "stories":
            False,

        "analytics":
            False,
    },


    RESTAURANT_PLAN_PREMIUM: {

        "profile":
            True,

        "reel":
            True,

        "gallery":
            True,

        "opening_hours":
            True,

        "customer_experiences":
            True,

        "stories":
            True,

        "analytics":
            True,
    },
}


# ============================================================
# RESTAURANT SUBSCRIPTION GRACE PERIOD
# ============================================================

RESTAURANT_SUBSCRIPTION_GRACE_DAYS = 5


# ============================================================
# RESTAURANT SUBSCRIPTION PAYMENT SETTINGS
# ============================================================




RESTAURANT_PAYABLE_PLANS = {

    RESTAURANT_PLAN_STANDARD: {

        "name":
            "Kalxa Restaurant Standard",

        "price":
            Decimal("219.00"),
    },


    RESTAURANT_PLAN_PREMIUM: {

        "name":
            "Kalxa Restaurant Premium",

        "price":
            Decimal("299.00"),
    },
}
# ============================================================
# KALXA CROSS-APP ATTRIBUTION
# ============================================================

KALXA_ATTRIBUTION_SECRET = (
    os.getenv(
        "KALXA_ATTRIBUTION_SECRET",
        "",
    )
    .strip()
)

KALXA_ATTRIBUTION_MAX_AGE_SECONDS = (
    7 * 24 * 60 * 60
)

KALXA_ATTRIBUTION_SALT = (
    "kalxa-restaurant-attribution"
)
# ============================================================

# RESTAURANT OPENING HOURS

# ============================================================

from datetime import datetime

from flask import (
abort,
flash,
redirect,
request,
url_for,
)

RESTAURANT_WEEKDAYS = (
"monday",
"tuesday",
"wednesday",
"thursday",
"friday",
"saturday",
"sunday",
)

# ============================================================

# TIME PARSER

# ============================================================


# ============================================================
# RESTAURANT ADVERTISING
# ============================================================
RESTAURANT_SUBSCRIPTION_GRACE_DAYS = 5


RESTAURANT_POSTER_MAX_FILE_BYTES = (
    8 * 1024 * 1024
)

RESTAURANT_POSTER_ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}



def allowed_restaurant_poster_filename(
    filename,
):

    if (
        not filename
        or "." not in filename
    ):
        return False

    extension = (
        filename
        .rsplit(
            ".",
            1,
        )[1]
        .lower()
    )

    return (
        extension
        in RESTAURANT_POSTER_ALLOWED_EXTENSIONS
    )
# ============================================================
# KALXA FEATURED LISTING
# ============================================================

FEATURED_LISTING_3_DAY_PRICE = Decimal(
    os.environ.get(
        "FEATURED_LISTING_3_DAY_PRICE",
        "9.00",
    )
)

FEATURED_LISTING_7_DAY_PRICE = Decimal(
    os.environ.get(
        "FEATURED_LISTING_7_DAY_PRICE",
        "19.00",
    )
)

FEATURED_LISTING_14_DAY_PRICE = Decimal(
    os.environ.get(
        "FEATURED_LISTING_14_DAY_PRICE",
        "29.00",
    )
)

FEATURED_LISTING_PLANS = {
    "3_day": {
        "name": "3 Day Featured Listing",
        "price": FEATURED_LISTING_3_DAY_PRICE,
        "duration_days": 3,
    },
    "7_day": {
        "name": "7 Day Featured Listing",
        "price": FEATURED_LISTING_7_DAY_PRICE,
        "duration_days": 7,
    },
    "14_day": {
        "name": "14 Day Featured Listing",
        "price": FEATURED_LISTING_14_DAY_PRICE,
        "duration_days": 14,
    },
}

FEATURED_IMAGE_MAX_COUNT = 3
FEATURED_IMAGE_MAX_BYTES = 5 * 1024 * 1024


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


# ============================================================
# STORIES CONVERSION ANALYTICS API
# ============================================================


# ============================================================
# GET RESTAURANT ANALYTICS SESSION
# ============================================================

def get_restaurant_analytics_session_id():

    session_id = session.get(
        RESTAURANT_ANALYTICS_SESSION_KEY
    )

    if not session_id:

        session_id = (
            uuid4().hex
        )

        session[
            RESTAURANT_ANALYTICS_SESSION_KEY
        ] = session_id

    return session_id



# ============================================================
# CAPTURE RESTAURANT ATTRIBUTION
# ============================================================



def cloudinary_reels_configured():

    return all(
        [
            CLOUDINARY_CLOUD_NAME,
            CLOUDINARY_API_KEY,
            CLOUDINARY_API_SECRET,
        ]
    )


def allowed_event_reel_filename(filename):

    if (
        not filename
        or "." not in filename
    ):
        return False

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    return (
        extension
        in EVENT_REEL_ALLOWED_EXTENSIONS
    )


# ============================================================
# RECORD RESTAURANT ANALYTICS EVENT
# ============================================================



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

            attendee_names = (
                item.attendee_names
                if isinstance(
                    item.attendee_names,
                    list,
                )
                else []
            )

            passes_to_create = max(
                0,
                item.quantity
                - existing_item_passes,
            )

            for offset in range(
                passes_to_create
            ):

                attendee_index = (
                    existing_item_passes
                    + offset
                )

                attendee_name = (
                    attendee_names[
                        attendee_index
                    ]
                    if attendee_index
                    < len(attendee_names)
                    else order.customer_name
                )

                db.session.add(
                    EntryPass(
                        order_id=order.id,
                        order_item_id=item.id,
                        attendee_name=(
                            attendee_name
                            or order.customer_name
                        ),
                        entry_code=
                            generate_entry_code(),
                        status="valid",
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


# ============================================================
# PASSWORD RESET EMAIL
# ============================================================

SMTP_HOST = (
    os.environ.get(
        "SMTP_HOST",
        "",
    )
    .strip()
)


SMTP_PORT = int(
    os.environ.get(
        "SMTP_PORT",
        "587",
    )
)


SMTP_USERNAME = (
    os.environ.get(
        "SMTP_USERNAME",
        "",
    )
    .strip()
)


SMTP_PASSWORD = (
    os.environ.get(
        "SMTP_PASSWORD",
        "",
    )
    .strip()
)


SMTP_FROM_EMAIL = (
    os.environ.get(
        "SMTP_FROM_EMAIL",
        SMTP_USERNAME,
    )
    .strip()
)


PASSWORD_RESET_MAX_AGE_SECONDS = (
    60 * 60
)


def finalize_paystack_subscription_payment(
    payment,
    transaction_data,
):

    # ========================================================
    # PAYMENT RECORD SAFETY
    # ========================================================

    if not payment:

        raise RuntimeError(
            "Subscription payment record is missing."
        )


    # ========================================================
    # IDEMPOTENCY
    # ========================================================
    #
    # Paystack may send the webhook more than once, or the
    # callback and webhook may both attempt to finalize the
    # same transaction.
    #
    # A payment that has already been finalized must not
    # extend the subscription for a second time.
    # ========================================================

    if (
        payment.payment_status
        == "paid"
    ):

        return payment


    # ========================================================
    # CANCELLED PAYMENT SAFETY
    # ========================================================
    #
    # IMPORTANT:
    #
    # A cancelled payment may belong to an outdated checkout.
    #
    # Example:
    #
    # Restaurant previously had an R199 checkout.
    # Restaurant subscription price changes to R219.
    # The R199 payment is cancelled and a new R219 payment
    # is created.
    #
    # If the customer somehow completes the old R199 checkout,
    # that payment must NOT activate or extend the restaurant
    # subscription.
    # ========================================================

    if (
        payment.payment_status
        == "cancelled"
    ):

        raise RuntimeError(
            (
                "Cancelled subscription payments "
                "cannot activate subscriptions."
            )
        )


    # ========================================================
    # PAYMENT STATUS SAFETY
    # ========================================================
    #
    # Only pending subscription payments are allowed to move
    # into the paid state.
    # ========================================================

    if (
        payment.payment_status
        != "pending"
    ):

        raise RuntimeError(
            (
                "Subscription payment is not "
                "eligible for confirmation."
            )
        )


    # ========================================================
    # PAYSTACK TRANSACTION STATUS
    # ========================================================

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


    # ========================================================
    # REFERENCE VERIFICATION
    # ========================================================

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


    # ========================================================
    # AMOUNT VERIFICATION
    # ========================================================

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


    # ========================================================
    # CURRENCY VERIFICATION
    # ========================================================

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


    # ========================================================
    # ORGANIZER
    # ========================================================

    organizer = (
        payment.organizer
    )


    if not organizer:

        raise RuntimeError(
            "Subscription organizer record is missing."
        )


    # ========================================================
    # ORGANIZER SUSPENSION SAFETY
    # ========================================================

    if organizer.is_suspended:

        raise RuntimeError(
            "Suspended organizers cannot activate subscriptions."
        )


    # ========================================================
    # SUBSCRIPTION PERIOD
    # ========================================================

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

        subscription_start = (
            now
        )


    subscription_end = (
        subscription_start
        + timedelta(
            days=(
                payment.period_days
                or KALXA_SUBSCRIPTION_PERIOD_DAYS
            )
        )
    )


    # ========================================================
    # PAYMENT CONFIRMATION
    # ========================================================

    payment.payment_method = (
        "paystack"
    )


    payment.payment_status = (
        "paid"
    )


    payment.paid_at = (
        now
    )


    payment.confirmed_at = (
        now
    )


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


    # ========================================================
    # ACTIVATE ORGANIZER SUBSCRIPTION
    # ========================================================

    organizer.active = (
        True
    )


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


    # ========================================================
    # SAVE
    # ========================================================

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


# ============================================================
# RESTAURANT PUSH - AUTOMATIC COPY
# ============================================================

def restaurant_notification_copy(
    advert,
):

    title = (
        "🍔 New around you"
    )


    if advert.headline:

        body = (
            f"{advert.business_name}: "
            f"{advert.headline}"
        )

    else:

        body = (
            f"{advert.business_name} "
            "just added something new on Kalxa."
        )


    if advert.area:

        body = (
            f"{body} · {advert.area}"
        )


    return (
        title[:120],
        body[:500],
    )

# ============================================================
# AUTOMATIC RESTAURANT PUSH
# ============================================================

# ============================================================
# AUTOMATIC RESTAURANT PUSH
# ============================================================

def send_automatic_restaurant_push(
    advert,
):

    # ========================================================
    # RESTAURANT REQUIRED
    # ========================================================

    if not advert:

        return None


    # ========================================================
    # RESTAURANT MUST BE ACTIVE
    # ========================================================

    if not advert.active:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "is inactive "
                "advert_id=%s"
            ),
            advert.id,
        )

        return None


    # ========================================================
    # RESTAURANT OWNER REQUIRED
    # ========================================================
    #
    # IMPORTANT:
    #
    # We require a valid restaurant owner account, but we
    # deliberately DO NOT require:
    #
    #     organizer.is_subscription_active
    #
    # That property belongs to the legacy Organizer SaaS
    # subscription system.
    #
    # Restaurant feature access is now controlled by the
    # RestaurantAdvert Free / Standard / Premium plan.
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "has no organizer "
                "advert_id=%s"
            ),
            advert.id,
        )

        return None


    # ========================================================
    # ORGANIZER ACCOUNT MUST BE ACTIVE
    # ========================================================

    if not organizer.active:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "owner account is inactive "
                "advert_id=%s "
                "organizer_id=%s"
            ),
            advert.id,
            organizer.id,
        )

        return None


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if (
        account_type
        != "restaurant"
    ):

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because organizer "
                "is not a restaurant account "
                "advert_id=%s "
                "organizer_id=%s"
            ),
            advert.id,
            organizer.id,
        )

        return None


    # ========================================================
    # RESTAURANT PLAN MUST BE ACTIVE
    # ========================================================
    #
    # FREE:
    #
    #     active
    #     no expiry required
    #
    # STANDARD / PREMIUM:
    #
    #     active
    #     future expiry required
    #
    # This is controlled by RestaurantAdvert rather than the
    # old Organizer subscription.
    # ========================================================

    if not advert.is_restaurant_subscription_active:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "plan is inactive "
                "advert_id=%s "
                "plan=%s"
            ),
            advert.id,
            advert.normalized_subscription_tier,
        )

        return None


    # ========================================================
    # REEL / DISCOVERY FEATURE
    # ========================================================
    #
    # Restaurant discovery/reel is currently available on:
    #
    #     FREE
    #     STANDARD
    #     PREMIUM
    #
    # Using the feature property keeps this function safe if
    # the plan matrix changes later.
    # ========================================================

    if not advert.can_use_reel:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "plan does not allow reels "
                "advert_id=%s "
                "plan=%s"
            ),
            advert.id,
            advert.normalized_subscription_tier,
        )

        return None


    # ========================================================
    # CAMPAIGN START DATE
    # ========================================================

    now = (
        datetime.utcnow()
    )


    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "campaign has not started "
                "advert_id=%s starts_at=%s"
            ),
            advert.id,
            advert.starts_at,
        )

        return None


    # ========================================================
    # CAMPAIGN END DATE
    # ========================================================

    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because restaurant "
                "campaign has expired "
                "advert_id=%s ends_at=%s"
            ),
            advert.id,
            advert.ends_at,
        )

        return None


    # ========================================================
    # FIREBASE REQUIRED
    # ========================================================

    if not firebase_admin_configured():

        current_app.logger.warning(
            (
                "[Restaurant Auto Push] "
                "Firebase Admin is not configured "
                "advert_id=%s"
            ),
            advert.id,
        )

        return None


    # ========================================================
    # AREA REQUIRED
    # ========================================================

    if not advert.area:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Skipped because advert has no area "
                "advert_id=%s"
            ),
            advert.id,
        )

        return None


    # ========================================================
    # PREVENT ACCIDENTAL DUPLICATE AUTO PUSH
    # ========================================================
    #
    # A restaurant advert should not automatically create
    # another push campaign if one has already been created
    # for this advert.
    # ========================================================

    existing_campaign = (
        PushCampaign.query

        .filter_by(
            restaurant_advert_id=(
                advert.id
            ),

            campaign_type=(
                "restaurant"
            ),

            created_by=(
                "restaurant_auto"
            ),
        )

        .filter(
            PushCampaign.status.in_(
                [
                    "draft",
                    "processing",
                    "completed",
                    "partial",
                ]
            )
        )

        .order_by(
            PushCampaign.created_at.desc()
        )

        .first()
    )


    if existing_campaign:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "Already created "
                "advert_id=%s "
                "campaign_id=%s"
            ),
            advert.id,
            existing_campaign.id,
        )

        return existing_campaign


    # ========================================================
    # AUDIENCE
    # ========================================================

    subscriptions = (
        get_restaurant_push_subscriptions(
            advert
        )
    )


    if not subscriptions:

        current_app.logger.info(
            (
                "[Restaurant Auto Push] "
                "No matching subscribers "
                "advert_id=%s area=%s"
            ),
            advert.id,
            advert.area,
        )

        return None


    # ========================================================
    # NOTIFICATION COPY
    # ========================================================

    (
        title,
        body,
    ) = (
        restaurant_notification_copy(
            advert
        )
    )


    # ========================================================
    # CREATE PUSH CAMPAIGN
    # ========================================================

    campaign = PushCampaign(

        campaign_type=(
            "restaurant"
        ),

        restaurant_advert_id=(
            advert.id
        ),

        event_id=None,

        title=(
            title
        ),

        body=(
            body
        ),

        target_url=(
            url_for(
                "restaurant_page",

                advert_id=(
                    advert.id
                ),

                _external=True,
            )
        ),

        target_mode=(
            "area"
        ),

        target_area=(
            advert.area
        ),

        target_latitude=None,

        target_longitude=None,

        radius_km=None,

        status=(
            "draft"
        ),

        recipient_count=(
            len(
                subscriptions
            )
        ),

        created_by=(
            "restaurant_auto"
        ),
    )


    # ========================================================
    # SAVE CAMPAIGN BEFORE SENDING
    # ========================================================

    try:

        db.session.add(
            campaign
        )

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Auto Push] "
                "Campaign creation failed "
                "advert_id=%s "
                "error=%s"
            ),
            advert.id,
            error,
        )


        return None


    # ========================================================
    # SEND
    # ========================================================

    try:

        send_push_campaign(
            campaign,
            subscriptions,
        )


    except Exception as error:

        db.session.rollback()


        # ----------------------------------------------------
        # RELOAD CAMPAIGN
        # ----------------------------------------------------

        campaign = (
            db.session.get(
                PushCampaign,
                campaign.id,
            )
        )


        # ----------------------------------------------------
        # MARK AS FAILED
        # ----------------------------------------------------

        if campaign:

            campaign.status = (
                "failed"
            )


            try:

                db.session.commit()

            except Exception:

                db.session.rollback()


                current_app.logger.exception(
                    (
                        "[Restaurant Auto Push] "
                        "Unable to mark failed "
                        "campaign "
                        "advert_id=%s "
                        "campaign_id=%s"
                    ),
                    advert.id,
                    campaign.id,
                )


        current_app.logger.exception(
            (
                "[Restaurant Auto Push] "
                "Firebase send failed "
                "advert_id=%s "
                "campaign_id=%s "
                "error=%s"
            ),
            advert.id,
            (
                campaign.id
                if campaign
                else None
            ),
            error,
        )


        return campaign


    # ========================================================
    # FINISHED
    # ========================================================

    current_app.logger.info(
        (
            "[Restaurant Auto Push] "
            "Finished "
            "advert_id=%s "
            "campaign_id=%s "
            "success=%s "
            "failed=%s"
        ),
        advert.id,
        campaign.id,
        campaign.success_count,
        campaign.failure_count,
    )


    return campaign



# ============================================================
# FINALIZE RESTAURANT SUBSCRIPTION PAYMENT
# ============================================================

def finalize_restaurant_subscription_payment(
    payment,
    transaction_data,
):

    # ========================================================
    # PAYMENT REQUIRED
    # ========================================================

    if not payment:

        raise RuntimeError(
            "Restaurant subscription payment was not found."
        )


    # ========================================================
    # IDEMPOTENCY
    # ========================================================
    #
    # The callback and webhook may both try to finalize the
    # same transaction.
    #
    # Never extend the subscription twice.
    # ========================================================

    if payment.payment_status == "paid":

        return payment


    if payment.payment_status == "cancelled":

        raise RuntimeError(
            "This restaurant subscription payment was cancelled."
        )


    # ========================================================
    # TRANSACTION STATUS
    # ========================================================

    transaction_status = (
        str(
            transaction_data.get(
                "status",
                "",
            )
        )
        .strip()
        .lower()
    )


    if transaction_status != "success":

        raise RuntimeError(
            (
                "Paystack transaction is not successful. "
                f"status={transaction_status or 'unknown'}"
            )
        )


    # ========================================================
    # REFERENCE
    # ========================================================

    transaction_reference = (
        str(
            transaction_data.get(
                "reference",
                "",
            )
        )
        .strip()
    )


    if (
        not transaction_reference
        or transaction_reference
        != payment.payment_reference
    ):

        raise RuntimeError(
            "Paystack transaction reference does not match."
        )


    # ========================================================
    # CURRENCY
    # ========================================================

    transaction_currency = (
        str(
            transaction_data.get(
                "currency",
                "",
            )
        )
        .strip()
        .upper()
    )


    expected_currency = (
        payment.currency
        or "ZAR"
    ).strip().upper()


    if transaction_currency != expected_currency:

        raise RuntimeError(
            "Paystack transaction currency does not match."
        )


    # ========================================================
    # AMOUNT
    # ========================================================
    #
    # Paystack returns the amount in cents.
    #
    # R219.00 = 21900
    # R299.00 = 29900
    # ========================================================

    expected_amount_cents = int(
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
            rounding=ROUND_UP,
        )
    )


    try:

        transaction_amount_cents = int(
            transaction_data.get(
                "amount"
            )
        )


    except (
        TypeError,
        ValueError,
    ):

        raise RuntimeError(
            "Paystack transaction amount is invalid."
        )


    if (
        transaction_amount_cents
        != expected_amount_cents
    ):

        raise RuntimeError(
            "Paystack transaction amount does not match."
        )


    # ========================================================
    # VALIDATE PLAN SNAPSHOT
    # ========================================================

    plan_tier = (
        payment.plan_tier
        or ""
    ).strip().lower()


    if plan_tier not in RESTAURANT_PAYABLE_PLANS:

        raise RuntimeError(
            "Restaurant subscription plan is invalid."
        )


    expected_plan = (
        RESTAURANT_PAYABLE_PLANS[
            plan_tier
        ]
    )


    expected_plan_amount = (
        Decimal(
            str(
                expected_plan[
                    "price"
                ]
            )
        )
    )


    payment_amount = (
        Decimal(
            str(
                payment.amount
            )
        )
    )


    if payment_amount != expected_plan_amount:

        raise RuntimeError(
            "Restaurant subscription plan price does not match."
        )


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=payment.restaurant_advert_id,
            organizer_id=payment.organizer_id,
        )
        .first()
    )


    if not advert:

        raise RuntimeError(
            "Restaurant linked to payment was not found."
        )


    # ========================================================
    # ORGANIZER
    # ========================================================

    organizer = (
        Organizer.query
        .filter_by(
            id=payment.organizer_id
        )
        .first()
    )


    if not organizer:

        raise RuntimeError(
            "Restaurant owner was not found."
        )


    if not organizer.active:

        raise RuntimeError(
            "Restaurant owner account is inactive."
        )


    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if account_type != "restaurant":

        raise RuntimeError(
            "Payment does not belong to a restaurant account."
        )


    # ========================================================
    # PAYMENT TIME
    # ========================================================

    now = (
        datetime.utcnow()
    )


    # ========================================================
    # SUBSCRIPTION START
    # ========================================================
    #
    # RULE:
    #
    # If the restaurant is renewing the SAME paid plan while
    # still active or within grace, continue from the previous
    # paid expiry date.
    #
    # Example:
    #
    # Premium expired 1 Oct
    # Restaurant pays 3 Oct during grace
    #
    # New period:
    #     1 Oct -> 31 Oct
    #
    # This preserves the restaurant's billing cycle.
    #
    # For:
    #
    #     Free -> Standard
    #     Free -> Premium
    #     Standard -> Premium
    #
    # start a fresh period from payment time.
    # ========================================================

    same_paid_plan = (
        advert.normalized_subscription_tier
        == plan_tier
        and
        plan_tier
        in (
            RESTAURANT_PLAN_STANDARD,
            RESTAURANT_PLAN_PREMIUM,
        )
    )


    if (
        same_paid_plan
        and
        advert.subscription_expires_at
    ):

        subscription_start = (
            advert.subscription_expires_at
        )


    else:

        subscription_start = (
            now
        )


    # ========================================================
    # SUBSCRIPTION END
    # ========================================================

    subscription_end = (
        subscription_start
        +
        timedelta(
            days=payment.period_days
        )
    )


    # ========================================================
    # PAYSTACK AUDIT
    # ========================================================

    transaction_id = (
        transaction_data.get(
            "id"
        )
    )


    payment_channel = (
        transaction_data.get(
            "channel"
        )
    )


    # ========================================================
    # UPDATE PAYMENT
    # ========================================================

    payment.payment_status = (
        "paid"
    )

    payment.paystack_transaction_id = (
        str(transaction_id)
        if transaction_id is not None
        else None
    )

    payment.payment_channel = (
        str(payment_channel)
        if payment_channel
        else None
    )

    payment.payment_verified_at = (
        now
    )

    payment.paid_at = (
        now
    )

    payment.confirmed_at = (
        now
    )

    payment.confirmed_by = (
        "paystack"
    )

    payment.subscription_start = (
        subscription_start
    )

    payment.subscription_end = (
        subscription_end
    )


    # ========================================================
    # ACTIVATE RESTAURANT PLAN
    # ========================================================

    advert.subscription_tier = (
        plan_tier
    )

    advert.subscription_status = (
        "active"
    )

    advert.subscription_started_at = (
        subscription_start
    )

    advert.subscription_expires_at = (
        subscription_end
    )


    # ========================================================
    # COMMIT ATOMICALLY
    # ========================================================

    db.session.commit()


    current_app.logger.info(
        (
            "[Restaurant Subscription] "
            "Payment finalized "
            "restaurant_id=%s "
            "organizer_id=%s "
            "plan=%s "
            "reference=%s "
            "subscription_end=%s"
        ),
        advert.id,
        organizer.id,
        plan_tier,
        payment.payment_reference,
        subscription_end,
    )


    return payment
# ============================================================
# FIREBASE WEB PUSH CONFIGURED
# ============================================================

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
# RESTAURANT HAS ACTIVE SUBSCRIPTION
# ============================================================

def restaurant_has_active_subscription(
    advert,
):

    # ========================================================
    # RESTAURANT REQUIRED
    # ========================================================

    if not advert:

        return False


    # ========================================================
    # RESTAURANT MUST BE ACTIVE
    # ========================================================

    if not advert.active:

        return False


    # ========================================================
    # ORGANIZER / OWNER REQUIRED
    # ========================================================
    #
    # We still require the restaurant to belong to a valid
    # Organizer account.
    #
    # We deliberately DO NOT require:
    #
    #     organizer.is_subscription_active
    #
    # That belongs to the legacy Organizer SaaS subscription.
    #
    # Restaurant subscription access is now controlled by
    # RestaurantAdvert.
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        return False


    # ========================================================
    # ORGANIZER ACCOUNT MUST BE ACTIVE
    # ========================================================

    if not organizer.active:

        return False


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if (
        account_type
        != "restaurant"
    ):

        return False


    # ========================================================
    # RESTAURANT PLAN
    # ========================================================
    #
    # FREE
    # --------------------------------------------------------
    #
    # subscription_tier:
    #     free
    #
    # subscription_status:
    #     active
    #
    # subscription_expires_at:
    #     None
    #
    # Result:
    #     ACTIVE
    #
    #
    # STANDARD / PREMIUM
    # --------------------------------------------------------
    #
    # subscription_status:
    #     active
    #
    # subscription_expires_at:
    #     future datetime
    #
    # Result:
    #     ACTIVE
    #
    #
    # Expired paid plans return False here.
    # ========================================================

    if not advert.is_restaurant_subscription_active:

        return False


    # ========================================================
    # ACTIVE RESTAURANT
    # ========================================================

    return True




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
            or_(
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

# ============================================================
# RESTAURANT PUSH - NORMALIZE AREA
# ============================================================

def normalize_notification_area(
    value,
):

    return (
        " ".join(
            str(
                value
                or ""
            )
            .strip()
            .lower()
            .split()
        )
    )


# ============================================================
# RESTAURANT PUSH - LOCAL SUBSCRIPTIONS
# ============================================================

def get_restaurant_push_subscriptions(
    advert,
):

    if not advert:

        return []


    advert_area = (
        normalize_notification_area(
            advert.area
        )
    )


    if not advert_area:

        return []


    active_subscriptions = (
        get_active_push_subscriptions()
    )


    matched = []


    for subscription in active_subscriptions:

        subscription_area = (
            normalize_notification_area(
                subscription.home_area
            )
        )


        if not subscription_area:

            continue


        if (
            subscription_area
            == advert_area
        ):

            matched.append(
                subscription
            )


    return matched


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

                "campaign_type":
                  str(
                    campaign.campaign_type
                    or "event"
                  ),

                "event_id":
                  (
                    str(
                      campaign.event_id
                    )
                    if campaign.event_id
                    else ""
                  ),

                "restaurant_advert_id":
                  (
                    str(
                     campaign.restaurant_advert_id
                    )
                    if campaign.restaurant_advert_id
                    else ""
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
# RESTAURANT SUBSCRIPTION PAYMENT REFERENCE
# ============================================================

def generate_restaurant_subscription_payment_reference():

    return (
        "KXR-"
        + datetime.utcnow().strftime(
            "%Y%m%d%H%M%S"
        )
        + "-"
        + secrets.token_hex(6).upper()
    )

# ============================================================
# PUBLIC RESTAURANT API
# ============================================================

@app.route(
    "/api/public/restaurants",
    methods=["GET"],
)
def api_public_restaurants():

    search = (
        request.args
        .get(
            "q",
            "",
        )
        .strip()
    )

    query = (
        RestaurantAdvert.query
        .filter(
            RestaurantAdvert.active.is_(True)
        )
    )

    if search:

        pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                RestaurantAdvert.business_name.ilike(
                    pattern
                ),
                RestaurantAdvert.area.ilike(
                    pattern
                ),
            )
        )

    restaurants = (
        query
        .order_by(
            RestaurantAdvert.business_name.asc()
        )
        .limit(30)
        .all()
    )

    return jsonify({
        "restaurants": [
            serialize_public_restaurant(
                restaurant
            )
            for restaurant in restaurants
        ]
    })


# ============================================================
# SINGLE PUBLIC RESTAURANT
# ============================================================

@app.route(
    "/api/public/restaurants/<int:advert_id>",
    methods=["GET"],
)
def api_public_restaurant(advert_id):

    restaurant = (
        RestaurantAdvert.query
        .filter(
            RestaurantAdvert.id == advert_id,
            RestaurantAdvert.active.is_(True),
        )
        .first()
    )

    if restaurant is None:

        return jsonify({
            "error": "Restaurant not found."
        }), 404

    return jsonify(
        serialize_public_restaurant(
            restaurant
        )
    )


# ============================================================
# RESTAURANT SERIALIZER
# ============================================================

def serialize_public_restaurant(
    restaurant
):

    return {

        "id":
            restaurant.id,

        "business_name":
            restaurant.business_name,

        "headline":
            restaurant.headline,

        "description":
            restaurant.description,

        "price_text":
            restaurant.price_text,

        "address":
            restaurant.address,

        "area":
            restaurant.area,

        "directions_url":
            restaurant.directions_url,

        "active":
            bool(
                restaurant.active
            ),

        "profile_path":
            url_for(
                "restaurant_page",
                advert_id=restaurant.id,
            ),

    }

    # ============================================================
# REQUIRE ACTIVE RESTAURANT SUBSCRIPTION
# ============================================================

def require_restaurant_subscription():

    # ========================================================
    # CURRENT ORGANIZER
    # ========================================================

    organizer = (
        get_current_organizer()
    )


    # ========================================================
    # AUTHENTICATION
    # ========================================================

    if not organizer:

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # ACCOUNT TYPE
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    # ========================================================
    # RESTAURANT ACCOUNT REQUIRED
    # ========================================================
    #
    # Restaurant tools are only available to accounts whose
    # account_type is:
    #
    #     restaurant
    #
    # Event organizer accounts should not be able to enter
    # restaurant management routes.
    # ========================================================

    if (
        account_type
        != "restaurant"
    ):

        flash(
            (
                "Restaurant tools are only "
                "available to restaurant accounts."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # RESTAURANT PLAN ARCHITECTURE
    # ========================================================
    #
    # IMPORTANT:
    #
    # We deliberately DO NOT check:
    #
    #     organizer.is_subscription_active
    #
    # here anymore.
    #
    # Restaurant access now follows the RestaurantAdvert plan:
    #
    # FREE
    #     R0
    #     Basic restaurant profile
    #     Main poster
    #     Restaurant reel/discovery
    #
    # STANDARD
    #     R219/month
    #     Free features
    #     Gallery
    #     Operational hours
    #     Customer experiences
    #     Rating QR
    #
    # PREMIUM
    #     R299/month
    #     Standard features
    #     Kalxa Stories eligibility
    #     Restaurant analytics
    #
    # Because Free is a valid active restaurant plan, a
    # restaurant account must NOT be forced to purchase the
    # old Organizer subscription merely to create/manage its
    # Free restaurant profile.
    #
    # Paid feature permissions are enforced on the actual
    # RestaurantAdvert through:
    #
    #     advert.can_use_gallery
    #     advert.can_use_opening_hours
    #     advert.can_receive_customer_experiences
    #     advert.can_use_stories
    #     advert.can_view_analytics
    #
    # This helper therefore controls access to RESTAURANT
    # TOOLS, not access to a particular paid restaurant
    # feature.
    # ========================================================


    # ========================================================
    # ACCESS ALLOWED
    # ========================================================

    return None
# ============================================================
# RESTAURANT ADVERT HELPERS
# ============================================================

def build_restaurant_whatsapp_url(
    phone_number,
):

    if not phone_number:
        return None


    digits = "".join(
        character
        for character in str(
            phone_number
        )
        if character.isdigit()
    )


    if not digits:
        return None


    # South African local format:
    # 0791234567 -> 27791234567
    if digits.startswith("0"):

        digits = (
            "27"
            + digits[1:]
        )


    return (
        f"https://wa.me/{digits}"
    )



def build_restaurant_phone_url(
    phone_number,
):

    if not phone_number:
        return None


    cleaned = "".join(
        character
        for character in str(
            phone_number
        )
        if (
            character.isdigit()
            or character == "+"
        )
    )


    if not cleaned:
        return None


    return (
        f"tel:{cleaned}"
    )



def valid_restaurant_directions_url(
    value,
):

    if not value:
        return None


    value = (
        str(value)
        .strip()
    )


    if not (
        value.startswith(
            "https://"
        )
        or value.startswith(
            "http://"
        )
    ):

        return None


    return value



def parse_restaurant_time(
    raw_value,
):

    """
    Convert HTML <input type="time"> values such as:

        09:00
        21:30

    into Python datetime.time objects.
    """

    raw_value = (
        raw_value
        or
        ""
    ).strip()

    if not raw_value:

        return None

    try:

        return datetime.strptime(
            raw_value,
            "%H:%M",
        ).time()

    except ValueError:

        raise ValueError(
            f"Invalid time value: {raw_value}"
        )
# ============================================================

# RESTAURANT HOURS PAYLOAD

# ============================================================

def build_restaurant_hours_payload(
  advert,
):



  payload = {}


  existing_hours = {
    opening_hour.day_of_week:
        opening_hour

    for opening_hour
    in advert.opening_hours
  }


  for day in RESTAURANT_WEEKDAYS:

    opening_hour = (
        existing_hours.get(
            day
        )
    )


    if not opening_hour:

        payload[
            day
        ] = {

            "open":
                "",

            "close":
                "",

            "closed":
                True,

        }


        continue


    payload[
        day
    ] = (
        opening_hour
        .to_public_dict()
    )


  return payload


def get_kalxa_attribution_serializer():
    """
    Build the serializer used to verify attribution tokens
    created by Kalxa Stories.
    """

    if not KALXA_ATTRIBUTION_SECRET:

        return None


    return URLSafeTimedSerializer(
        KALXA_ATTRIBUTION_SECRET,
        salt=KALXA_ATTRIBUTION_SALT,
    )


def capture_restaurant_attribution(
    advert,
):
    """
    Verify a signed Kalxa Stories attribution token and
    persist the verified attribution inside the Ticketing
    Flask session.

    Expected URL:

        /restaurant/2?kat=<SIGNED_TOKEN>

    The token is created by Kalxa Stories using the same
    KALXA_ATTRIBUTION_SECRET and salt.

    Stored attribution also receives a captured_at timestamp
    so Ticketing can enforce its own attribution window after
    the signed token has been accepted.

    No customer name, email address, phone number or IP
    address is stored.
    """

    # ========================================================
    # CURRENT TIME
    # ========================================================

    now = datetime.now(
        timezone.utc
    )


    # ========================================================
    # INCOMING SIGNED TOKEN
    # ========================================================

    token = (
        request.args
        .get(
            "kat",
            "",
        )
        .strip()
    )


    # ========================================================
    # NO NEW TOKEN
    # ========================================================
    #
    # Preserve existing attribution only when:
    #
    # 1. It belongs to the restaurant currently being viewed.
    # 2. It contains a valid captured_at timestamp.
    # 3. It is still inside the attribution window.
    #
    # Old sessions created before captured_at was introduced
    # are treated as expired rather than being trusted
    # indefinitely.
    # ========================================================

    if not token:

        existing = (
            session.get(
                RESTAURANT_ATTRIBUTION_SESSION_KEY
            )
            or
            {}
        )


        if (
            existing.get(
                "restaurant_id"
            )
            != advert.id
        ):

            return {}


        captured_at_raw = (
            existing.get(
                "captured_at"
            )
        )


        if not captured_at_raw:

            session.pop(
                RESTAURANT_ATTRIBUTION_SESSION_KEY,
                None,
            )

            session.modified = True

            return {}


        try:

            captured_at = (
                datetime.fromisoformat(
                    captured_at_raw
                )
            )


            if captured_at.tzinfo is None:

                captured_at = (
                    captured_at.replace(
                        tzinfo=timezone.utc
                    )
                )


        except (
            TypeError,
            ValueError,
        ):

            session.pop(
                RESTAURANT_ATTRIBUTION_SESSION_KEY,
                None,
            )

            session.modified = True

            return {}


        attribution_age_seconds = (
            now
            -
            captured_at
        ).total_seconds()


        if (
            attribution_age_seconds < 0
            or
            attribution_age_seconds
            >
            KALXA_ATTRIBUTION_MAX_AGE_SECONDS
        ):

            session.pop(
                RESTAURANT_ATTRIBUTION_SESSION_KEY,
                None,
            )

            session.modified = True

            return {}


        return existing


    # ========================================================
    # SERIALIZER
    # ========================================================

    serializer = (
        get_kalxa_attribution_serializer()
    )


    if serializer is None:

        current_app.logger.error(
            "KALXA_ATTRIBUTION_SECRET is not configured."
        )

        return {}


    # ========================================================
    # VERIFY TOKEN
    # ========================================================

    try:

        payload = serializer.loads(
            token,
            max_age=(
                KALXA_ATTRIBUTION_MAX_AGE_SECONDS
            ),
        )

    except SignatureExpired:

        current_app.logger.info(
            "Expired Kalxa Stories attribution token."
        )

        return {}

    except BadSignature:

        current_app.logger.warning(
            "Rejected invalid Kalxa Stories "
            "attribution token."
        )

        return {}


    # ========================================================
    # VERIFY SOURCE
    # ========================================================

    if (
        payload.get(
            "source"
        )
        !=
        "kalxa_stories"
    ):

        return {}


    # ========================================================
    # VERIFY RESTAURANT
    # ========================================================

    try:

        source_restaurant_id = int(
            payload.get(
                "restaurant_id"
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return {}


    if (
        source_restaurant_id
        != advert.id
    ):

        current_app.logger.warning(
            (
                "Rejected mismatched Kalxa Stories "
                "attribution. "
                "URL restaurant=%s "
                "token restaurant=%s"
            ),
            advert.id,
            source_restaurant_id,
        )

        return {}


    # ========================================================
    # VERIFY STORY
    # ========================================================

    try:

        story_id = int(
            payload.get(
                "story_id"
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return {}


    if story_id <= 0:

        return {}


    # ========================================================
    # SOURCE SESSION
    # ========================================================

    source_session_id = (
        payload.get(
            "source_session_id"
        )
    )


    if source_session_id is not None:

        source_session_id = str(
            source_session_id
        )[:100]


    # ========================================================
    # VERIFIED ATTRIBUTION
    # ========================================================
    #
    # article_id remains the internal session key because
    # RestaurantAnalyticsEvent stores:
    #
    #     source_article_id
    #
    # captured_at controls how long this verified attribution
    # remains usable inside Ticketing.
    # ========================================================

    attribution = {

        "source":
            "kalxa_stories",

        "article_id":
            story_id,

        "restaurant_id":
            advert.id,

        "source_session_id":
            source_session_id,

        "captured_at":
            now.isoformat(),
    }


    # ========================================================
    # STORE IN SIGNED FLASK SESSION
    # ========================================================

    session[
        RESTAURANT_ATTRIBUTION_SESSION_KEY
    ] = attribution

    session.modified = True


    return attribution
# ============================================================

# CHECK RESTAURANT OWNER

# ============================================================

def restaurant_can_be_managed_by_current_organizer(
    advert,
):

    current_organizer = (
        get_current_organizer()
    )

    if not current_organizer:
        return False

    return (
        advert.organizer_id
        ==
        current_organizer.id
    )

# ============================================================

# CHECK ACTIVE RESTAURANT SUBSCRIPTION

# ============================================================

# ============================================================
# UPDATE RESTAURANT OPERATIONAL HOURS
# ============================================================

@app.route(
    "/restaurant/<int:advert_id>/hours",
    methods=["POST"],
)
def update_restaurant_hours(
    advert_id,
):

    # ========================================================
    # ORGANIZER AUTHENTICATION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    current_organizer = (
        get_current_organizer()
    )


    if not current_organizer:

        abort(401)


    # ========================================================
    # OWNER ACCOUNT ACTIVE
    # ========================================================

    if not current_organizer.active:

        abort(403)


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================
    #
    # Operational hours belong only to restaurant accounts.
    #
    # IMPORTANT:
    #
    # Do NOT check:
    #
    #     current_organizer.is_subscription_active
    #
    # That belongs to the legacy Organizer/Event SaaS
    # subscription.
    #
    # Restaurant plan access belongs to RestaurantAdvert.
    # ========================================================

    if (
        getattr(
            current_organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # RESTAURANT + OWNERSHIP
    # ========================================================
    #
    # Fetching using both IDs gives us an additional ownership
    # boundary.
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
            organizer_id=current_organizer.id,
        )

        .first_or_404()
    )


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================

    if not advert.active:

        abort(403)


    # ========================================================
    # RESTAURANT ORGANIZER SAFETY
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        abort(403)


    if not organizer.active:

        abort(403)


    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # STANDARD / PREMIUM ACTIVE
    #     -> operational hours available
    #
    # STANDARD / PREMIUM IN 5-DAY GRACE
    #     -> operational hours remain available
    #
    # AFTER GRACE
    #     -> sync automatically downgrades to Free
    #
    # FREE
    #     -> operational hours unavailable
    #
    # IMPORTANT:
    #
    # Existing RestaurantOpeningHour rows are NOT deleted when
    # a restaurant becomes Free.
    #
    # They remain stored so that upgrading again can restore
    # the feature.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # RESTAURANT PLAN PERMISSION
    # ========================================================

    if not advert.can_use_opening_hours:

        flash(
            (
                "Operational hours are available "
                "on the Standard and Premium "
                "restaurant plans."
            ),
            "error",
        )


        return redirect(
            url_for(
                "restaurant_page",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # EXISTING HOURS
    # ========================================================

    existing_hours = {

        opening_hour.day_of_week:
            opening_hour

        for opening_hour
        in (
            RestaurantOpeningHour.query

            .filter_by(
                restaurant_advert_id=advert.id
            )

            .all()
        )
    }


    # ========================================================
    # UPDATE ALL 7 DAYS
    # ========================================================

    try:

        # ====================================================
        # FINAL CAPABILITY CHECK
        # ====================================================
        #
        # Keep the actual database mutation behind the
        # RestaurantAdvert capability boundary.
        # ====================================================

        sync_restaurant_subscription(
            advert
        )


        if not advert.can_use_opening_hours:

            flash(
                (
                    "Operational hours are available "
                    "on the Standard and Premium "
                    "restaurant plans."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "restaurant_page",
                    advert_id=advert.id,
                )
            )


        # ====================================================
        # PROCESS EACH DAY
        # ====================================================

        for day in RESTAURANT_WEEKDAYS:

            # =================================================
            # CLOSED STATE
            # =================================================

            is_closed = (
                request.form.get(
                    f"{day}_closed"
                )
                == "1"
            )


            # =================================================
            # OPENING TIME
            # =================================================

            open_raw = (
                request.form.get(
                    f"{day}_open"
                )
                or ""
            ).strip()


            # =================================================
            # CLOSING TIME
            # =================================================

            close_raw = (
                request.form.get(
                    f"{day}_close"
                )
                or ""
            ).strip()


            # =================================================
            # VALIDATE TIMES
            # =================================================

            if is_closed:

                open_time = None

                close_time = None


            else:

                # =============================================
                # BOTH TIMES REQUIRED
                # =============================================

                if (
                    not open_raw
                    or
                    not close_raw
                ):

                    flash(
                        (
                            f"{day.capitalize()} requires "
                            "both an opening and closing time, "
                            "or mark the day as closed."
                        ),
                        "error",
                    )


                    return redirect(
                        url_for(
                            "restaurant_page",
                            advert_id=advert.id,
                        )
                    )


                # =============================================
                # PARSE OPENING TIME
                # =============================================

                open_time = (
                    parse_restaurant_time(
                        open_raw
                    )
                )


                # =============================================
                # PARSE CLOSING TIME
                # =============================================

                close_time = (
                    parse_restaurant_time(
                        close_raw
                    )
                )


            # =================================================
            # GET OR CREATE DAY
            # =================================================

            opening_hour = (
                existing_hours.get(
                    day
                )
            )


            if not opening_hour:

                opening_hour = (
                    RestaurantOpeningHour(

                        restaurant_advert_id=(
                            advert.id
                        ),

                        day_of_week=(
                            day
                        ),
                    )
                )


                db.session.add(
                    opening_hour
                )


                # =============================================
                # KEEP LOCAL LOOKUP SYNCHRONIZED
                # =============================================

                existing_hours[
                    day
                ] = opening_hour


            # =================================================
            # SAVE VALUES
            # =================================================

            opening_hour.open_time = (
                open_time
            )


            opening_hour.close_time = (
                close_time
            )


            opening_hour.is_closed = (
                is_closed
            )


        # ====================================================
        # COMMIT
        # ====================================================

        db.session.commit()


    # ========================================================
    # INVALID TIME VALUE
    # ========================================================

    except ValueError as error:

        db.session.rollback()


        flash(
            str(
                error
            ),
            "error",
        )


        return redirect(
            url_for(
                "restaurant_page",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Hours] "
                "Unable to update restaurant "
                "working hours "
                "advert_id=%s "
                "organizer_id=%s "
                "error=%s"
            ),
            advert.id,
            current_organizer.id,
            error,
        )


        flash(
            (
                "Unable to update working hours. "
                "Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "restaurant_page",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # SUCCESS
    # ========================================================

    flash(
        "Restaurant working hours updated.",
        "success",
    )


    return redirect(
        url_for(
            "restaurant_page",
            advert_id=advert.id,
        )
    )
# ============================================================

# ============================================================
# RESTAURANT CAMPAIGN SCHEDULING
# ============================================================

RESTAURANT_CAMPAIGN_DURATION_OPTIONS = {
    "7": 7,
    "14": 14,
    "30": 30,
}

def parse_restaurant_campaign_date(
    value,
):

    value = (
        str(
            value
            or ""
        )
        .strip()
    )


    if not value:

        return None


    try:

        return (
            datetime.strptime(
                value,
                "%Y-%m-%d",
            )
            .date()
        )


    except ValueError:

        return None




def parse_restaurant_campaign_date(value):
    """
    Parse a restaurant campaign date from an HTML date input.

    Expected format:
        YYYY-MM-DD

    Returns:
        datetime.date or None
    """

    value = str(value or "").strip()

    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()

    except (TypeError, ValueError):
        return None

RESTAURANT_CAMPAIGN_DURATION_OPTIONS = {
    "7": 7,
    "14": 14,
    "30": 30,
}


def build_restaurant_campaign_schedule(
    form,
    organizer,
    existing_advert=None,
):

    # ========================================================
    # CURRENT DATE
    # ========================================================

    today = (
        datetime.utcnow()
        .date()
    )


    # ========================================================
    # IMPORTANT - RESTAURANT PLAN ARCHITECTURE
    # ========================================================
    #
    # Restaurant campaign scheduling is no longer limited by:
    #
    #     organizer.subscription_expires_at
    #
    # The old architecture tied restaurant visibility to the
    # Organizer SaaS subscription.
    #
    # The new architecture uses RestaurantAdvert plans:
    #
    # FREE
    #     R0
    #     Profile + basic discovery/reel
    #
    # STANDARD
    #     R219/month
    #     Additional restaurant features
    #
    # PREMIUM
    #     R299/month
    #     Standard features + Stories + analytics
    #
    # Therefore this helper is now responsible ONLY for
    # validating the restaurant campaign's requested dates.
    #
    # Restaurant-plan expiry is handled separately through:
    #
    #     RestaurantAdvert.subscription_expires_at
    #
    # and the feature capability properties.
    #
    # NOTE:
    #
    # We keep the organizer argument in this function for now
    # so existing route calls do not need to change.
    # ========================================================


    # ========================================================
    # START DATE
    # ========================================================

    start_date_raw = (
        form.get(
            "start_date",
            "",
        )
        .strip()
    )


    start_date = (
        parse_restaurant_campaign_date(
            start_date_raw
        )
    )


    # ========================================================
    # DEFAULT START DATE
    # ========================================================
    #
    # If no start date is supplied, start today.
    # ========================================================

    if not start_date:

        start_date = (
            today
        )


    # ========================================================
    # NEW RESTAURANT - PAST DATE PROTECTION
    # ========================================================
    #
    # A newly created restaurant campaign cannot start in
    # the past.
    #
    # Existing adverts are allowed to retain/edit campaigns
    # whose original start date may already be in the past.
    # ========================================================

    if (
        existing_advert is None
        and
        start_date < today
    ):

        return (
            None,
            None,
            (
                "Campaign start date cannot "
                "be in the past."
            ),
        )


    # ========================================================
    # START DATETIME
    # ========================================================

    starts_at = (
        datetime.combine(
            start_date,
            datetime.min.time(),
        )
    )


    # ========================================================
    # DURATION
    # ========================================================

    duration_choice = (
        form.get(
            "duration_choice",
            "14",
        )
        .strip()
        .lower()
    )


    # ========================================================
    # PRESET DURATION
    # ========================================================

    if (
        duration_choice
        in RESTAURANT_CAMPAIGN_DURATION_OPTIONS
    ):

        duration_days = (
            RESTAURANT_CAMPAIGN_DURATION_OPTIONS[
                duration_choice
            ]
        )


        # ----------------------------------------------------
        # SAFETY
        # ----------------------------------------------------
        #
        # Duration options should always contain positive
        # integer day values.
        # ----------------------------------------------------

        try:

            duration_days = int(
                duration_days
            )

        except (
            TypeError,
            ValueError,
        ):

            return (
                None,
                None,
                (
                    "Choose a valid "
                    "campaign duration."
                ),
            )


        if duration_days <= 0:

            return (
                None,
                None,
                (
                    "Choose a valid "
                    "campaign duration."
                ),
            )


        # ----------------------------------------------------
        # EXCLUSIVE END
        # ----------------------------------------------------
        #
        # Example:
        #
        # Start:
        #     01 October 00:00
        #
        # 14-day duration:
        #     ends_at = 15 October 00:00
        #
        # This means the restaurant remains visible throughout
        # 14 October and stops being active at midnight.
        # ----------------------------------------------------

        ends_at = (
            starts_at
            + timedelta(
                days=duration_days
            )
        )


    # ========================================================
    # CUSTOM DURATION
    # ========================================================

    elif (
        duration_choice
        == "custom"
    ):

        custom_end_date_raw = (
            form.get(
                "custom_end_date",
                "",
            )
            .strip()
        )


        custom_end_date = (
            parse_restaurant_campaign_date(
                custom_end_date_raw
            )
        )


        # ----------------------------------------------------
        # END DATE REQUIRED
        # ----------------------------------------------------

        if not custom_end_date:

            return (
                None,
                None,
                (
                    "Choose the campaign "
                    "end date."
                ),
            )


        # ----------------------------------------------------
        # END CANNOT PRECEDE START
        # ----------------------------------------------------

        if (
            custom_end_date
            < start_date
        ):

            return (
                None,
                None,
                (
                    "Campaign end date cannot "
                    "be before the start date."
                ),
            )


        # ----------------------------------------------------
        # EXCLUSIVE END
        # ----------------------------------------------------
        #
        # If the user selects:
        #
        #     31 October
        #
        # the restaurant remains visible throughout that day
        # and ends:
        #
        #     01 November 00:00
        # ----------------------------------------------------

        ends_at = (
            datetime.combine(
                (
                    custom_end_date
                    + timedelta(
                        days=1
                    )
                ),
                datetime.min.time(),
            )
        )


    # ========================================================
    # INVALID DURATION
    # ========================================================

    else:

        return (
            None,
            None,
            (
                "Choose a valid "
                "campaign duration."
            ),
        )


    # ========================================================
    # FINAL DATE SAFETY
    # ========================================================

    if (
        ends_at
        <= starts_at
    ):

        return (
            None,
            None,
            (
                "Campaign end date must "
                "be after the start date."
            ),
        )


    # ========================================================
    # NO ORGANIZER SUBSCRIPTION LIMIT
    # ========================================================
    #
    # OLD LOGIC REMOVED:
    #
    #     organizer.subscription_expires_at
    #
    # Restaurant campaigns must not disappear simply because
    # the old Organizer SaaS subscription expires.
    #
    # RestaurantAdvert subscription rules now determine which
    # paid restaurant features are available.
    #
    # This is especially important for FREE restaurants:
    #
    #     subscription_tier = "free"
    #     subscription_status = "active"
    #     subscription_expires_at = None
    #
    # A Free restaurant is therefore allowed to maintain its
    # basic restaurant presence without requiring an expiry
    # date.
    # ========================================================


    # ========================================================
    # SUCCESS
    # ========================================================

    return (
        starts_at,
        ends_at,
        None,
    )

# ============================================================
# STAGE 6 - RESTAURANT CONVERSION ANALYTICS
# ============================================================

RESTAURANT_ANALYTICS_ATTRIBUTION_KEY = (
    "kalxa_restaurant_attribution"
)

RESTAURANT_ANALYTICS_DEDUPLICATION_MINUTES = 30


# ============================================================
# SAFE POSITIVE INTEGER
# ============================================================

def parse_positive_int(
    value,
):

    if value is None:

        return None

    try:

        parsed_value = int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if parsed_value <= 0:

        return None

    return parsed_value


# ============================================================
# CAPTURE STORIES ATTRIBUTION
# ============================================================



# ============================================================
# GET STORED RESTAURANT ATTRIBUTION
# ============================================================

def get_restaurant_attribution(
    restaurant_id,
):

    attribution = (
        session.get(
            RESTAURANT_ANALYTICS_ATTRIBUTION_KEY
        )
        or {}
    )


    if (
        attribution.get(
            "restaurant_id"
        )
        != restaurant_id
    ):

        return {}


    if (
        attribution.get(
            "source"
        )
        != "stories"
    ):

        return {}


    return attribution


# ============================================================
# RECENT RESTAURANT ANALYTICS EVENT
# ============================================================
def recent_restaurant_analytics_event_exists(
    restaurant_id,
    event_type,
    session_id,
    source=None,
    source_article_id=None,
):
    """
    Check whether the same anonymous analytics event was
    recently recorded.

    Current deduplication identity:

        restaurant
        + event type
        + anonymous session
        + traffic source
        + source article (when applicable)

    This prevents repeated refreshes from inflating views
    while preserving separate attribution journeys.

    Example:

        Same browser
        Restaurant #2
        restaurant_view
        source = direct
        within 30 minutes

            -> duplicate

        Same browser
        Restaurant #2
        restaurant_view
        source = kalxa_stories
        Story #1

            -> separate attributed journey
    """

    # ========================================================
    # CUTOFF
    # ========================================================

    cutoff = (
        datetime.now(
            timezone.utc
        )
        -
        timedelta(
            minutes=(
                RESTAURANT_ANALYTICS_DEDUPLICATION_MINUTES
            )
        )
    )


    # ========================================================
    # BASE QUERY
    # ========================================================

    query = (
        RestaurantAnalyticsEvent.query

        .filter(
            RestaurantAnalyticsEvent.restaurant_id
            == restaurant_id,

            RestaurantAnalyticsEvent.event_type
            == event_type,

            RestaurantAnalyticsEvent.session_id
            == session_id,

            RestaurantAnalyticsEvent.created_at
            >= cutoff,
        )
    )


    # ========================================================
    # TRAFFIC SOURCE
    # ========================================================

    if source is None:

        query = query.filter(
            RestaurantAnalyticsEvent
            .source
            .is_(None)
        )

    else:

        query = query.filter(
            RestaurantAnalyticsEvent.source
            == source
        )


    # ========================================================
    # SOURCE ARTICLE
    # ========================================================

    if source_article_id is None:

        query = query.filter(
            RestaurantAnalyticsEvent
            .source_article_id
            .is_(None)
        )

    else:

        query = query.filter(
            RestaurantAnalyticsEvent
            .source_article_id
            == source_article_id
        )


    # ========================================================
    # RESULT
    # ========================================================

    return (
        query.first()
        is not None
    ) #============================================================
# RECORD RESTAURANT ANALYTICS EVENT
# ============================================================

def record_restaurant_analytics_event(
    advert=None,
    restaurant_id=None,
    event_type=None,
    metadata=None,
    deduplicate=False,
):
    """
    Record one anonymous Kalxa Ticketing restaurant
    analytics event.

    The helper supports either:

        advert=advert

    or:

        restaurant_id=advert.id

    Traffic classification:

        source = "kalxa_stories"

            when a valid, unexpired, verified Kalxa Stories
            attribution exists for this restaurant.

        source = "direct"

            when no valid attribution exists.

    Stories attribution is accepted only when:

        1. It belongs to this restaurant.
        2. It came from the verified Ticketing session.
        3. It contains a valid captured_at timestamp.
        4. It is still inside the attribution window.

    Expired or invalid attribution is cleared before the
    analytics event is recorded.

    Analytics failures must never block the customer journey.
    """

    # ========================================================
    # RESOLVE RESTAURANT ID
    # ========================================================

    resolved_restaurant_id = None


    if advert is not None:

        resolved_restaurant_id = (
            getattr(
                advert,
                "id",
                None,
            )
        )


    if (
        resolved_restaurant_id
        is None
        and
        restaurant_id is not None
    ):

        try:

            resolved_restaurant_id = int(
                restaurant_id
            )

        except (
            TypeError,
            ValueError,
        ):

            resolved_restaurant_id = None


    if resolved_restaurant_id is None:

        current_app.logger.warning(
            "Restaurant analytics event skipped: "
            "restaurant ID missing."
        )

        return False


    # ========================================================
    # VALIDATE EVENT TYPE
    # ========================================================

    if not event_type:

        current_app.logger.warning(
            "Restaurant analytics event skipped: "
            "event type missing."
        )

        return False


    # ========================================================
    # ANONYMOUS RESTAURANT SESSION
    # ========================================================

    anonymous_session_id = (
        get_restaurant_experience_session_id()
    )


    # ========================================================
    # GET VERIFIED STORIES ATTRIBUTION
    # ========================================================

    attribution = (
        session.get(
            RESTAURANT_ATTRIBUTION_SESSION_KEY,
            {},
        )
        or
        {}
    )


    # ========================================================
    # RESTAURANT SAFETY CHECK
    # ========================================================

    attributed_restaurant_id = (
        attribution.get(
            "restaurant_id"
        )
    )


    if (
        attributed_restaurant_id
        != resolved_restaurant_id
    ):

        attribution = {}


    # ========================================================
    # ATTRIBUTION EXPIRY CHECK
    # ========================================================

    if attribution:

        captured_at_raw = (
            attribution.get(
                "captured_at"
            )
        )


        if not captured_at_raw:

            attribution = {}

            session.pop(
                RESTAURANT_ATTRIBUTION_SESSION_KEY,
                None,
            )

            session.modified = True


        else:

            try:

                captured_at = (
                    datetime.fromisoformat(
                        captured_at_raw
                    )
                )


                if captured_at.tzinfo is None:

                    captured_at = (
                        captured_at.replace(
                            tzinfo=timezone.utc
                        )
                    )


                attribution_age_seconds = (
                    datetime.now(
                        timezone.utc
                    )
                    -
                    captured_at
                ).total_seconds()


                if (
                    attribution_age_seconds < 0
                    or
                    attribution_age_seconds
                    >
                    KALXA_ATTRIBUTION_MAX_AGE_SECONDS
                ):

                    attribution = {}

                    session.pop(
                        RESTAURANT_ATTRIBUTION_SESSION_KEY,
                        None,
                    )

                    session.modified = True


            except (
                TypeError,
                ValueError,
            ):

                attribution = {}

                session.pop(
                    RESTAURANT_ATTRIBUTION_SESSION_KEY,
                    None,
                )

                session.modified = True


    # ========================================================
    # TRAFFIC SOURCE CLASSIFICATION
    # ========================================================
    #
    # At this stage Kalxa has two restaurant traffic classes:
    #
    #     kalxa_stories
    #     direct
    #
    # "direct" means that this analytics event does not have
    # a currently valid verified Stories attribution.
    #
    # Future sources can be introduced here, for example:
    #
    #     kalxa_qr
    #     kalxa_discovery
    #     kalxa_search
    #     kalxa_push
    #
    # without changing the RestaurantAnalyticsEvent schema.
    # ========================================================

    if (
        attribution.get(
            "source"
        )
        ==
        "kalxa_stories"
    ):

        source = (
            "kalxa_stories"
        )

    else:

        source = (
            "direct"
        )


    # ========================================================
    # ATTRIBUTION VALUES
    # ========================================================
    #
    # Direct traffic must not inherit Story attribution
    # identifiers.
    # ========================================================

    if (
        source
        ==
        "kalxa_stories"
    ):

        source_article_id = (
            attribution.get(
                "article_id"
            )
        )

        source_restaurant_id = (
            attribution.get(
                "restaurant_id"
            )
        )

        source_session_id = (
            attribution.get(
                "source_session_id"
            )
        )


    else:

        source_article_id = None

        source_restaurant_id = None

        source_session_id = None


    # ========================================================
    # OPTIONAL DEDUPLICATION
    # ========================================================

    if deduplicate:

        try:

            duplicate_exists = (
                recent_restaurant_analytics_event_exists(

                    restaurant_id=(
                        resolved_restaurant_id
                    ),

                    event_type=(
                        event_type
                    ),

                    session_id=(
                        anonymous_session_id
                    ),
                    
                    

                   source=(
                        source
                   ),                    

                    source_article_id=(
                        source_article_id
                    ),
                )
            )


            if duplicate_exists:

                return False


        except Exception:

            current_app.logger.exception(
                "Unable to check restaurant analytics "
                "deduplication."
            )


    # ========================================================
    # CREATE EVENT
    # ========================================================

    analytics_event = (
        RestaurantAnalyticsEvent(

            restaurant_id=(
                resolved_restaurant_id
            ),

            event_type=(
                event_type
            ),

            session_id=(
                anonymous_session_id
            ),

            source=(
                source
            ),

            source_article_id=(
                source_article_id
            ),

            source_restaurant_id=(
                source_restaurant_id
            ),

            source_session_id=(
                source_session_id
            ),

            event_metadata=(
                metadata
                or
                {}
            ),

            referrer=(
                request.referrer
            ),

            created_at=(
                datetime.now(
                    timezone.utc
                )
            ),
        )
    )


    # ========================================================
    # SAVE EVENT
    # ========================================================

    try:

        db.session.add(
            analytics_event
        )

        db.session.commit()

        return True


    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "Unable to record restaurant "
            "analytics event: %s",
            event_type,
        )

        return False
# ============================================================
# ORGANIZER HOME ENDPOINT
# ============================================================

def organizer_home_endpoint(
    organizer,
):

    if (
        organizer
        and organizer.account_type
        == "restaurant"
    ):

        return "admin_restaurants"


    return "admin_dashboard"
    
def require_restaurant_organizer():

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    organizer = (
        get_current_organizer()
    )


    if (
        not organizer
        or organizer.account_type
        != "restaurant"
    ):

        flash(
            (
                "This area is for "
                "restaurant advertisers."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    return None


def require_event_organizer():

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    organizer = (
        get_current_organizer()
    )


    if (
        not organizer
        or organizer.account_type
        != "event"
    ):

        return redirect(
            url_for(
                "admin_restaurants"
            )
        )


    return None
# ============================================================
# FEATURED LISTING HELPERS
# ============================================================

def featured_listing_plan(plan_code):

    plan = FEATURED_LISTING_PLANS.get(
        str(plan_code or "")
        .strip()
        .lower()
    )

    if not plan:
        raise ValueError(
            "Invalid featured listing plan."
        )

    return plan


def generate_featured_listing_reference():

    return (
        "KXFEATURED-"
        + secrets.token_hex(6).upper()
    )


def get_active_featured_listing(event_id):

    now = datetime.utcnow()

    return (
        FeaturedListing.query
        .filter(
            FeaturedListing.event_id
            == event_id,
            FeaturedListing.status
            == "active",
            FeaturedListing.starts_at
            <= now,
            FeaturedListing.ends_at
            > now,
        )
        .order_by(
            FeaturedListing.starts_at.desc()
        )
        .first()
    )


def validate_featured_image_upload(image_file):

    filename = secure_filename(
        image_file.filename or ""
    )

    if (
        not filename
        or "."
        not in filename
    ):
        raise ValueError(
            "Featured posters must be JPG, JPEG, PNG or WEBP images."
        )

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    mimetypes = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }

    if extension not in mimetypes:
        raise ValueError(
            "Featured posters must be JPG, JPEG, PNG or WEBP images."
        )

    data = image_file.read()

    if not data:
        raise ValueError(
            "One of the featured poster images is empty."
        )

    if len(data) > FEATURED_IMAGE_MAX_BYTES:
        raise ValueError(
            "Each featured poster must be 5 MB or smaller."
        )

    return {
        "data": data,
        "mimetype": mimetypes[extension],
        "filename": filename,
    }


def finalize_featured_listing_payment(
    listing,
    transaction_data,
):

    if listing.is_active_now:
        return listing

    if (
        not isinstance(
            transaction_data,
            dict,
        )
        or transaction_data.get("status")
        != "success"
    ):
        raise RuntimeError(
            "Paystack featured-listing transaction is not successful."
        )

    reference = str(
        transaction_data.get(
            "reference",
            "",
        )
    ).strip()

    if reference != listing.payment_reference:
        raise RuntimeError(
            "Paystack featured-listing reference does not match."
        )

    expected_amount = int(
        (
            Decimal(
                str(listing.price)
            )
            * 100
        )
        .quantize(
            Decimal("1"),
            rounding=ROUND_UP,
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
            "Paystack featured-listing amount does not match."
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
            "Paystack featured-listing currency does not match."
        )

    now = datetime.utcnow()

    listing.status = "active"
    listing.paid_at = now
    listing.payment_verified_at = now
    listing.starts_at = now
    listing.ends_at = (
        now
        + timedelta(
            days=listing.duration_days
        )
    )

    listing.paystack_transaction_id = (
        str(
            transaction_data.get(
                "id"
            )
            or ""
        )
        or None
    )

    listing.payment_channel = (
        transaction_data.get(
            "channel"
        )
        or None
    )

    db.session.commit()

    return listing


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

        campaign_type=
            "event",

        restaurant_advert_id=
            None,

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


# ============================================================
# EVENT ORGANIZER SUBSCRIPTION PRICE
# ============================================================

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


# ============================================================
# RESTAURANT SUBSCRIPTION PRICE
# ============================================================

try:

    KALXA_RESTAURANT_SUBSCRIPTION_PRICE = Decimal(
        os.environ.get(
            "KALXA_RESTAURANT_SUBSCRIPTION_PRICE",
            "219.00",
        )
    )


except InvalidOperation:

    raise RuntimeError(
        (
            "KALXA_RESTAURANT_SUBSCRIPTION_PRICE "
            "must be a valid number."
        )
    )


# ============================================================
# SUBSCRIPTION PERIOD
# ============================================================

KALXA_SUBSCRIPTION_PERIOD_DAYS = 30

# ============================================================
# KALXA EVENT PARTNER PROGRAM
# ============================================================

KALXA_PARTNER_PLAN_NAME = (
    "Kalxa Event Partner - 30 Day Access"
)

KALXA_PARTNER_ACCESS_DAYS = 30

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
# SALES PHASE HELPERS
# ============================================================

def parse_phase_datetime(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        local_value = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=ZoneInfo("Africa/Johannesburg"))
    except ValueError as error:
        raise ValueError("Enter a valid sales phase date and time.") from error
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)

def phase_datetime_input_value(value):
    if not value:
        return ""
    return value.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%dT%H:%M")

def validate_ticket_phase_sequence(ticket_type, rows):
    previous = None
    for row in rows:
        if row["end_at"] and row["start_at"] and row["end_at"] <= row["start_at"]:
            raise ValueError(f"{ticket_type.name}: phase end must be after phase start.")
        if previous and previous["end_at"] and row["start_at"] and row["start_at"] < previous["end_at"]:
            raise ValueError(f"{ticket_type.name}: sales phases cannot overlap.")
        previous = row

def serialize_phase_for_form(phase):
    return {
        "id": phase.id, "name": phase.name, "price": phase.price,
        "start_at": phase_datetime_input_value(phase.start_at),
        "end_at": phase_datetime_input_value(phase.end_at),
        "quantity_limit": phase.quantity_limit, "sold_quantity": phase.sold_quantity,
        "active": phase.active,
    }


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
# STAFF CHECK-IN SESSION
# ============================================================

STAFF_SESSION_KEY = (
    "kalxa_staff_account_id"
)


def normalize_staff_username(
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


def get_current_staff():

    staff_id = (
        session.get(
            STAFF_SESSION_KEY
        )
    )


    if not staff_id:

        return None


    try:

        staff_id = int(
            staff_id
        )


    except (
        TypeError,
        ValueError,
    ):

        session.pop(
            STAFF_SESSION_KEY,
            None,
        )

        return None


    staff = (
        db.session.get(
            StaffAccount,
            staff_id,
        )
    )


    if (
        not staff
        or not staff.active
        or not staff.organizer
        or not staff.organizer.is_subscription_active
    ):

        session.pop(
            STAFF_SESSION_KEY,
            None,
        )

        return None


    return staff


def require_staff_account():

    staff = (
        get_current_staff()
    )


    if staff:

        return None


    flash(
        (
            "Please sign in with your "
            "Kalxa gate staff account."
        ),
        "error",
    )


    return redirect(
        url_for(
            "staff_login"
        )
    )


def get_staff_event_ids(
    staff,
):

    if not staff:

        return []


    return [
        access.event_id
        for access in staff.event_access
        if (
            access.event
            and not access.event.organizer_deleted
        )
    ]


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
# EVENT PARTNER TEMPORARY PASSWORD
# ============================================================

def generate_partner_temporary_password():

    alphabet = (
        string.ascii_letters
        + string.digits
    )

    return "".join(
        secrets.choice(
            alphabet
        )
        for _ in range(12)
    )


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
# SUPER ADMIN - CREATE EVENT PARTNER ACCOUNT
# ============================================================

@app.route(
    "/superadmin/partners/new",
    methods=[
        "GET",
        "POST",
    ],
)
def superadmin_create_partner():

    auth = (
        require_superadmin()
    )

    if auth:
        return auth


    if request.method == "POST":

        # ====================================================
        # FORM
        # ====================================================

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
        )


        email = (
            normalize_email(
                request.form.get(
                    "email",
                    "",
                )
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


        # ====================================================
        # VALIDATION
        # ====================================================

        if not name:

            flash(
                "Organizer name is required.",
                "error",
            )

            return render_template(
                "superadmin/partner_form.html"
            )


        if not business_name:

            flash(
                (
                    "Event business or brand "
                    "name is required."
                ),
                "error",
            )

            return render_template(
                "superadmin/partner_form.html"
            )


        if not email:

            flash(
                "Email address is required.",
                "error",
            )

            return render_template(
                "superadmin/partner_form.html"
            )


        existing_organizer = (
            Organizer.query
            .filter_by(
                email=
                    email
            )
            .first()
        )


        if existing_organizer:

            flash(
                (
                    "An organizer account already "
                    "exists with this email."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "superadmin_organizer_detail",
                    organizer_id=
                        existing_organizer.id,
                )
            )


        # ====================================================
        # PARTNER ACCESS
        # ====================================================

        temporary_password = (
            generate_partner_temporary_password()
        )


        now = (
            datetime.utcnow()
        )


        subscription_end = (
            now
            + timedelta(
                days=
                    KALXA_PARTNER_ACCESS_DAYS
            )
        )


        # ====================================================
        # CREATE EVENT ORGANIZER
        # ====================================================

        organizer = Organizer(

            name=
                name,

            business_name=
                business_name,

            email=
                email,

            phone=
                phone,

            account_type=
                "event",

            active=
                True,

            subscription_status=
                "active",

            subscription_started_at=
                now,

            subscription_expires_at=
                subscription_end,
        )


        organizer.set_password(
            temporary_password
        )


        try:

            db.session.add(
                organizer
            )

            db.session.flush()


            # ================================================
            # PARTNER GRANT AUDIT RECORD
            # ================================================

            partner_payment = (
                SubscriptionPayment(

                    organizer_id=
                        organizer.id,

                    plan_name=
                        KALXA_PARTNER_PLAN_NAME,

                    amount=
                        Decimal(
                            "0.00"
                        ),

                    period_days=
                        KALXA_PARTNER_ACCESS_DAYS,

                    payment_reference=
                        generate_subscription_payment_reference(),

                    payment_method=
                        "partner_grant",

                    payment_status=
                        "paid",

                    paid_at=
                        now,

                    confirmed_at=
                        now,

                    confirmed_by=
                        "superadmin_partner_grant",

                    subscription_start=
                        now,

                    subscription_end=
                        subscription_end,
                )
            )


            db.session.add(
                partner_payment
            )

            db.session.commit()


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Event Partner] "
                    "Unable to create partner "
                    "email=%s error=%s"
                ),
                email,
                error,
            )


            flash(
                (
                    "Partner account could "
                    "not be created."
                ),
                "error",
            )


            return render_template(
                "superadmin/partner_form.html"
            )


        # ====================================================
        # SUCCESS
        # ====================================================

        current_app.logger.info(
            (
                "[Event Partner] "
                "Partner account created "
                "organizer_id=%s expires_at=%s"
            ),
            organizer.id,
            subscription_end,
        )


        return render_template(
            "superadmin/partner_created.html",

            organizer=
                organizer,

            temporary_password=
                temporary_password,

            subscription_end=
                subscription_end,
        )


    return render_template(
        "superadmin/partner_form.html"
    )


# ============================================================
# SUPER ADMIN - EXTEND EVENT PARTNER
# ============================================================

@app.route(
    "/superadmin/organizers/<int:organizer_id>/partner/extend",
    methods=[
        "POST",
    ],
)
def superadmin_extend_partner_access(
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
        getattr(
            organizer,
            "account_type",
            "event",
        )
        != "event"
    ):

        flash(
            (
                "Complimentary Event Partner "
                "access can only be granted "
                "to Event accounts."
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
        organizer.subscription_status
        == "suspended"
        or not organizer.active
    ):

        flash(
            (
                "Reactivate this organizer "
                "before extending partner access."
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
            days=
                KALXA_PARTNER_ACCESS_DAYS
        )
    )


    partner_payment = (
        SubscriptionPayment(

            organizer_id=
                organizer.id,

            plan_name=
                KALXA_PARTNER_PLAN_NAME,

            amount=
                Decimal(
                    "0.00"
                ),

            period_days=
                KALXA_PARTNER_ACCESS_DAYS,

            payment_reference=
                generate_subscription_payment_reference(),

            payment_method=
                "partner_grant",

            payment_status=
                "paid",

            paid_at=
                now,

            confirmed_at=
                now,

            confirmed_by=
                "superadmin_partner_extension",

            subscription_start=
                subscription_start,

            subscription_end=
                subscription_end,
        )
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

        db.session.add(
            partner_payment
        )

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Event Partner] "
                "Extension failed "
                "organizer_id=%s error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            (
                "Partner access could not "
                "be extended."
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


    flash(
        (
            "30 days of complimentary "
            "partner access added successfully."
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


    # ========================================================
    # ORGANIZERS
    # ========================================================

    total_organizers = (
        Organizer.query.count()
    )


    active_subscriptions = (
        Organizer.query

        .filter(
            Organizer.active.is_(
                True
            )
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


    # ========================================================
    # SUBSCRIPTION PAYMENTS
    # ========================================================

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
    # RESTAURANT EXPERIENCE POSTS WAITING FOR MODERATION
    # ========================================================

    pending_restaurant_experiences = (
        RestaurantExperiencePost.query

        .filter(
            RestaurantExperiencePost.moderation_status
            == "pending"
        )

        .order_by(
            RestaurantExperiencePost.created_at.asc()
        )

        .limit(20)

        .all()
    )


    pending_restaurant_experience_count = (
        RestaurantExperiencePost.query

        .filter(
            RestaurantExperiencePost.moderation_status
            == "pending"
        )

        .count()
    )


    # ========================================================
    # EVENTS READY FOR PUSH
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


    # ========================================================
    # RESTAURANT ADVERTS READY FOR PUSH
    # ========================================================

    promoted_restaurant_ids = (

        db.session.query(
            PushCampaign.restaurant_advert_id
        )

        .filter(
            PushCampaign.restaurant_advert_id.isnot(
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


    notification_ready_restaurants = (

        RestaurantAdvert.query

        .join(
            Organizer,
            RestaurantAdvert.organizer_id
            == Organizer.id,
        )

        .filter(
            RestaurantAdvert.active.is_(
                True
            )
        )

        .filter(
            Organizer.subscription_status
            == "active"
        )

        .filter(
            Organizer.subscription_expires_at
            > now
        )

        .filter(
            ~RestaurantAdvert.id.in_(
                db.select(
                    promoted_restaurant_ids
                    .c
                    .restaurant_advert_id
                )
            )
        )

        .order_by(
            RestaurantAdvert.created_at.desc()
        )

        .limit(20)

        .all()
    )


    notification_ready_restaurant_count = (
        len(
            notification_ready_restaurants
        )
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

        notification_ready_restaurants=
            notification_ready_restaurants,

        notification_ready_restaurant_count=
            notification_ready_restaurant_count,

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

        # NEW
        pending_restaurant_experiences=
            pending_restaurant_experiences,

        pending_restaurant_experience_count=
            pending_restaurant_experience_count,

        subscription_plan_name=
            KALXA_SUBSCRIPTION_PLAN_NAME,

        subscription_price=
            KALXA_SUBSCRIPTION_PRICE,
    )


# ============================================================
# SUPERADMIN - RESTAURANT EXPERIENCE MODERATION
# ============================================================

@app.route(
    "/superadmin/restaurant-experiences"
)
def superadmin_restaurant_experiences():

    auth = (
        require_superadmin()
    )


    if auth:
        return auth


    pending_posts = (
        RestaurantExperiencePost.query

        .filter(
            RestaurantExperiencePost.moderation_status
            == "pending"
        )

        .order_by(
            RestaurantExperiencePost.created_at.asc()
        )

        .all()
    )


    approved_posts = (
        RestaurantExperiencePost.query

        .filter(
            RestaurantExperiencePost.moderation_status
            == "approved"
        )

        .order_by(
            RestaurantExperiencePost.created_at.desc()
        )

        .limit(50)

        .all()
    )


    rejected_posts = (
        RestaurantExperiencePost.query

        .filter(
            RestaurantExperiencePost.moderation_status
            == "rejected"
        )

        .order_by(
            RestaurantExperiencePost.created_at.desc()
        )

        .limit(50)

        .all()
    )


    return render_template(
        "superadmin/restaurant_experiences.html",

        pending_posts=
            pending_posts,

        approved_posts=
            approved_posts,

        rejected_posts=
            rejected_posts,
    )


# ============================================================
# SUPERADMIN - APPROVE RESTAURANT EXPERIENCE
# ============================================================

@app.route(
    "/superadmin/restaurant-experiences/<int:post_id>/approve",
    methods=[
        "POST",
    ],
)
def superadmin_approve_restaurant_experience(
    post_id,
):

    auth = (
        require_superadmin()
    )


    if auth:
        return auth


    experience_post = (
        RestaurantExperiencePost.query
        .filter_by(
            id=
                post_id
        )
        .first_or_404()
    )


    experience_post.moderation_status = (
        "approved"
    )


    experience_post.active = True


    experience_post.moderated_at = (
        datetime.utcnow()
    )


    experience_post.moderated_by = (
        "superadmin"
    )


    experience_post.rejection_reason = (
        None
    )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Experience Moderation] "
                "Approve failed post_id=%s "
                "error=%s"
            ),
            experience_post.id,
            error,
        )


        flash(
            "Experience could not be approved.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_restaurant_experiences"
            )
        )


    flash(
        "Restaurant experience approved.",
        "success",
    )


    return redirect(
        url_for(
            "superadmin_restaurant_experiences"
        )
    )


# ============================================================
# SUPERADMIN - REJECT RESTAURANT EXPERIENCE
# ============================================================

@app.route(
    "/superadmin/restaurant-experiences/<int:post_id>/reject",
    methods=[
        "POST",
    ],
)
def superadmin_reject_restaurant_experience(
    post_id,
):

    auth = (
        require_superadmin()
    )


    if auth:
        return auth


    experience_post = (
        RestaurantExperiencePost.query
        .filter_by(
            id=
                post_id
        )
        .first_or_404()
    )


    rejection_reason = (
        request.form.get(
            "rejection_reason",
            "",
        )
        .strip()
        or None
    )


    experience_post.moderation_status = (
        "rejected"
    )


    experience_post.active = False


    experience_post.moderated_at = (
        datetime.utcnow()
    )


    experience_post.moderated_by = (
        "superadmin"
    )


    experience_post.rejection_reason = (
        rejection_reason
    )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Experience Moderation] "
                "Reject failed post_id=%s "
                "error=%s"
            ),
            experience_post.id,
            error,
        )


        flash(
            "Experience could not be rejected.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_restaurant_experiences"
            )
        )


    flash(
        "Restaurant experience rejected.",
        "success",
    )


    return redirect(
        url_for(
            "superadmin_restaurant_experiences"
        )
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

# ========================================================
# ACTIVE RESTAURANT ADVERTS
# ========================================================

    now = (
        datetime.utcnow()
    )


    restaurant_adverts = (
        RestaurantAdvert.query

        .join(
          Organizer,
          RestaurantAdvert.organizer_id
          == Organizer.id,
        )

        .filter(
          RestaurantAdvert.active.is_(
            True
          )
        )

        .filter(
          Organizer.active.is_(
            True
          )
        )

        .filter(
          Organizer.subscription_status
          == "active"
        )

        .filter(
          Organizer.subscription_expires_at
          > now
        )

        .filter(
          or_(
            RestaurantAdvert.starts_at.is_(
                None
            ),

            RestaurantAdvert.starts_at
            <= now,
          )
        )

        .filter(
          or_(
            RestaurantAdvert.ends_at.is_(
                None
            ),

            RestaurantAdvert.ends_at
            > now,
          )
        )

        .order_by(
          RestaurantAdvert.created_at.desc()
        )

        .limit(50)

        .all()
    )

    restaurant_audience_counts = {

      advert.id:
        len(
            get_restaurant_push_subscriptions(
                advert
            )
        )

      for advert in restaurant_adverts
    }

    selected_restaurant = None


    selected_restaurant_id = (
      request.args.get(
        "restaurant_id",
        type=int,
      )
    )


    if selected_restaurant_id:

      selected_restaurant = (
        RestaurantAdvert.query

        .join(
            Organizer,
            RestaurantAdvert.organizer_id
            == Organizer.id,
        )

        .filter(
            RestaurantAdvert.id
            == selected_restaurant_id
        )

        .filter(
            RestaurantAdvert.active.is_(
                True
            )
        )

        .filter(
            Organizer.subscription_status
            == "active"
        )

        .filter(
            Organizer.subscription_expires_at
            > datetime.utcnow()
        )

        .first()
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

    selected_restaurant_audience_count = (

      restaurant_audience_counts.get(
        selected_restaurant.id,
        0,
      )

      if selected_restaurant
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

        restaurant_adverts=
            restaurant_adverts,

        selected_restaurant=
            selected_restaurant,

        restaurant_audience_counts=
            restaurant_audience_counts,

        selected_restaurant_audience_count=
            selected_restaurant_audience_count,

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

        campaign_type=
            "event",

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
# ORGANIZER PASSWORD RESET HELPERS
# ============================================================

ORGANIZER_PASSWORD_RESET_SALT = (
    "kalxa-organizer-password-reset"
)


def get_password_reset_serializer():

    return URLSafeTimedSerializer(
        current_app.secret_key
    )



def create_organizer_password_reset_token(
    organizer,
):

    serializer = (
        get_password_reset_serializer()
    )


    return serializer.dumps(
        {
            "organizer_id":
                organizer.id,

            "email":
                organizer.email,
        },
        salt=
            ORGANIZER_PASSWORD_RESET_SALT,
    )



def verify_organizer_password_reset_token(
    token,
):

    serializer = (
        get_password_reset_serializer()
    )


    try:

        payload = (
            serializer.loads(
                token,

                salt=
                    ORGANIZER_PASSWORD_RESET_SALT,

                max_age=
                    PASSWORD_RESET_MAX_AGE_SECONDS,
            )
        )


    except SignatureExpired:

        return (
            None,
            "expired",
        )


    except BadSignature:

        return (
            None,
            "invalid",
        )


    if not isinstance(
        payload,
        dict,
    ):

        return (
            None,
            "invalid",
        )


    organizer_id = (
        payload.get(
            "organizer_id"
        )
    )


    email = (
        payload.get(
            "email"
        )
    )


    if (
        not organizer_id
        or not email
    ):

        return (
            None,
            "invalid",
        )


    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    if not organizer:

        return (
            None,
            "invalid",
        )


    if (
        normalize_email(
            organizer.email
        )
        !=
        normalize_email(
            email
        )
    ):

        return (
            None,
            "invalid",
        )


    return (
        organizer,
        None,
    )

# ============================================================
# SEND PASSWORD RESET EMAIL
# ============================================================

def send_organizer_password_reset_email(
    organizer,
    reset_url,
):

    if (
        not SMTP_HOST
        or not SMTP_FROM_EMAIL
    ):

        raise RuntimeError(
            (
                "Password reset email "
                "is not configured."
            )
        )


    message = EmailMessage()


    message[
        "Subject"
    ] = (
        "Reset your Kalxa password"
    )


    message[
        "From"
    ] = SMTP_FROM_EMAIL


    message[
        "To"
    ] = organizer.email


    message.set_content(
        (
            f"Hi {organizer.name},\n\n"

            "We received a request to reset "
            "your Kalxa password.\n\n"

            "Use the link below to choose "
            "a new password:\n\n"

            f"{reset_url}\n\n"

            "This link expires in 1 hour.\n\n"

            "If you did not request a password "
            "reset, you can ignore this email.\n\n"

            "Kalxa"
        )
    )


    if SMTP_PORT == 465:

        with smtplib.SMTP_SSL(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
        ) as server:

            if (
                SMTP_USERNAME
                and SMTP_PASSWORD
            ):

                server.login(
                    SMTP_USERNAME,
                    SMTP_PASSWORD,
                )


            server.send_message(
                message
            )


    else:

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20,
        ) as server:

            server.ehlo()

            server.starttls()

            server.ehlo()


            if (
                SMTP_USERNAME
                and SMTP_PASSWORD
            ):

                server.login(
                    SMTP_USERNAME,
                    SMTP_PASSWORD,
                )


            server.send_message(
                message
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
# SUPER ADMIN - SEND RESTAURANT PUSH
# ============================================================
@app.route(
    "/superadmin/notifications/restaurants/send",
    methods=[
        "POST",
    ],
)
def superadmin_send_restaurant_notification():

    # ========================================================
    # SUPERADMIN AUTHENTICATION
    # ========================================================

    auth = (
        require_superadmin()
    )


    if auth:
        return auth


    # ========================================================
    # FIREBASE REQUIRED
    # ========================================================

    if not firebase_admin_configured():

        flash(
            (
                "Server-side Firebase sending "
                "is not configured."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications"
            )
        )


    # ========================================================
    # FORM VALUES
    # ========================================================

    restaurant_id = (
        request.form.get(
            "restaurant_id",
            type=int,
        )
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


    # ========================================================
    # RESTAURANT ID REQUIRED
    # ========================================================

    if not restaurant_id:

        flash(
            "Choose a restaurant advert.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications"
            )
        )


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=restaurant_id,
        )

        .first()
    )


    if not advert:

        flash(
            "Restaurant advert was not found.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications"
            )
        )


    # ========================================================
    # OWNER
    # ========================================================

    organizer = (
        advert.organizer
    )


    # ========================================================
    # RESTAURANT OWNER REQUIRED
    # ========================================================
    #
    # IMPORTANT:
    #
    # We no longer check:
    #
    #     organizer.is_subscription_active
    #
    # Restaurant promotion is now controlled by the
    # RestaurantAdvert Free / Standard / Premium plan.
    #
    # The Organizer account must still exist and be active.
    # ========================================================

    if not organizer:

        flash(
            (
                "This restaurant does not have "
                "a valid owner account."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # OWNER ACCOUNT MUST BE ACTIVE
    # ========================================================

    if not organizer.active:

        flash(
            (
                "This restaurant owner account "
                "is currently inactive."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if (
        account_type
        != "restaurant"
    ):

        flash(
            (
                "This advert is not owned by "
                "a restaurant account."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # RESTAURANT ADVERT MUST BE ACTIVE
    # ========================================================

    if not advert.active:

        flash(
            (
                "This restaurant advert "
                "is currently paused."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # RESTAURANT PLAN MUST BE ACTIVE
    # ========================================================
    #
    # FREE
    # --------------------------------------------------------
    # Active without an expiry date.
    #
    # STANDARD / PREMIUM
    # --------------------------------------------------------
    # Must have active status and a future restaurant-plan
    # expiry date.
    #
    # This check belongs to RestaurantAdvert rather than the
    # old Organizer SaaS subscription.
    # ========================================================

    if not advert.is_restaurant_subscription_active:

        flash(
            (
                "This restaurant plan is "
                "currently inactive."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # RESTAURANT PROMOTION / REEL FEATURE
    # ========================================================
    #
    # Restaurant discovery/reel promotion is currently
    # available on:
    #
    #     FREE
    #     STANDARD
    #     PREMIUM
    #
    # We still use the feature property rather than hardcoding
    # plan names so this route automatically follows future
    # changes to the restaurant feature matrix.
    # ========================================================

    if not advert.can_use_reel:

        flash(
            (
                "This restaurant plan does not "
                "currently allow restaurant promotion."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # CAMPAIGN WINDOW
    # ========================================================

    now = (
        datetime.utcnow()
    )


    # ========================================================
    # CAMPAIGN HAS NOT STARTED
    # ========================================================

    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        flash(
            (
                "This restaurant campaign "
                "has not started yet."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # CAMPAIGN EXPIRED
    # ========================================================

    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        flash(
            (
                "This restaurant campaign "
                "has already expired."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # TITLE REQUIRED
    # ========================================================

    if not title:

        flash(
            "Notification title is required.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # BODY REQUIRED
    # ========================================================

    if not body:

        flash(
            "Notification message is required.",
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # TITLE LENGTH
    # ========================================================

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

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # BODY LENGTH
    # ========================================================

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

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # AREA REQUIRED
    # ========================================================

    if not advert.area:

        flash(
            (
                "This restaurant does not have "
                "an area configured."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # AUDIENCE
    # ========================================================

    subscriptions = (
        get_restaurant_push_subscriptions(
            advert
        )
    )


    if not subscriptions:

        flash(
            (
                "No active notification "
                f"subscribers were found in {advert.area}."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # CREATE PUSH CAMPAIGN
    # ========================================================

    campaign = PushCampaign(

        campaign_type="restaurant",

        event_id=None,

        restaurant_advert_id=advert.id,

        title=title,

        body=body,

        target_url=(
            url_for(
                "restaurant_page",

                advert_id=advert.id,

                _external=True,
            )
        ),

        target_mode="area",

        target_area=advert.area,

        target_latitude=None,

        target_longitude=None,

        radius_km=None,

        status="draft",

        recipient_count=(
            len(
                subscriptions
            )
        ),

        created_by="superadmin",
    )


    # ========================================================
    # SAVE CAMPAIGN
    # ========================================================

    try:

        db.session.add(
            campaign
        )

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Push] "
                "Campaign creation failed "
                "advert_id=%s "
                "error=%s"
            ),
            advert.id,
            error,
        )


        flash(
            (
                "Restaurant notification "
                "campaign could not be created."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # SEND PUSH CAMPAIGN
    # ========================================================

    try:

        send_push_campaign(
            campaign,
            subscriptions,
        )


    except Exception as error:

        db.session.rollback()


        # ====================================================
        # RELOAD CAMPAIGN
        # ====================================================

        campaign = (
            db.session.get(
                PushCampaign,
                campaign.id,
            )
        )


        # ====================================================
        # MARK CAMPAIGN AS FAILED
        # ====================================================

        if campaign:

            campaign.status = (
                "failed"
            )


            try:

                db.session.commit()


            except Exception:

                db.session.rollback()


                current_app.logger.exception(
                    (
                        "[Restaurant Push] "
                        "Unable to mark campaign "
                        "as failed "
                        "campaign_id=%s "
                        "advert_id=%s"
                    ),
                    campaign.id,
                    advert.id,
                )


        # ====================================================
        # LOG SEND FAILURE
        # ====================================================

        current_app.logger.exception(
            (
                "[Restaurant Push] "
                "Send failed "
                "campaign_id=%s "
                "advert_id=%s "
                "error=%s"
            ),
            (
                campaign.id
                if campaign
                else None
            ),
            advert.id,
            error,
        )


        flash(
            (
                "Firebase could not send the "
                "restaurant notification."
            ),
            "error",
        )


        return redirect(
            url_for(
                "superadmin_notifications",

                restaurant_id=advert.id,
            )
        )


    # ========================================================
    # SEND RESULT
    # ========================================================

    if campaign.failure_count:

        flash(
            (
                "Restaurant notification finished. "
                f"{campaign.success_count} sent, "
                f"{campaign.failure_count} failed."
            ),
            "success",
        )


    else:

        flash(
            (
                "Restaurant notification sent "
                f"successfully to "
                f"{campaign.success_count} "
                "subscriber(s)."
            ),
            "success",
        )


    # ========================================================
    # SUCCESS REDIRECT
    # ========================================================

    return redirect(
        url_for(
            "superadmin_notifications",

            restaurant_id=advert.id,
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

    # ========================================================
    # CURRENT DATE / TIME
    # ========================================================

    today = (
        date.today()
    )


    now = (
        datetime.utcnow()
    )


    # ========================================================
    # EVENTS
    # ========================================================

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


    # ========================================================
    # FEATURED EVENTS
    # ========================================================

    active_featured_listings = (
        FeaturedListing.query

        .join(
            TicketEvent,

            FeaturedListing.event_id
            ==
            TicketEvent.id,
        )

        .filter(
            FeaturedListing.status
            == "active",

            FeaturedListing.starts_at
            <= now,

            FeaturedListing.ends_at
            > now,

            TicketEvent.active.is_(True),

            TicketEvent.status
            == "published",

            TicketEvent.organizer_deleted.is_(False),

            TicketEvent.event_date
            >= today,
        )

        .order_by(
            FeaturedListing.starts_at.desc()
        )

        .all()
    )


    featured_by_event = {}


    for listing in active_featured_listings:

        if (
            listing.event_id
            not in featured_by_event
        ):

            featured_by_event[
                listing.event_id
            ] = listing


    featured_events = [

        {
            "event":
                listing.event,

            "listing":
                listing,

            "images":
                list(
                    listing.event.featured_images
                )[
                    :FEATURED_IMAGE_MAX_COUNT
                ],
        }

        for listing
        in featured_by_event.values()
    ]


    featured_event_ids = {

        item["event"].id

        for item
        in featured_events
    }


    normal_events = [

        event

        for event
        in events

        if (
            event.id
            not in featured_event_ids
        )
    ]


    # ========================================================
    # EVENT REELS
    # ========================================================
    #
    # SEE THE VIBE
    # ========================================================

    reels = (
        EventReel.query

        .join(
            TicketEvent,

            EventReel.event_id
            ==
            TicketEvent.id,
        )

        .filter(
            EventReel.active.is_(True),

            TicketEvent.active.is_(True),

            TicketEvent.status
            == "published",

            TicketEvent.organizer_deleted.is_(False),

            TicketEvent.event_date
            >= today,
        )

        .order_by(
            EventReel.created_at.desc()
        )

        .limit(12)

        .all()
    )


    # ========================================================
    # RESTAURANT REELS
    # ========================================================
    #
    # EAT AROUND YOU
    #
    # IMPORTANT:
    #
    # Restaurant Reels are available on:
    #
    #     FREE        YES
    #     STANDARD    YES
    #     PREMIUM     YES
    #
    # Therefore this query must NOT use:
    #
    #     Organizer.subscription_status
    #
    # or:
    #
    #     Organizer.subscription_expires_at
    #
    # Those belong to the legacy Organizer/Event SaaS
    # subscription.
    #
    # Restaurant Reel access belongs to RestaurantAdvert.
    # ========================================================

    restaurant_reels = (
        RestaurantReel.query

        .join(
            RestaurantAdvert,

            RestaurantReel.advert_id
            ==
            RestaurantAdvert.id,
        )

        .join(
            Organizer,

            RestaurantAdvert.organizer_id
            ==
            Organizer.id,
        )

        .filter(
            # =================================================
            # REEL ACTIVE
            # =================================================

            RestaurantReel.active.is_(
                True
            ),

            # =================================================
            # RESTAURANT ACTIVE
            # =================================================

            RestaurantAdvert.active.is_(
                True
            ),

            # =================================================
            # RESTAURANT SUBSCRIPTION STATUS
            # =================================================
            #
            # Free restaurants are active indefinitely.
            #
            # Paid restaurants remain active during their
            # grace period.
            # =================================================

            RestaurantAdvert.subscription_status
            == "active",

            # =================================================
            # ORGANIZER ACTIVE
            # =================================================

            Organizer.active.is_(
                True
            ),

            # =================================================
            # RESTAURANT ACCOUNT
            # =================================================

            Organizer.account_type
            == "restaurant",

            # =================================================
            # CAMPAIGN START
            # =================================================

            or_(
                RestaurantAdvert.starts_at.is_(
                    None
                ),

                RestaurantAdvert.starts_at
                <= now,
            ),

            # =================================================
            # CAMPAIGN END
            # =================================================

            or_(
                RestaurantAdvert.ends_at.is_(
                    None
                ),

                RestaurantAdvert.ends_at
                > now,
            ),
        )

        .order_by(
            RestaurantReel.created_at.desc()
        )

        .limit(12)

        .all()
    )


    # ========================================================
    # FINAL RESTAURANT REEL CAPABILITY CHECK
    # ========================================================
    #
    # Keep the public feed aligned with the centralized
    # RestaurantAdvert capability system.
    #
    # Free, Standard and Premium currently all have:
    #
    #     can_use_reel == True
    #
    # If plan rules change later, this filter will follow
    # those rules.
    # ========================================================

    visible_restaurant_reels = []


    for restaurant_reel in restaurant_reels:

        advert = (
            restaurant_reel.advert
        )


        if not advert:

            continue


        # ====================================================
        # SYNCHRONIZE PAID PLAN LIFECYCLE
        # ====================================================
        #
        # If Standard/Premium grace has expired, this can
        # downgrade the restaurant to Free.
        #
        # That does NOT remove the Reel because Free is
        # allowed to use Reel/Discovery.
        # ====================================================

        sync_restaurant_subscription(
            advert
        )


        if not advert.can_use_reel:

            continue


        visible_restaurant_reels.append(
            restaurant_reel
        )


    restaurant_reels = (
        visible_restaurant_reels
    )


    # ========================================================
    # CUSTOMER RESTAURANT EXPERIENCES
    # ========================================================
    #
    # Customer experiences are a paid restaurant capability.
    #
    # FREE
    #     -> hidden
    #
    # STANDARD
    #     -> visible
    #
    # PREMIUM
    #     -> visible
    #
    # PAID GRACE
    #     -> visible
    #
    # AFTER GRACE
    #     -> restaurant becomes Free
    #     -> existing posts remain stored
    #     -> existing posts are NOT publicly exposed
    #
    # IMPORTANT:
    #
    # We do not delete experience posts when a restaurant
    # downgrades.
    #
    # Re-upgrading can expose the approved posts again.
    # ========================================================

    restaurant_experience_candidates = (
        RestaurantExperiencePost.query

        .join(
            RestaurantAdvert,

            RestaurantExperiencePost.restaurant_advert_id
            ==
            RestaurantAdvert.id,
        )

        .join(
            Organizer,

            RestaurantAdvert.organizer_id
            ==
            Organizer.id,
        )

        .filter(
            # =================================================
            # EXPERIENCE ACTIVE
            # =================================================

            RestaurantExperiencePost.active.is_(
                True
            ),

            # =================================================
            # APPROVED ONLY
            # =================================================

            RestaurantExperiencePost.moderation_status
            == "approved",

            # =================================================
            # RESTAURANT ACTIVE
            # =================================================

            RestaurantAdvert.active.is_(
                True
            ),

            # =================================================
            # RESTAURANT SUBSCRIPTION STATUS
            # =================================================

            RestaurantAdvert.subscription_status
            == "active",

            # =================================================
            # STANDARD / PREMIUM ONLY
            # =================================================

            RestaurantAdvert.subscription_tier.in_(
                [
                    RESTAURANT_PLAN_STANDARD,
                    RESTAURANT_PLAN_PREMIUM,
                ]
            ),

            # =================================================
            # PAID EXPIRY REQUIRED
            # =================================================

            RestaurantAdvert.subscription_expires_at
            .isnot(
                None
            ),

            # =================================================
            # ORGANIZER ACTIVE
            # =================================================

            Organizer.active.is_(
                True
            ),

            # =================================================
            # RESTAURANT ORGANIZER
            # =================================================

            Organizer.account_type
            == "restaurant",

            # =================================================
            # CAMPAIGN START
            # =================================================

            or_(
                RestaurantAdvert.starts_at.is_(
                    None
                ),

                RestaurantAdvert.starts_at
                <= now,
            ),

            # =================================================
            # CAMPAIGN END
            # =================================================

            or_(
                RestaurantAdvert.ends_at.is_(
                    None
                ),

                RestaurantAdvert.ends_at
                > now,
            ),
        )

        .order_by(
            RestaurantExperiencePost.created_at.desc()
        )

        # ====================================================
        # FETCH EXTRA CANDIDATES
        # ====================================================
        #
        # Some candidates may be removed below because their
        # paid grace period has expired.
        #
        # Fetching more than 20 gives us room to still return
        # up to 20 eligible posts.
        # ====================================================

        .limit(60)

        .all()
    )


    # ========================================================
    # FINAL EXPERIENCE CAPABILITY CHECK
    # ========================================================

    restaurant_experiences = []


    for post in restaurant_experience_candidates:

        advert = (
            post.restaurant_advert
        )


        if not advert:

            continue


        # ====================================================
        # SYNCHRONIZE SUBSCRIPTION
        # ====================================================

        sync_restaurant_subscription(
            advert
        )


        # ====================================================
        # CUSTOMER EXPERIENCE CAPABILITY
        # ====================================================

        if not advert.can_receive_customer_experiences:

            continue


        # ====================================================
        # ADD TO PUBLIC FEED
        # ====================================================

        restaurant_experiences.append(
            post
        )


        # ====================================================
        # HOME FEED LIMIT
        # ====================================================

        if (
            len(
                restaurant_experiences
            )
            >= 20
        ):

            break


    # ========================================================
    # CURRENT ANONYMOUS LOVE STATE
    # ========================================================

    anonymous_session_id = (
        get_restaurant_experience_session_id()
    )


    loved_experience_post_ids = set()


    if restaurant_experiences:

        post_ids = [

            post.id

            for post
            in restaurant_experiences
        ]


        loved_experience_post_ids = {

            love.post_id

            for love
            in (
                RestaurantExperienceLove.query

                .filter(
                    RestaurantExperienceLove.post_id.in_(
                        post_ids
                    )
                )

                .filter(
                    RestaurantExperienceLove.anonymous_session_id
                    ==
                    anonymous_session_id
                )

                .all()
            )
        }


    # ========================================================
    # RENDER HOME
    # ========================================================

    return render_template(
        "event.html",

        featured_events=(
            featured_events
        ),

        events=(
            normal_events
        ),

        event=None,

        reels=(
            reels
        ),

        restaurant_reels=(
            restaurant_reels
        ),

        restaurant_experiences=(
            restaurant_experiences
        ),

        loved_experience_post_ids=(
            loved_experience_post_ids
        ),

        firebase_config=(
            FIREBASE_WEB_CONFIG
        ),

        firebase_vapid_key=(
            FIREBASE_VAPID_KEY
        ),

        firebase_push_configured=(
            firebase_web_push_configured()
        ),
    )
# ============================================================
# RESTAURANT GALLERY
# ============================================================


RESTAURANT_GALLERY_MAX_IMAGES = 5

RESTAURANT_GALLERY_MAX_FILE_BYTES = 8 * 1024 * 1024


def get_restaurant_gallery_files():
    files = request.files.getlist("gallery_images")

    return [
        file
        for file in files
        if file and file.filename
    ]


def validate_restaurant_gallery_files(
    files,
    existing_count=0,
):
    total_after_upload = existing_count + len(files)

    if total_after_upload > RESTAURANT_GALLERY_MAX_IMAGES:
        remaining = max(
            RESTAURANT_GALLERY_MAX_IMAGES - existing_count,
            0,
        )

        return (
            False,
            (
                "A restaurant can have a maximum "
                "of 5 gallery photos. "
                f"You can upload {remaining} more."
            ),
        )

    for image in files:
        if not allowed_restaurant_poster_filename(
            image.filename
        ):
            return (
                False,
                (
                    "Gallery photos must be JPG, "
                    "JPEG, PNG or WebP."
                ),
            )

        image.stream.seek(0, os.SEEK_END)
        file_size = image.stream.tell()
        image.stream.seek(0)

        if file_size > RESTAURANT_GALLERY_MAX_FILE_BYTES:
            return (
                False,
                (
                    f"{image.filename} is too large. "
                    "Maximum size is 8 MB per photo."
                ),
            )

    return True, None


def upload_restaurant_gallery_image(
    image,
    organizer_id,
    advert_id,
):
    image.stream.seek(0, os.SEEK_END)
    file_bytes = image.stream.tell()
    image.stream.seek(0)

    result = cloudinary.uploader.upload(
        image,
        resource_type="image",
        folder=(
            "kalxa/"
            f"organizers/{organizer_id}/"
            f"restaurants/{advert_id}/"
            "gallery"
        ),
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )

    public_id = result.get("public_id")
    secure_url = result.get("secure_url")

    if not public_id or not secure_url:
        raise RuntimeError(
            "Cloudinary did not return "
            "the restaurant gallery image."
        )

    return {
        "public_id": public_id,
        "secure_url": secure_url,
        "width": result.get("width"),
        "height": result.get("height"),
        "file_bytes": file_bytes,
    }

# ============================================================
# PUBLIC EVENT POSTER
# ============================================================

@app.route(
    "/api/public/stories/conversions"
)
def stories_conversion_analytics():

    article_ids_raw = (
        request.args
        .get(
            "article_ids",
            "",
        )
        .strip()
    )

    article_ids = []

    for value in (
        article_ids_raw.split(",")
    ):

        value = (
            value.strip()
        )

        if not value:

            continue

        try:

            article_id = int(
                value
            )

        except ValueError:

            continue

        if (
            article_id > 0
            and
            article_id not in article_ids
        ):

            article_ids.append(
                article_id
            )


    if not article_ids:

        return jsonify({
            "articles": []
        })


    rows = (
        db.session.query(
            RestaurantAnalyticsEvent
            .source_article_id,

            RestaurantAnalyticsEvent
            .event_type,

            func.count(
                RestaurantAnalyticsEvent.id
            ).label(
                "total"
            ),
        )
        .filter(
            RestaurantAnalyticsEvent.source
            == "stories",

            RestaurantAnalyticsEvent
            .source_article_id
            .in_(
                article_ids
            ),
        )
        .group_by(
            RestaurantAnalyticsEvent
            .source_article_id,

            RestaurantAnalyticsEvent
            .event_type,
        )
        .all()
    )


    article_lookup = {
        article_id: {
            "article_id":
                article_id,

            "restaurant_views":
                0,

            "experience_views":
                0,

            "whatsapp_clicks":
                0,

            "phone_clicks":
                0,

            "directions_clicks":
                0,
        }

        for article_id
        in article_ids
    }


    field_lookup = {

        "restaurant_view":
            "restaurant_views",

        "experience_view":
            "experience_views",

        "whatsapp_click":
            "whatsapp_clicks",

        "phone_click":
            "phone_clicks",

        "directions_click":
            "directions_clicks",
    }


    for row in rows:

        article_id = (
            row.source_article_id
        )

        field = (
            field_lookup.get(
                row.event_type
            )
        )

        if (
            article_id in article_lookup
            and
            field
        ):

            article_lookup[
                article_id
            ][
                field
            ] = int(
                row.total or 0
            )


    return jsonify({
        "articles": [
            article_lookup[
                article_id
            ]

            for article_id
            in article_ids
        ]
    })


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
# PUBLIC FEATURED LISTING IMAGE
# ============================================================

@app.route(
    "/featured/events/<int:event_id>/images/<int:image_id>"
)
def featured_listing_image(
    event_id,
    image_id,
):

    image = (
        FeaturedListingImage.query
        .filter_by(
            id=image_id,
            event_id=event_id,
        )
        .first_or_404()
    )

    response = Response(
        image.image_data,
        mimetype=image.image_mimetype,
    )

    response.headers[
        "Cache-Control"
    ] = "public, max-age=3600"

    return response



@app.route(
    "/r/<string:public_code>"
)
def restaurant_rating_qr_page(
    public_code,
):

    # ========================================================
    # FIND ACTIVE RATING QR
    # ========================================================
    #
    # The QR record may continue to exist even if the
    # restaurant later downgrades to Free.
    #
    # We deliberately do NOT delete old QR records when a
    # restaurant subscription changes.
    #
    # Access is controlled below using the current restaurant
    # subscription capability.
    # ========================================================

    restaurant_qr = (
        RestaurantRatingQRCode.query

        .filter_by(
            public_code=public_code,
            active=True,
        )

        .first_or_404()
    )


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        restaurant_qr.restaurant_advert
    )


    if not advert:

        abort(404)


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # STANDARD / PREMIUM ACTIVE
    #     -> customer experiences available
    #
    # STANDARD / PREMIUM EXPIRED <= 5 DAYS
    #     -> grace period
    #     -> customer experiences remain available
    #
    # STANDARD / PREMIUM EXPIRED > 5 DAYS
    #     -> automatically downgraded to Free
    #
    # FREE
    #     -> Rating QR cannot be used to submit experiences
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================

    if not advert.active:

        abort(404)


    # ========================================================
    # ORGANIZER / ACCOUNT SAFETY
    # ========================================================
    #
    # IMPORTANT:
    #
    # Do NOT use:
    #
    #     organizer.is_subscription_active
    #
    # That belongs to the legacy Organizer/Event SaaS
    # subscription.
    #
    # Restaurant Rating QR access is controlled by the
    # RestaurantAdvert subscription.
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        abort(404)


    if not organizer.active:

        abort(404)


    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(404)


    # ========================================================
    # CUSTOMER EXPERIENCE CAPABILITY
    # ========================================================
    #
    # FREE
    # --------------------------------------------------------
    #
    # Public profile               YES
    # Campaign                     YES
    # Reel / Discovery             YES
    #
    # Customer experiences         NO
    # Rating QR                    NO
    #
    #
    # STANDARD
    # --------------------------------------------------------
    #
    # Active                       YES
    # 5-day grace                  YES
    #
    #
    # PREMIUM
    # --------------------------------------------------------
    #
    # Active                       YES
    # 5-day grace                  YES
    #
    #
    # AFTER GRACE
    # --------------------------------------------------------
    #
    # sync_restaurant_subscription() converts the restaurant
    # to Free.
    #
    # This capability then becomes False.
    # ========================================================

    if not advert.can_receive_customer_experiences:

        abort(404)


    # ========================================================
    # CAMPAIGN DATE SAFETY
    # ========================================================
    #
    # Customer experience QR access is available only while
    # the restaurant campaign/profile is currently available.
    #
    # Operational hours are NOT checked here.
    # ========================================================

    now = (
        datetime.utcnow()
    )


    # ========================================================
    # CAMPAIGN NOT STARTED
    # ========================================================

    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        abort(404)


    # ========================================================
    # CAMPAIGN ENDED
    # ========================================================

    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        abort(404)


    # ========================================================
    # FINAL EXPERIENCE ELIGIBILITY CHECK
    # ========================================================
    #
    # Keep the QR route aligned with the same centralized
    # eligibility helper used by:
    #
    #     /experiences/new
    #
    # and:
    #
    #     get_taggable_restaurants()
    #
    # This gives us one consistent rule across the platform.
    # ========================================================

    if not restaurant_can_receive_experience_posts(
        advert
    ):

        abort(404)


    # ========================================================
    # SEND CUSTOMER TO EXPERIENCE FORM
    # ========================================================
    #
    # The restaurant ID is passed to:
    #
    #     /experiences/new?restaurant_id=<id>
    #
    # create_restaurant_experience() performs another
    # server-side eligibility check before displaying the
    # preselected restaurant.
    #
    # It then checks the restaurant again during POST.
    #
    # Therefore the security chain is:
    #
    #     QR scan
    #         ↓
    #     Rating QR eligibility
    #         ↓
    #     Experience GET eligibility
    #         ↓
    #     Experience POST eligibility
    #         ↓
    #     Final eligibility before DB/Cloudinary write
    # ========================================================

    return redirect(
        url_for(
            "create_restaurant_experience",

            restaurant_id=(
                advert.id
            ),
        )
    )
# ============================================================
# ADMIN - RESTAURANTS
# ============================================================

@app.route(
    "/admin/restaurants"
)
def admin_restaurants():

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    organizer = (
        get_current_organizer()
    )


    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    # ========================================================
    # RESTAURANT ACCOUNTS ONLY
    # ========================================================

    if (
        account_type
        != "restaurant"
    ):

        flash(
            (
                "Restaurant advertising is only "
                "available to restaurant accounts."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # ADVERTS
    # ========================================================

    adverts = (
        RestaurantAdvert.query

        .filter_by(
            organizer_id=
                organizer.id
        )

        .order_by(
            RestaurantAdvert.created_at.desc()
        )

        .all()
    )


    advert_ids = [
        advert.id
        for advert
        in adverts
    ]


    # ========================================================
    # DASHBOARD METRICS
    # ========================================================

    live_adverts = sum(
        1
        for advert in adverts
        if advert.campaign_status
        == "live"
    )


    scheduled_adverts = sum(
        1
        for advert in adverts
        if advert.campaign_status
        == "scheduled"
    )


    expired_adverts = sum(
        1
        for advert in adverts
        if advert.campaign_status
        == "expired"
    )


    paused_adverts = sum(
        1
        for advert in adverts
        if advert.campaign_status
        == "paused"
    )


    live_reels = sum(
        1
        for advert in adverts
        if (
            advert.reel
            and advert.reel.active
            and advert.campaign_status
            == "live"
        )
    )


    # ========================================================
    # CUSTOMER EXPERIENCE METRICS
    # ========================================================

    approved_experience_count = 0
    pending_experience_count = 0
    total_experience_loves = 0


    if advert_ids:

        approved_experience_count = (
            RestaurantExperiencePost.query

            .filter(
                RestaurantExperiencePost.restaurant_advert_id.in_(
                    advert_ids
                )
            )

            .filter(
                RestaurantExperiencePost.active.is_(
                    True
                )
            )

            .filter(
                RestaurantExperiencePost.moderation_status
                == "approved"
            )

            .count()
        )


        pending_experience_count = (
            RestaurantExperiencePost.query

            .filter(
                RestaurantExperiencePost.restaurant_advert_id.in_(
                    advert_ids
                )
            )

            .filter(
                RestaurantExperiencePost.moderation_status
                == "pending"
            )

            .count()
        )


        restaurant_post_ids = [

            post_id

            for (
                post_id,
            )
            in (
                db.session.query(
                    RestaurantExperiencePost.id
                )

                .filter(
                    RestaurantExperiencePost.restaurant_advert_id.in_(
                        advert_ids
                    )
                )

                .filter(
                    RestaurantExperiencePost.moderation_status
                    == "approved"
                )

                .all()
            )
        ]


        if restaurant_post_ids:

            total_experience_loves = (
                RestaurantExperienceLove.query

                .filter(
                    RestaurantExperienceLove.post_id.in_(
                        restaurant_post_ids
                    )
                )

                .count()
            )


    # ========================================================
    # RESTAURANT CUSTOMER RATING QR DATA
    # ========================================================
    #
    # IMPORTANT:
    #
    # This dashboard only READS existing QR records.
    #
    # It does not create QR records just because the owner
    # opened the Restaurant Control Centre.
    #
    # A QR is created only when the owner explicitly clicks
    # "Generate Customer Rating QR".
    # ========================================================

    restaurant_qr_data = {}


    if advert_ids:

        existing_rating_qrs = (
            RestaurantRatingQRCode.query

            .filter(
                RestaurantRatingQRCode.restaurant_advert_id.in_(
                    advert_ids
                )
            )

            .filter(
                RestaurantRatingQRCode.placement_type
                == "main"
            )

            .order_by(
                RestaurantRatingQRCode.created_at.asc()
            )

            .all()
        )


        # ====================================================
        # ONE MAIN QR PER RESTAURANT
        # ====================================================

        rating_qr_by_restaurant = {}


        for restaurant_qr in existing_rating_qrs:

            if (
                restaurant_qr.restaurant_advert_id
                not in rating_qr_by_restaurant
            ):

                rating_qr_by_restaurant[
                    restaurant_qr.restaurant_advert_id
                ] = restaurant_qr


        # ====================================================
        # BUILD TEMPLATE PAYLOAD
        # ====================================================

        for advert in adverts:

            restaurant_qr = (
                rating_qr_by_restaurant.get(
                    advert.id
                )
            )


            if restaurant_qr:

                rating_url = (
                    url_for(
                        "restaurant_rating_qr_page",

                        public_code=
                            restaurant_qr.public_code,

                        _external=True,

                        _scheme="https",
                    )
                )


                restaurant_qr_data[
                    advert.id
                ] = {

                    "exists":
                        True,

                    "public_code":
                        restaurant_qr.public_code,

                    "active":
                        restaurant_qr.active,

                    "rating_url":
                        rating_url,

                    "image_url":
                        url_for(
                            "restaurant_rating_qr_image",
                            advert_id=
                                advert.id,
                        ),

                    "download_url":
                        url_for(
                            "download_restaurant_rating_qr",
                            advert_id=
                                advert.id,
                        ),

                    "create_url":
                        url_for(
                            "create_restaurant_rating_qr",
                            advert_id=
                                advert.id,
                        ),
                }


            else:

                restaurant_qr_data[
                    advert.id
                ] = {

                    "exists":
                        False,

                    "public_code":
                        "",

                    "active":
                        False,

                    "rating_url":
                        "",

                    "image_url":
                        "",

                    "download_url":
                        "",

                    "create_url":
                        url_for(
                            "create_restaurant_rating_qr",
                            advert_id=
                                advert.id,
                        ),
                }


    # ========================================================
    # PENDING SUBSCRIPTION
    # ========================================================

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


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "admin/restaurants.html",

        organizer=
            organizer,

        adverts=
            adverts,

        live_adverts=
            live_adverts,

        scheduled_adverts=
            scheduled_adverts,

        expired_adverts=
            expired_adverts,

        paused_adverts=
            paused_adverts,

        live_reels=
            live_reels,

        # ====================================================
        # CUSTOMER EXPERIENCES
        # ====================================================

        approved_experience_count=
            approved_experience_count,

        pending_experience_count=
            pending_experience_count,

        total_experience_loves=
            total_experience_loves,

        # ====================================================
        # CUSTOMER RATING QR
        # ====================================================

        restaurant_qr_data=
            restaurant_qr_data,

        # ====================================================
        # SUBSCRIPTION
        # ====================================================

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
           KALXA_RESTAURANT_SUBSCRIPTION_PRICE,
                      
    )


@app.route(
    "/admin/restaurants/new",
    methods=["GET", "POST"],
)
def admin_create_restaurant():

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    auth = require_ticketing_organizer()

    if auth:
        return auth


    # ========================================================
    # RESTAURANT ACCOUNT ACCESS
    # ========================================================
    #
    # IMPORTANT:
    #
    # This must NOT use the legacy Organizer subscription.
    #
    # Restaurant subscription access belongs to:
    #
    #     RestaurantAdvert
    #
    # New restaurants always begin on the Free plan.
    # ========================================================

    subscription_auth = (
        require_restaurant_subscription()
    )

    if subscription_auth:
        return subscription_auth


    organizer = (
        get_current_organizer()
    )


    if not organizer:

        flash(
            "Organizer account could not be found.",
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # ORGANIZER ACTIVE
    # ========================================================

    if not organizer.active:

        flash(
            "Your organizer account is inactive.",
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # FORM DATE HELPERS
    # ========================================================

    today_iso = (
        datetime.utcnow()
        .date()
        .isoformat()
    )


    # ========================================================
    # LEGACY ORGANIZER SUBSCRIPTION DATE
    # ========================================================
    #
    # Keep this only if restaurant_form.html still expects
    # subscription_end_iso.
    #
    # It does NOT control restaurant access.
    # ========================================================

    subscription_end_iso = (
        organizer.subscription_expires_at
        .date()
        .isoformat()

        if organizer.subscription_expires_at

        else ""
    )


    # ========================================================
    # FORM RENDER HELPER
    # ========================================================
    #
    # No RestaurantAdvert exists during GET.
    #
    # Therefore capabilities are supplied using the Free
    # restaurant plan.
    # ========================================================

    def render_form():

        return render_template(
            "admin/restaurant_form.html",

            organizer=organizer,

            advert=None,

            today_iso=today_iso,

            subscription_end_iso=(
                subscription_end_iso
            ),

            # =================================================
            # RESTAURANT PLAN
            # =================================================

            restaurant_plan=(
                RESTAURANT_PLAN_FREE
            ),

            restaurant_plan_name=(
                RESTAURANT_PLAN_NAMES[
                    RESTAURANT_PLAN_FREE
                ]
            ),

            restaurant_plan_price=(
                RESTAURANT_PLAN_PRICES[
                    RESTAURANT_PLAN_FREE
                ]
            ),

            # =================================================
            # FREE PLAN CAPABILITIES
            # =================================================

            can_use_reel=True,

            can_use_gallery=False,

            can_use_opening_hours=False,

            can_receive_customer_experiences=False,

            can_use_stories=False,

            can_view_analytics=False,
        )


    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        return render_form()


    # ========================================================
    # POST
    # ========================================================

    # ========================================================
    # BASIC FORM VALUES
    # ========================================================

    business_name = (
        request.form.get(
            "business_name",
            "",
        )
        .strip()
    )


    headline = (
        request.form.get(
            "headline",
            "",
        )
        .strip()
        or None
    )


    description = (
        request.form.get(
            "description",
            "",
        )
        .strip()
        or None
    )


    area = (
        request.form.get(
            "area",
            "",
        )
        .strip()
        or None
    )


    address = (
        request.form.get(
            "address",
            "",
        )
        .strip()
        or None
    )


    whatsapp_number = (
        request.form.get(
            "whatsapp_number",
            "",
        )
        .strip()
        or None
    )


    phone_number = (
        request.form.get(
            "phone_number",
            "",
        )
        .strip()
        or None
    )


    directions_url = (
        valid_restaurant_directions_url(
            request.form.get(
                "directions_url",
                "",
            )
        )
    )


    # ========================================================
    # BUSINESS NAME
    # ========================================================

    if not business_name:

        flash(
            "Business name is required.",
            "error",
        )

        return render_form()


    # ========================================================
    # CAMPAIGN SCHEDULE
    # ========================================================
    #
    # Campaign access is available on Free, Standard and
    # Premium.
    #
    # Do NOT gate this behind a paid restaurant plan.
    # ========================================================

    (
        starts_at,
        ends_at,
        schedule_error,
    ) = build_restaurant_campaign_schedule(
        request.form,
        organizer,
    )


    if schedule_error:

        flash(
            schedule_error,
            "error",
        )

        return render_form()


    # ========================================================
    # MAIN POSTER
    # ========================================================
    #
    # FREE       -> YES
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    poster = (
        request.files.get(
            "poster"
        )
    )


    if (
        not poster
        or
        not poster.filename
    ):

        flash(
            "Upload a restaurant poster.",
            "error",
        )

        return render_form()


    # ========================================================
    # POSTER FILE TYPE
    # ========================================================

    if not allowed_restaurant_poster_filename(
        poster.filename
    ):

        flash(
            (
                "Use a JPG, JPEG, PNG "
                "or WebP poster."
            ),
            "error",
        )

        return render_form()


    # ========================================================
    # POSTER FILE SIZE
    # ========================================================

    poster.stream.seek(
        0,
        os.SEEK_END,
    )

    poster_file_size = (
        poster.stream.tell()
    )

    poster.stream.seek(
        0
    )


    if (
        poster_file_size
        >
        RESTAURANT_POSTER_MAX_FILE_BYTES
    ):

        flash(
            (
                "The poster is too large. "
                "Maximum size is 8 MB."
            ),
            "error",
        )

        return render_form()


    # ========================================================
    # GALLERY FILES
    # ========================================================
    #
    # Every newly created restaurant starts on Free.
    #
    # Therefore gallery uploads are not accepted during
    # restaurant creation.
    #
    # The restaurant can upgrade to Standard/Premium and add
    # gallery images afterwards.
    # ========================================================

    gallery_files = (
        get_restaurant_gallery_files()
    )


    if gallery_files:

        flash(
            (
                "Gallery photos are available on "
                "the Standard and Premium restaurant "
                "plans. Create your restaurant first, "
                "then upgrade to add gallery photos."
            ),
            "error",
        )

        return render_form()


    # ========================================================
    # CLOUDINARY TRACKING
    # ========================================================

    poster_public_id = None


    try:

        # ====================================================
        # UPLOAD MAIN POSTER
        # ====================================================

        upload_result = (
            cloudinary.uploader.upload(
                poster,

                resource_type="image",

                folder=(
                    "kalxa/"
                    f"organizers/{organizer.id}/"
                    "restaurants/posters"
                ),

                use_filename=True,

                unique_filename=True,

                overwrite=False,
            )
        )


        poster_public_id = (
            upload_result.get(
                "public_id"
            )
        )


        poster_secure_url = (
            upload_result.get(
                "secure_url"
            )
        )


        if (
            not poster_public_id
            or
            not poster_secure_url
        ):

            raise RuntimeError(
                (
                    "Cloudinary did not return "
                    "the uploaded poster."
                )
            )


        # ====================================================
        # CREATE RESTAURANT
        # ========================================================
        #
        # Every new restaurant starts on Free.
        #
        # Free has no expiry date.
        # ====================================================

        advert = RestaurantAdvert(

            organizer_id=(
                organizer.id
            ),

            business_name=(
                business_name
            ),

            headline=(
                headline
            ),

            description=(
                description
            ),

            area=(
                area
            ),

            address=(
                address
            ),

            directions_url=(
                directions_url
            ),

            whatsapp_number=(
                whatsapp_number
            ),

            phone_number=(
                phone_number
            ),

            poster_image_url=(
                poster_secure_url
            ),

            poster_cloudinary_public_id=(
                poster_public_id
            ),

            starts_at=(
                starts_at
            ),

            ends_at=(
                ends_at
            ),

            active=True,

            # ================================================
            # RESTAURANT SUBSCRIPTION
            # ================================================

            subscription_tier=(
                RESTAURANT_PLAN_FREE
            ),

            subscription_status=(
                "active"
            ),

            subscription_started_at=(
                datetime.utcnow()
            ),

            subscription_expires_at=None,
        )


        db.session.add(
            advert
        )

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        # ====================================================
        # CLEAN FAILED CLOUDINARY UPLOAD
        # ====================================================

        if poster_public_id:

            try:

                cloudinary.uploader.destroy(
                    poster_public_id,
                    resource_type="image",
                )

            except Exception:

                current_app.logger.exception(
                    (
                        "[Restaurant Advert] "
                        "Unable to remove failed "
                        "poster upload."
                    )
                )


        current_app.logger.exception(
            (
                "[Restaurant Advert] "
                "Create failed "
                "organizer_id=%s "
                "error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            (
                "Restaurant advert could "
                "not be created."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_create_restaurant"
            )
        )


    # ========================================================
    # AUTOMATIC RESTAURANT PUSH
    # ========================================================
    #
    # Restaurant creation has succeeded at this point.
    #
    # Free restaurants are allowed to use Reel/Discovery.
    # ========================================================

    if advert.can_use_reel:

        try:

            send_automatic_restaurant_push(
                advert
            )

        except Exception as error:

            current_app.logger.exception(
                (
                    "[Restaurant Advert] "
                    "Advert created but automatic "
                    "push notification failed "
                    "advert_id=%s "
                    "organizer_id=%s "
                    "error=%s"
                ),
                advert.id,
                organizer.id,
                error,
            )


    # ========================================================
    # SUCCESS
    # ========================================================

    flash(
        (
            "Restaurant created successfully "
            "on the Free plan."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_manage_restaurant",
            advert_id=advert.id,
        )
    )


# ============================================================
# EDIT RESTAURANT
# ============================================================
# ============================================================
# EDIT RESTAURANT
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/edit",
    methods=["GET", "POST"],
)
def admin_edit_restaurant(
    advert_id,
):

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    # ========================================================
    # RESTAURANT ACCOUNT ACCESS
    # ========================================================
    #
    # IMPORTANT:
    #
    # This must NOT require the legacy Organizer/Event SaaS
    # subscription.
    #
    # Restaurant subscription permissions belong to:
    #
    #     RestaurantAdvert
    # ========================================================

    subscription_auth = (
        require_restaurant_subscription()
    )

    if subscription_auth:
        return subscription_auth


    organizer = (
        get_current_organizer()
    )


    if not organizer:

        flash(
            "Organizer account could not be found.",
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # ORGANIZER ACTIVE
    # ========================================================

    if not organizer.active:

        flash(
            "Your organizer account is inactive.",
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # RESTAURANT + OWNERSHIP
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
            organizer_id=organizer.id,
        )

        .first_or_404()
    )


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================

    if not advert.active:

        abort(403)


    # ========================================================
    # RESTAURANT ORGANIZER SAFETY
    # ========================================================

    if not advert.organizer:

        abort(403)


    if not advert.organizer.active:

        abort(403)


    if (
        getattr(
            advert.organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # STANDARD / PREMIUM ACTIVE
    #     -> paid features enabled
    #
    # STANDARD / PREMIUM GRACE
    #     -> paid features remain enabled
    #
    # GRACE EXPIRED
    #     -> automatically downgrade to Free
    #
    # Existing paid content is NOT deleted.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # FORM DATE HELPERS
    # ========================================================

    today_iso = (
        datetime.utcnow()
        .date()
        .isoformat()
    )


    # ========================================================
    # LEGACY ORGANIZER SUBSCRIPTION DATE
    # ========================================================
    #
    # Keep only if restaurant_form.html still expects it.
    #
    # It does NOT control RestaurantAdvert capabilities.
    # ========================================================

    subscription_end_iso = (
        organizer.subscription_expires_at
        .date()
        .isoformat()

        if organizer.subscription_expires_at

        else ""
    )


    # ========================================================
    # FORM RENDER HELPER
    # ========================================================

    def render_form():

        return render_template(
            "admin/restaurant_form.html",

            organizer=organizer,

            advert=advert,

            today_iso=today_iso,

            subscription_end_iso=(
                subscription_end_iso
            ),

            # =================================================
            # RESTAURANT PLAN
            # =================================================

            restaurant_plan=(
                advert.normalized_subscription_tier
            ),

            restaurant_plan_name=(
                advert.subscription_plan_name
            ),

            restaurant_plan_price=(
                advert.subscription_price
            ),

            # =================================================
            # RESTAURANT PLAN CAPABILITIES
            # =================================================

            can_use_reel=(
                advert.can_use_reel
            ),

            can_use_gallery=(
                advert.can_use_gallery
            ),

            can_use_opening_hours=(
                advert.can_use_opening_hours
            ),

            can_receive_customer_experiences=(
                advert.can_receive_customer_experiences
            ),

            can_use_stories=(
                advert.can_use_stories
            ),

            can_view_analytics=(
                advert.can_view_analytics
            ),
        )


    # ========================================================
    # GET
    # ========================================================

    if request.method == "GET":

        return render_form()


    # ========================================================
    # POST
    # ========================================================

    # ========================================================
    # RE-SYNC BEFORE MUTATION
    # ========================================================
    #
    # The subscription may have changed between GET and POST.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # BUSINESS NAME
    # ========================================================

    business_name = (
        request.form.get(
            "business_name",
            "",
        )
        .strip()
    )


    if not business_name:

        flash(
            "Business name is required.",
            "error",
        )

        return render_form()


    # ========================================================
    # CAMPAIGN SCHEDULE
    # ========================================================
    #
    # Campaign is available on ALL restaurant plans:
    #
    # FREE       -> YES
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    (
        starts_at,
        ends_at,
        schedule_error,
    ) = build_restaurant_campaign_schedule(
        request.form,
        organizer,
        existing_advert=advert,
    )


    if schedule_error:

        flash(
            schedule_error,
            "error",
        )

        return render_form()


    # ========================================================
    # EXISTING GALLERY COUNT
    # ========================================================

    existing_gallery_count = (
        RestaurantGalleryImage.query

        .filter_by(
            restaurant_advert_id=advert.id
        )

        .count()
    )


    # ========================================================
    # NEW GALLERY FILES
    # ========================================================

    gallery_files = (
        get_restaurant_gallery_files()
    )


    # ========================================================
    # GALLERY PLAN PERMISSION
    # ========================================================
    #
    # FREE
    #     Upload gallery        NO
    #
    # STANDARD
    #     Upload gallery        YES
    #
    # PREMIUM
    #     Upload gallery        YES
    #
    # Existing images are retained when a restaurant
    # downgrades to Free.
    # ========================================================

    if (
        gallery_files
        and
        not advert.can_use_gallery
    ):

        flash(
            (
                "Gallery photos are available "
                "on the Standard and Premium "
                "restaurant plans."
            ),
            "error",
        )

        return render_form()


    # ========================================================
    # VALIDATE GALLERY FILES
    # ========================================================

    if gallery_files:

        (
            gallery_valid,
            gallery_error,
        ) = validate_restaurant_gallery_files(
            gallery_files,
            existing_count=(
                existing_gallery_count
            ),
        )


        if not gallery_valid:

            flash(
                gallery_error,
                "error",
            )

            return render_form()


    # ========================================================
    # OPTIONAL NEW POSTER
    # ========================================================
    #
    # Main poster belongs to the basic restaurant profile.
    #
    # FREE       -> YES
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    new_poster = (
        request.files.get(
            "poster"
        )
    )


    # ========================================================
    # UPLOAD TRACKING
    # ========================================================
    #
    # Used for Cloudinary cleanup if database persistence
    # fails.
    # ========================================================

    uploaded_public_id = None

    old_public_id = None

    gallery_uploaded_public_ids = []


    try:

        # ====================================================
        # OPTIONAL POSTER UPLOAD
        # ====================================================

        if (
            new_poster
            and
            new_poster.filename
        ):

            # =================================================
            # POSTER FILE TYPE
            # =================================================

            if not allowed_restaurant_poster_filename(
                new_poster.filename
            ):

                flash(
                    (
                        "Use a JPG, JPEG, PNG "
                        "or WebP poster."
                    ),
                    "error",
                )

                return render_form()


            # =================================================
            # POSTER FILE SIZE
            # =================================================

            new_poster.stream.seek(
                0,
                os.SEEK_END,
            )


            file_size = (
                new_poster.stream.tell()
            )


            new_poster.stream.seek(
                0
            )


            if (
                file_size
                >
                RESTAURANT_POSTER_MAX_FILE_BYTES
            ):

                flash(
                    (
                        "The poster is too large. "
                        "Maximum size is 8 MB."
                    ),
                    "error",
                )

                return render_form()


            # =================================================
            # UPLOAD NEW POSTER
            # =================================================

            upload_result = (
                cloudinary.uploader.upload(
                    new_poster,

                    resource_type="image",

                    folder=(
                        f"kalxa/organizers/"
                        f"{organizer.id}/"
                        "restaurants/posters"
                    ),

                    use_filename=True,

                    unique_filename=True,

                    overwrite=False,
                )
            )


            uploaded_public_id = (
                upload_result.get(
                    "public_id"
                )
            )


            secure_url = (
                upload_result.get(
                    "secure_url"
                )
            )


            if (
                not uploaded_public_id
                or
                not secure_url
            ):

                raise RuntimeError(
                    (
                        "Cloudinary did not return "
                        "the uploaded poster."
                    )
                )


            old_public_id = (
                advert
                .poster_cloudinary_public_id
            )


            advert.poster_cloudinary_public_id = (
                uploaded_public_id
            )


            advert.poster_image_url = (
                secure_url
            )


        # ====================================================
        # UPDATE BASIC RESTAURANT DETAILS
        # ========================================================
        #
        # Available on Free, Standard and Premium.
        # ====================================================

        advert.business_name = (
            business_name
        )


        advert.headline = (
            request.form.get(
                "headline",
                "",
            )
            .strip()
            or None
        )


        advert.description = (
            request.form.get(
                "description",
                "",
            )
            .strip()
            or None
        )


        advert.area = (
            request.form.get(
                "area",
                "",
            )
            .strip()
            or None
        )


        advert.address = (
            request.form.get(
                "address",
                "",
            )
            .strip()
            or None
        )


        advert.whatsapp_number = (
            request.form.get(
                "whatsapp_number",
                "",
            )
            .strip()
            or None
        )


        advert.phone_number = (
            request.form.get(
                "phone_number",
                "",
            )
            .strip()
            or None
        )


        advert.directions_url = (
            valid_restaurant_directions_url(
                request.form.get(
                    "directions_url",
                    "",
                )
            )
        )


        # ====================================================
        # UPDATE CAMPAIGN
        # ========================================================

        advert.starts_at = (
            starts_at
        )


        advert.ends_at = (
            ends_at
        )


        # ====================================================
        # FINAL GALLERY CAPABILITY CHECK
        # ========================================================
        #
        # This is intentionally close to the actual gallery
        # database mutation.
        #
        # It provides another server-side boundary before
        # Cloudinary uploads and RestaurantGalleryImage rows
        # are created.
        # ========================================================

        if gallery_files:

            sync_restaurant_subscription(
                advert
            )


            if not advert.can_use_gallery:

                db.session.rollback()


                flash(
                    (
                        "Gallery photos are available "
                        "on the Standard and Premium "
                        "restaurant plans."
                    ),
                    "error",
                )


                return redirect(
                    url_for(
                        "admin_edit_restaurant",
                        advert_id=advert.id,
                    )
                )


        # ====================================================
        # ADD GALLERY PHOTOS
        # ========================================================

        next_image_order = (
            existing_gallery_count
            + 1
        )


        for image in gallery_files:

            # =================================================
            # UPLOAD GALLERY IMAGE
            # =================================================

            gallery_result = (
                upload_restaurant_gallery_image(
                    image,
                    organizer.id,
                    advert.id,
                )
            )


            public_id = (
                gallery_result[
                    "public_id"
                ]
            )


            gallery_uploaded_public_ids.append(
                public_id
            )


            # =================================================
            # CREATE GALLERY DATABASE ROW
            # =================================================

            gallery_image = (
                RestaurantGalleryImage(

                    restaurant_advert_id=(
                        advert.id
                    ),

                    cloudinary_public_id=(
                        public_id
                    ),

                    image_url=(
                        gallery_result[
                            "secure_url"
                        ]
                    ),

                    image_order=(
                        next_image_order
                    ),

                    width=(
                        gallery_result[
                            "width"
                        ]
                    ),

                    height=(
                        gallery_result[
                            "height"
                        ]
                    ),

                    file_bytes=(
                        gallery_result[
                            "file_bytes"
                        ]
                    ),
                )
            )


            db.session.add(
                gallery_image
            )


            next_image_order += 1


        # ====================================================
        # SAVE DATABASE CHANGES
        # ====================================================

        db.session.commit()


    # ========================================================
    # UPDATE FAILURE
    # ========================================================

    except Exception as error:

        db.session.rollback()


        # ====================================================
        # CLEAN NEW POSTER
        # ====================================================

        if uploaded_public_id:

            try:

                cloudinary.uploader.destroy(
                    uploaded_public_id,
                    resource_type="image",
                    invalidate=True,
                )

            except Exception:

                current_app.logger.exception(
                    (
                        "[Restaurant Advert Edit] "
                        "Failed to clean up newly "
                        "uploaded poster."
                    )
                )


        # ====================================================
        # CLEAN NEW GALLERY FILES
        # ====================================================

        for public_id in (
            gallery_uploaded_public_ids
        ):

            try:

                cloudinary.uploader.destroy(
                    public_id,
                    resource_type="image",
                    invalidate=True,
                )

            except Exception:

                current_app.logger.exception(
                    (
                        "[Restaurant Gallery] "
                        "Failed to clean up newly "
                        "uploaded gallery image "
                        "public_id=%s"
                    ),
                    public_id,
                )


        # ====================================================
        # LOG ERROR
        # ====================================================

        current_app.logger.exception(
            (
                "[Restaurant Advert Edit] "
                "Failed organizer_id=%s "
                "advert_id=%s error=%s"
            ),
            organizer.id,
            advert.id,
            error,
        )


        flash(
            (
                "Restaurant advert could "
                "not be updated."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_edit_restaurant",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # REMOVE OLD POSTER AFTER SUCCESS
    # ========================================================
    #
    # IMPORTANT:
    #
    # Delete the previous Cloudinary poster only AFTER the
    # database transaction succeeds.
    # ========================================================

    if (
        old_public_id
        and
        old_public_id
        != uploaded_public_id
    ):

        try:

            cloudinary.uploader.destroy(
                old_public_id,
                resource_type="image",
                invalidate=True,
            )

        except Exception:

            current_app.logger.exception(
                (
                    "[Restaurant Advert Edit] "
                    "Old poster cleanup failed "
                    "public_id=%s"
                ),
                old_public_id,
            )


    # ========================================================
    # SUCCESS MESSAGE
    # ========================================================

    if gallery_files:

        photo_count = (
            len(
                gallery_files
            )
        )


        photo_label = (
            "photo"

            if photo_count == 1

            else "photos"
        )


        flash(
            (
                "Restaurant updated successfully. "
                f"{photo_count} gallery "
                f"{photo_label} added."
            ),
            "success",
        )


    else:

        flash(
            "Restaurant advert updated.",
            "success",
        )


    # ========================================================
    # REDIRECT TO RESTAURANT CONTROL CENTRE
    # ========================================================

    return redirect(
        url_for(
            "admin_manage_restaurant",
            advert_id=advert.id,
        )
    )


# ============================================================
# DELETE CLOUDINARY REEL
# ============================================================

def delete_cloudinary_reel(
    public_id,
):

    # ========================================================
    # NOTHING TO DELETE
    # ========================================================

    if not public_id:
        return


    # ========================================================
    # DELETE CLOUDINARY VIDEO
    # ========================================================
    #
    # IMPORTANT:
    #
    # This helper only removes the Cloudinary asset.
    #
    # Restaurant plan permissions must be checked by the
    # restaurant Reel route BEFORE this helper is called.
    #
    # Do NOT add:
    #
    #     Organizer.is_subscription_active
    #
    # here.
    #
    # This helper can also be used for cleanup after a failed
    # upload, where subscription checks would be inappropriate.
    # ========================================================

    try:

        cloudinary.uploader.destroy(
            public_id,
            resource_type="video",
            invalidate=True,
        )


    except Exception as error:

        current_app.logger.exception(
            (
                "[Restaurant/Event Reel] "
                "Unable to delete Cloudinary "
                "video asset "
                "public_id=%s "
                "error=%s"
            ),
            public_id,
            error,
        )



# ============================================================
# DELETE RESTAURANT GALLERY IMAGE
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/gallery/<int:image_id>/delete",
    methods=["POST"],
)
def admin_delete_restaurant_gallery_image(
    advert_id,
    image_id,
):

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    # ========================================================
    # RESTAURANT ACCOUNT ACCESS
    # ========================================================
    #
    # IMPORTANT:
    #
    # This checks restaurant-account access only.
    #
    # It must NOT require the legacy Organizer/Event SaaS
    # subscription.
    # ========================================================

    subscription_auth = (
        require_restaurant_subscription()
    )

    if subscription_auth:
        return subscription_auth


    # ========================================================
    # CURRENT ORGANIZER
    # ========================================================

    organizer = (
        get_current_organizer()
    )


    if not organizer:

        abort(401)


    # ========================================================
    # ORGANIZER ACTIVE
    # ========================================================

    if not organizer.active:

        abort(403)


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # RESTAURANT + OWNERSHIP
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
            organizer_id=organizer.id,
        )

        .first_or_404()
    )


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================

    if not advert.active:

        abort(403)


    # ========================================================
    # RESTAURANT ORGANIZER SAFETY
    # ========================================================

    if not advert.organizer:

        abort(403)


    if not advert.organizer.active:

        abort(403)


    if (
        getattr(
            advert.organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # STANDARD / PREMIUM ACTIVE
    #     -> gallery management allowed
    #
    # STANDARD / PREMIUM GRACE
    #     -> gallery management allowed
    #
    # GRACE EXPIRED
    #     -> automatically downgraded to Free
    #
    # FREE
    #     -> gallery management blocked
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # GALLERY PLAN PERMISSION
    # ========================================================

    if not advert.can_use_gallery:

        flash(
            (
                "Gallery management is available "
                "on the Standard and Premium "
                "restaurant plans."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_edit_restaurant",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # FIND GALLERY IMAGE
    # ========================================================
    #
    # IMPORTANT:
    #
    # Query using BOTH:
    #
    #     image_id
    #     restaurant_advert_id
    #
    # This prevents one restaurant owner from submitting an
    # image ID belonging to another restaurant.
    # ========================================================

    gallery_image = (
        RestaurantGalleryImage.query

        .filter_by(
            id=image_id,
            restaurant_advert_id=advert.id,
        )

        .first_or_404()
    )


    # ========================================================
    # SAVE CLOUDINARY PUBLIC ID
    # ========================================================
    #
    # Keep this before deleting the database record.
    # ========================================================

    public_id = (
        gallery_image.cloudinary_public_id
    )


    # ========================================================
    # FINAL SUBSCRIPTION CHECK
    # ========================================================
    #
    # Keep the destructive operation behind a final
    # capability boundary.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    if not advert.can_use_gallery:

        flash(
            (
                "Gallery management is available "
                "on the Standard and Premium "
                "restaurant plans."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_edit_restaurant",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # DELETE DATABASE RECORD
    # ========================================================
    #
    # Database first.
    #
    # If the database operation fails, the Cloudinary asset
    # remains intact.
    #
    # If the database succeeds but Cloudinary cleanup fails,
    # the user-facing gallery is still correctly updated and
    # the orphaned Cloudinary asset can be cleaned later.
    # ========================================================

    try:

        db.session.delete(
            gallery_image
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Gallery] "
                "Unable to delete gallery image "
                "advert_id=%s "
                "image_id=%s "
                "organizer_id=%s "
                "error=%s"
            ),
            advert.id,
            image_id,
            organizer.id,
            error,
        )


        flash(
            (
                "The gallery photo could not "
                "be deleted. Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_edit_restaurant",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # DELETE CLOUDINARY ASSET
    # ========================================================
    #
    # Only remove the Cloudinary image AFTER the database
    # commit succeeds.
    # ========================================================

    if public_id:

        try:

            cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )


        except Exception as error:

            current_app.logger.exception(
                (
                    "[Restaurant Gallery] "
                    "Database row deleted but "
                    "Cloudinary cleanup failed "
                    "advert_id=%s "
                    "image_id=%s "
                    "public_id=%s "
                    "error=%s"
                ),
                advert.id,
                image_id,
                public_id,
                error,
            )


    # ========================================================
    # SUCCESS
    # ========================================================

    flash(
        "Gallery photo deleted.",
        "success",
    )


    return redirect(
        url_for(
            "admin_edit_restaurant",
            advert_id=advert.id,
        )
    )
@app.route(
    "/restaurant/<int:advert_id>/rating-qr",
    methods=["POST"],
)
def create_restaurant_rating_qr(
    advert_id,
):

    # ========================================================
    # ORGANIZER AUTHENTICATION
    # ========================================================

    current_organizer = (
        get_current_organizer()
    )


    if not current_organizer:

        abort(401)


    # ========================================================
    # OWNER ACCOUNT ACTIVE
    # ========================================================

    if not current_organizer.active:

        abort(403)


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================
    #
    # Rating QR codes belong only to restaurant accounts.
    #
    # Do NOT use:
    #
    #     organizer.is_subscription_active
    #
    # That belongs to the legacy Organizer/Event SaaS
    # subscription system.
    # ========================================================

    if (
        getattr(
            current_organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
        )

        .first_or_404()
    )


    # ========================================================
    # OWNERSHIP SAFETY
    # ========================================================

    if (
        advert.organizer_id
        !=
        current_organizer.id
    ):

        abort(403)


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================

    if not advert.active:

        abort(403)


    # ========================================================
    # RESTAURANT ORGANIZER SAFETY
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        abort(403)


    if not organizer.active:

        abort(403)


    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # STANDARD / PREMIUM ACTIVE
    #     -> Rating QR available
    #
    # STANDARD / PREMIUM EXPIRED <= 5 DAYS
    #     -> grace period
    #     -> Rating QR remains available
    #
    # STANDARD / PREMIUM EXPIRED > 5 DAYS
    #     -> automatically downgraded to Free
    #
    # FREE
    #     -> Rating QR unavailable
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # CUSTOMER EXPERIENCE FEATURE REQUIRED
    # ========================================================
    #
    # The Rating QR exists specifically to collect customer
    # restaurant experiences.
    #
    # Therefore its availability must follow the same
    # customer_experiences capability.
    #
    #
    # FREE
    # --------------------------------------------------------
    #
    # Public profile               YES
    # Campaign                     YES
    # Reel / Discovery             YES
    #
    # Customer experiences         NO
    # Rating QR                    NO
    #
    #
    # STANDARD
    # --------------------------------------------------------
    #
    # Active                       YES
    # 5-day grace                  YES
    #
    #
    # PREMIUM
    # --------------------------------------------------------
    #
    # Active                       YES
    # 5-day grace                  YES
    # ========================================================

    if not advert.can_receive_customer_experiences:

        abort(403)


    # ========================================================
    # CAMPAIGN AVAILABILITY
    # ========================================================
    #
    # Keep QR creation aligned with the public customer
    # experience system.
    #
    # Operational hours are NOT checked.
    # ========================================================

    now = (
        datetime.utcnow()
    )


    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        abort(403)


    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        abort(403)


    # ========================================================
    # FINAL EXPERIENCE ELIGIBILITY
    # ========================================================
    #
    # Use the same centralized eligibility helper used by:
    #
    #     /experiences/new
    #
    #     /r/<public_code>
    #
    #     get_taggable_restaurants()
    #
    # This keeps Rating QR creation consistent with the rest
    # of the customer-experience system.
    # ========================================================

    if not restaurant_can_receive_experience_posts(
        advert
    ):

        abort(403)


    # ========================================================
    # CREATE OR REUSE PERMANENT QR
    # ========================================================
    #
    # We reuse the restaurant's existing main Rating QR where
    # possible.
    #
    # If the restaurant later falls back to Free, the QR
    # record can remain stored in PostgreSQL.
    #
    # It simply becomes unusable because the public QR route
    # checks the current RestaurantAdvert capability.
    # ========================================================

    restaurant_qr = (
        get_or_create_restaurant_main_qr(
            advert
        )
    )


    # ========================================================
    # PUBLIC RATING URL
    # ========================================================

    restaurant_rating_url = (
        url_for(
            "restaurant_rating_qr_page",

            public_code=(
                restaurant_qr.public_code
            ),

            _external=True,

            _scheme="https",
        )
    )


    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "success": True,

        "restaurant_id": (
            advert.id
        ),

        "business_name": (
            advert.business_name
        ),

        "public_code": (
            restaurant_qr.public_code
        ),

        "rating_url": (
            restaurant_rating_url
        ),
    }


# ============================================================
# DOWNLOAD RESTAURANT RATING QR
# ============================================================

@app.route(
    "/restaurant/<int:advert_id>/rating-qr/download"
)
def download_restaurant_rating_qr(
    advert_id,
):

    # ========================================================
    # ORGANIZER AUTHENTICATION
    # ========================================================

    current_organizer = (
        get_current_organizer()
    )


    if not current_organizer:

        abort(401)


    # ========================================================
    # OWNER ACCOUNT ACTIVE
    # ========================================================

    if not current_organizer.active:

        abort(403)


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    if (
        getattr(
            current_organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id
        )

        .first_or_404()
    )


    # ========================================================
    # OWNERSHIP
    # ========================================================

    if (
        advert.organizer_id
        !=
        current_organizer.id
    ):

        abort(403)


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================

    if not advert.active:

        abort(403)


    # ========================================================
    # RESTAURANT ORGANIZER SAFETY
    # ========================================================
    #
    # Do NOT check:
    #
    #     organizer.is_subscription_active
    #
    # Restaurant subscription access belongs to
    # RestaurantAdvert.
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        abort(403)


    if not organizer.active:

        abort(403)


    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # CUSTOMER EXPERIENCE FEATURE REQUIRED
    # ========================================================
    #
    # FREE
    #     -> Rating QR download disabled
    #
    # STANDARD ACTIVE
    #     -> enabled
    #
    # STANDARD GRACE
    #     -> enabled
    #
    # PREMIUM ACTIVE
    #     -> enabled
    #
    # PREMIUM GRACE
    #     -> enabled
    #
    # AFTER GRACE
    #     -> restaurant becomes Free
    #     -> download disabled
    # ========================================================

    if not advert.can_receive_customer_experiences:

        abort(403)


    # ========================================================
    # CAMPAIGN AVAILABILITY
    # ========================================================
    #
    # Rating QR download follows the same campaign
    # availability rules as customer experience submission.
    #
    # Operational hours are deliberately NOT checked.
    # ========================================================

    now = (
        datetime.utcnow()
    )


    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        abort(403)


    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        abort(403)


    # ========================================================
    # FINAL EXPERIENCE ELIGIBILITY
    # ========================================================

    if not restaurant_can_receive_experience_posts(
        advert
    ):

        abort(403)


    # ========================================================
    # GET OR CREATE PERMANENT QR
    # ========================================================

    restaurant_qr = (
        get_or_create_restaurant_main_qr(
            advert
        )
    )


    # ========================================================
    # PUBLIC DESTINATION
    # ========================================================

    rating_url = (
        url_for(
            "restaurant_rating_qr_page",

            public_code=(
                restaurant_qr.public_code
            ),

            _external=True,

            _scheme="https",
        )
    )


    # ========================================================
    # GENERATE QR
    # ========================================================

    qr = qrcode.QRCode(
        version=None,

        error_correction=(
            qrcode.constants.ERROR_CORRECT_M
        ),

        box_size=12,

        border=4,
    )


    qr.add_data(
        rating_url
    )


    qr.make(
        fit=True
    )


    qr_image = (
        qr.make_image(
            fill_color="black",
            back_color="white",
        )
    )


    # ========================================================
    # PNG BUFFER
    # ========================================================

    image_buffer = (
        io.BytesIO()
    )


    qr_image.save(
        image_buffer,
        format="PNG",
    )


    image_buffer.seek(
        0
    )


    # ========================================================
    # SAFE FILE NAME
    # ========================================================

    safe_business_name = (
        "".join(
            character

            if (
                character.isalnum()
                or
                character
                in {
                    "-",
                    "_",
                }
            )

            else "-"

            for character
            in advert.business_name
        )

        .strip("-")

        .lower()
    )


    if not safe_business_name:

        safe_business_name = (
            f"restaurant-{advert.id}"
        )


    filename = (
        f"kalxa-{safe_business_name}-rating-qr.png"
    )


    # ========================================================
    # DOWNLOAD
    # ========================================================

    return send_file(
        image_buffer,

        mimetype="image/png",

        as_attachment=True,

        download_name=filename,

        max_age=0,
    )
def restaurant_can_receive_experience_posts(
    advert,
):

    # ========================================================
    # RESTAURANT REQUIRED
    # ========================================================

    if not advert:

        return False


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # This keeps the RestaurantAdvert subscription state
    # current before checking customer-experience access.
    #
    # STANDARD / PREMIUM:
    #
    #     Active
    #         -> paid features available
    #
    #     Expired <= 5 days
    #         -> grace period
    #         -> paid features remain available
    #
    #     Expired > 5 days
    #         -> automatically downgraded to Free
    #
    # FREE:
    #
    #     Remains active indefinitely, but does NOT have the
    #     customer_experiences capability.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # RESTAURANT ACTIVE
    # ========================================================
    #
    # A paused/deactivated restaurant cannot receive customer
    # experience submissions regardless of plan.
    # ========================================================

    if not advert.active:

        return False


    # ========================================================
    # ORGANIZER
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        return False


    # ========================================================
    # ORGANIZER ACTIVE
    # ========================================================

    if not organizer.active:

        return False


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================
    #
    # Customer restaurant experiences belong only to Kalxa
    # restaurant accounts.
    #
    # IMPORTANT:
    #
    # Do NOT check:
    #
    #     organizer.is_subscription_active
    #
    # That belongs to the legacy Organizer/Event SaaS
    # subscription system.
    # ========================================================

    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        return False


    # ========================================================
    # CUSTOMER EXPERIENCE PLAN CAPABILITY
    # ========================================================
    #
    # FREE
    # --------------------------------------------------------
    #
    # Profile                     YES
    # Campaign                    YES
    # Reel / Discovery            YES
    #
    # Customer experiences        NO
    #
    #
    # STANDARD
    # --------------------------------------------------------
    #
    # Customer experiences        YES
    #
    #
    # PREMIUM
    # --------------------------------------------------------
    #
    # Customer experiences        YES
    #
    #
    # STANDARD / PREMIUM GRACE
    # --------------------------------------------------------
    #
    # Customer experiences remain available during the
    # configured 5-day grace period.
    #
    #
    # AFTER GRACE
    # --------------------------------------------------------
    #
    # sync_restaurant_subscription() converts the restaurant
    # back to Free.
    #
    # advert.can_receive_customer_experiences then becomes
    # False automatically.
    # ========================================================

    if not advert.can_receive_customer_experiences:

        return False


    # ========================================================
    # CAMPAIGN WINDOW
    # ========================================================
    #
    # Customer experiences are only accepted while the public
    # restaurant campaign/profile is currently available.
    #
    # This check is independent of operational hours.
    #
    # A restaurant does NOT need its operational hours to be
    # currently open in order for this helper to return True.
    #
    # Therefore:
    #
    #     opening_hours != experience eligibility
    #
    # This is especially important because operational hours
    # are a Standard/Premium display feature rather than the
    # restaurant campaign lifecycle itself.
    # ========================================================

    now = (
        datetime.utcnow()
    )


    # ========================================================
    # CAMPAIGN NOT STARTED
    # ========================================================

    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        return False


    # ========================================================
    # CAMPAIGN ENDED
    # ========================================================

    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        return False


    # ========================================================
    # ELIGIBLE
    # ========================================================
    #
    # At this point:
    #
    #     restaurant exists
    #     restaurant is active
    #     organizer exists
    #     organizer is active
    #     organizer is a restaurant account
    #     restaurant has customer-experience capability
    #     campaign has started
    #     campaign has not ended
    #
    # Therefore customer experience submission is allowed.
    # ========================================================

    return True



def get_taggable_restaurants():

    # ========================================================
    # CURRENT TIME
    # ========================================================

    now = (
        datetime.utcnow()
    )


    # ========================================================
    # PAID PLAN GRACE CUTOFF
    # ========================================================
    #
    # Restaurant customer experiences are available to:
    #
    #     STANDARD
    #     PREMIUM
    #
    # while the subscription is:
    #
    #     active
    #
    # OR
    #
    #     within the configured 5-day grace period.
    #
    #
    # Example:
    #
    #     subscription_expires_at = 1 October
    #
    #     grace ends             = 6 October
    #
    #
    # SQL equivalent:
    #
    #     subscription_expires_at
    #         + 5 days
    #         > now
    #
    # Rearranged:
    #
    #     subscription_expires_at
    #         > now - 5 days
    #
    #
    # IMPORTANT:
    #
    # Free restaurants do NOT have an expiry date and are
    # deliberately excluded from this query.
    # ========================================================

    grace_cutoff = (
        now
        - timedelta(
            days=(
                RESTAURANT_SUBSCRIPTION_GRACE_DAYS
            )
        )
    )


    # ========================================================
    # DATABASE QUERY
    # ========================================================
    #
    # We perform the strongest filtering possible directly
    # in PostgreSQL.
    #
    # This prevents Free/inactive/expired restaurants from
    # being unnecessarily loaded into the public restaurant
    # selection list.
    # ========================================================

    restaurants = (
        RestaurantAdvert.query

        .join(
            Organizer,

            RestaurantAdvert.organizer_id
            ==
            Organizer.id,
        )


        # ====================================================
        # RESTAURANT ACTIVE
        # ====================================================
        #
        # Paused/deactivated restaurants cannot receive
        # customer experiences regardless of plan.
        # ====================================================

        .filter(
            RestaurantAdvert.active.is_(
                True
            )
        )


        # ====================================================
        # RESTAURANT SUBSCRIPTION STATUS
        # ====================================================
        #
        # The RestaurantAdvert subscription is the source of
        # truth.
        #
        # Do NOT use:
        #
        #     Organizer.is_subscription_active
        #
        # That belongs to the legacy Event/Organizer SaaS
        # subscription system.
        # ====================================================

        .filter(
            RestaurantAdvert.subscription_status
            == "active"
        )


        # ====================================================
        # CUSTOMER EXPERIENCE PLANS
        # ====================================================
        #
        # FREE
        # ----------------------------------------------------
        #
        # Public profile               YES
        # Contact/details              YES
        # Main poster                  YES
        # Campaign                     YES
        # Reel / Discovery             YES
        #
        # Customer experiences         NO
        # Select Restaurant dropdown   NO
        #
        #
        # STANDARD
        # ----------------------------------------------------
        #
        # Customer experiences         YES
        # Select Restaurant dropdown   YES
        #
        #
        # PREMIUM
        # ----------------------------------------------------
        #
        # Customer experiences         YES
        # Select Restaurant dropdown   YES
        #
        #
        # Therefore Free is intentionally absent from this
        # list.
        # ====================================================

        .filter(
            RestaurantAdvert.subscription_tier.in_(
                [
                    RESTAURANT_PLAN_STANDARD,
                    RESTAURANT_PLAN_PREMIUM,
                ]
            )
        )


        # ====================================================
        # PAID EXPIRY REQUIRED
        # ====================================================
        #
        # Standard and Premium are paid subscriptions and
        # therefore must have a subscription expiry date.
        #
        # Free restaurants normally have:
        #
        #     subscription_expires_at = None
        #
        # but Free has already been excluded above.
        # ====================================================

        .filter(
            RestaurantAdvert
            .subscription_expires_at
            .isnot(
                None
            )
        )


        # ====================================================
        # ACTIVE OR WITHIN 5-DAY GRACE
        # ====================================================
        #
        # Example:
        #
        # Paid subscription:
        #
        #     expires 1 October
        #
        # Grace:
        #
        #     1 October -> 6 October
        #
        # Restaurant remains taggable during that period.
        #
        # Once grace expires, it disappears from this query.
        #
        # The normal restaurant subscription synchronization
        # can then permanently convert the RestaurantAdvert
        # back to the Free tier.
        # ====================================================

        .filter(
            RestaurantAdvert.subscription_expires_at
            > grace_cutoff
        )


        # ====================================================
        # CAMPAIGN START
        # ====================================================
        #
        # Restaurant campaign must already have started.
        #
        # No start date means immediately available.
        # ====================================================

        .filter(
            or_(
                RestaurantAdvert.starts_at.is_(
                    None
                ),

                RestaurantAdvert.starts_at
                <= now,
            )
        )


        # ====================================================
        # CAMPAIGN END
        # ====================================================
        #
        # Restaurant campaign must not have ended.
        #
        # No end date means no campaign-end restriction.
        # ====================================================

        .filter(
            or_(
                RestaurantAdvert.ends_at.is_(
                    None
                ),

                RestaurantAdvert.ends_at
                > now,
            )
        )


        # ====================================================
        # ORGANIZER ACTIVE
        # ====================================================
        #
        # Restaurant owner account itself must still be
        # active.
        # ====================================================

        .filter(
            Organizer.active.is_(
                True
            )
        )


        # ====================================================
        # RESTAURANT ACCOUNT TYPE
        # ========================================================
        #
        # Only restaurant Organizer accounts are eligible.
        #
        # Again, we deliberately do NOT check the legacy
        # Organizer subscription.
        # ====================================================

        .filter(
            Organizer.account_type
            == "restaurant"
        )


        # ====================================================
        # DISPLAY ORDER
        # ====================================================
        #
        # Customer selector:
        #
        #     Restaurant Name
        #     Area
        # ====================================================

        .order_by(
            RestaurantAdvert
            .business_name
            .asc(),

            RestaurantAdvert
            .area
            .asc(),
        )


        # ====================================================
        # EXECUTE
        # ====================================================

        .all()
    )


    # ========================================================
    # FINAL CAPABILITY CHECK
    # ========================================================
    #
    # The SQL query above is the fast database-level filter.
    #
    # This second check is intentional.
    #
    # It ensures the final list also obeys the centralized
    # RestaurantAdvert capability system:
    #
    #     advert.can_receive_customer_experiences
    #
    # Therefore if we change the restaurant plan capability
    # configuration later, this function still respects it.
    #
    #
    # Expected:
    #
    # FREE
    #     -> False
    #
    # STANDARD ACTIVE
    #     -> True
    #
    # STANDARD GRACE
    #     -> True
    #
    # PREMIUM ACTIVE
    #     -> True
    #
    # PREMIUM GRACE
    #     -> True
    #
    # EXPIRED BEYOND GRACE
    #     -> False
    # ========================================================

    taggable_restaurants = []


    for advert in restaurants:

        # ====================================================
        # SYNCHRONIZE BEFORE FINAL CHECK
        # ====================================================
        #
        # Usually the SQL grace cutoff has already excluded an
        # expired restaurant.
        #
        # Synchronizing here keeps RestaurantAdvert state
        # consistent whenever this restaurant reaches the
        # final capability check.
        # ====================================================

        sync_restaurant_subscription(
            advert
        )


        # ====================================================
        # CUSTOMER EXPERIENCE CAPABILITY
        # ====================================================

        if not advert.can_receive_customer_experiences:

            continue


        # ====================================================
        # ADD TO PUBLIC SELECTOR
        # ====================================================

        taggable_restaurants.append(
            advert
        )


    # ========================================================
    # RETURN
    # ========================================================

    return taggable_restaurants
# ============================================================
# ADMIN - MANAGE RESTAURANT
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/manage"
)
def admin_manage_restaurant(
    advert_id,
):

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    organizer = (
        get_current_organizer()
    )


    # ========================================================
    # ORGANIZER REQUIRED
    # ========================================================

    if not organizer:

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # RESTAURANT ACCOUNT ONLY
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if (
        account_type
        != "restaurant"
    ):

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # ORGANIZER ACCOUNT MUST BE ACTIVE
    # ========================================================
    #
    # IMPORTANT:
    #
    # We only check whether the owner account itself is active.
    #
    # We deliberately DO NOT require:
    #
    #     organizer.is_subscription_active
    #
    # Restaurant subscription access is now controlled by the
    # RestaurantAdvert Free / Standard / Premium plan.
    # ========================================================

    if not organizer.active:

        flash(
            (
                "Your restaurant account is "
                "currently inactive."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
            organizer_id=organizer.id,
        )

        .first_or_404()
    )


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # STANDARD / PREMIUM lifecycle:
    #
    # Active
    #     -> paid features available
    #
    # Expired
    #     -> 5-day grace period
    #     -> paid features remain available
    #
    # Grace period expires
    #     -> automatically downgrade to Free
    #
    # Existing gallery images, hours and experiences remain
    # stored in the database.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # CURRENT TIME
    # ========================================================

    now = (
        datetime.utcnow()
    )


    # ========================================================
    # RESTAURANT PLAN
    # ========================================================

    restaurant_plan = (
        advert.normalized_subscription_tier
    )


    restaurant_plan_name = (
        advert.subscription_plan_name
    )


    restaurant_plan_price = (
        advert.subscription_price
    )


    # ========================================================
    # PLAN STATE
    # ========================================================

    restaurant_subscription_active = (
        advert.is_restaurant_subscription_active
    )


    restaurant_subscription_in_grace = (
        advert.is_restaurant_subscription_in_grace_period
    )


    restaurant_subscription_grace_ends_at = (
        advert.restaurant_subscription_grace_ends_at
    )


    # ========================================================
    # GRACE PERIOD DAYS REMAINING
    # ========================================================
    #
    # Example:
    #
    # Premium expires:
    #     1 October 10:00
    #
    # Grace ends:
    #     6 October 10:00
    #
    # During this period the owner retains Premium features
    # while being prompted to renew.
    # ========================================================

    restaurant_subscription_grace_days_remaining = (
        None
    )


    if (
        restaurant_subscription_in_grace
        and
        restaurant_subscription_grace_ends_at
    ):

        remaining_seconds = max(
            0,
            (
                restaurant_subscription_grace_ends_at
                -
                now
            ).total_seconds(),
        )


        # ----------------------------------------------------
        # ROUND UP PARTIAL DAYS
        # ----------------------------------------------------
        #
        # 2 days + 3 hours remaining should display as:
        #
        #     3 days remaining
        #
        # rather than:
        #
        #     2 days remaining
        # ----------------------------------------------------

        restaurant_subscription_grace_days_remaining = (
            max(
                1,
                int(
                    (
                        remaining_seconds
                        +
                        86399
                    )
                    //
                    86400
                ),
            )
        )


    # ========================================================
    # SUBSCRIPTION EXPIRY
    # ========================================================

    restaurant_subscription_expires_at = (
        advert.subscription_expires_at
    )


    # ========================================================
    # PLAN FLAGS
    # ========================================================

    is_free_plan = (
        advert.is_free_plan
    )


    is_standard_plan = (
        advert.is_standard_plan
    )


    is_premium_plan = (
        advert.is_premium_plan
    )


    # ========================================================
    # UPGRADE / RENEWAL OPTIONS
    # ========================================================
    #
    # These flags only control what the management page should
    # offer.
    #
    # The payment routes must still validate the requested plan
    # server-side when Paystack is connected.
    # ========================================================

    can_upgrade_to_standard = (
        restaurant_plan
        != RESTAURANT_PLAN_STANDARD
    )


    can_upgrade_to_premium = (
        restaurant_plan
        != RESTAURANT_PLAN_PREMIUM
    )


    can_renew_standard = (
        restaurant_plan
        == RESTAURANT_PLAN_STANDARD
    )


    can_renew_premium = (
        restaurant_plan
        == RESTAURANT_PLAN_PREMIUM
    )


    # ========================================================
    # PLAN PRICES
    # ========================================================

    standard_plan_price = (
        RESTAURANT_PLAN_PRICES[
            RESTAURANT_PLAN_STANDARD
        ]
    )


    premium_plan_price = (
        RESTAURANT_PLAN_PRICES[
            RESTAURANT_PLAN_PREMIUM
        ]
    )


    # ========================================================
    # RESTAURANT FEATURE PERMISSIONS
    # ========================================================

    can_use_reel = (
        advert.can_use_reel
    )


    can_use_gallery = (
        advert.can_use_gallery
    )


    can_use_opening_hours = (
        advert.can_use_opening_hours
    )


    can_receive_customer_experiences = (
        advert.can_receive_customer_experiences
    )


    can_use_stories = (
        advert.can_use_stories
    )


    can_view_analytics = (
        advert.can_view_analytics
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "admin/restaurant_manage.html",


        # ====================================================
        # ORGANIZER
        # ====================================================

        organizer=(
            organizer
        ),


        # ====================================================
        # RESTAURANT
        # ====================================================

        advert=(
            advert
        ),


        # ====================================================
        # RESTAURANT PLAN
        # ====================================================

        restaurant_plan=(
            restaurant_plan
        ),

        restaurant_plan_name=(
            restaurant_plan_name
        ),

        restaurant_plan_price=(
            restaurant_plan_price
        ),

        restaurant_subscription_active=(
            restaurant_subscription_active
        ),

        restaurant_subscription_expires_at=(
            restaurant_subscription_expires_at
        ),


        # ====================================================
        # GRACE PERIOD
        # ====================================================

        restaurant_subscription_in_grace=(
            restaurant_subscription_in_grace
        ),

        restaurant_subscription_grace_ends_at=(
            restaurant_subscription_grace_ends_at
        ),

        restaurant_subscription_grace_days_remaining=(
            restaurant_subscription_grace_days_remaining
        ),


        # ====================================================
        # PLAN FLAGS
        # ====================================================

        is_free_plan=(
            is_free_plan
        ),

        is_standard_plan=(
            is_standard_plan
        ),

        is_premium_plan=(
            is_premium_plan
        ),


        # ====================================================
        # PLAN PRICES
        # ====================================================

        standard_plan_price=(
            standard_plan_price
        ),

        premium_plan_price=(
            premium_plan_price
        ),


        # ====================================================
        # UPGRADE / RENEWAL CONTROLS
        # ====================================================

        can_upgrade_to_standard=(
            can_upgrade_to_standard
        ),

        can_upgrade_to_premium=(
            can_upgrade_to_premium
        ),

        can_renew_standard=(
            can_renew_standard
        ),

        can_renew_premium=(
            can_renew_premium
        ),


        # ====================================================
        # RESTAURANT FEATURE PERMISSIONS
        # ====================================================

        can_use_reel=(
            can_use_reel
        ),

        can_use_gallery=(
            can_use_gallery
        ),

        can_use_opening_hours=(
            can_use_opening_hours
        ),

        can_receive_customer_experiences=(
            can_receive_customer_experiences
        ),

        can_use_stories=(
            can_use_stories
        ),

        can_view_analytics=(
            can_view_analytics
        ),
    )

# ============================================================
# CREATE RESTAURANT EXPERIENCE
# ============================================================


@app.route(
    "/experiences/new",
    methods=[
        "GET",
        "POST",
    ],
)
def create_restaurant_experience():

    # ========================================================
    # TAGGABLE RESTAURANTS
    # ========================================================
    #
    # Only restaurants that currently have the
    # customer_experiences capability should appear in the
    # public restaurant selector.
    #
    # Expected:
    #
    # FREE
    #     -> excluded
    #
    # STANDARD ACTIVE
    #     -> included
    #
    # STANDARD GRACE
    #     -> included
    #
    # PREMIUM ACTIVE
    #     -> included
    #
    # PREMIUM GRACE
    #     -> included
    #
    # AFTER 5-DAY GRACE
    #     -> subscription sync downgrades to Free
    #     -> excluded
    #
    # Operational hours are NOT part of this decision.
    # ========================================================

    restaurants = (
        get_taggable_restaurants()
    )


    # ========================================================
    # FORM RENDER HELPER
    # ========================================================

    def render_experience_form(
        preselected_restaurant=None,
    ):

        return render_template(
            "restaurant_experience_form.html",

            restaurants=restaurants,

            preselected_restaurant=(
                preselected_restaurant
            ),
        )


    # ========================================================
    # QR / PRESELECTED RESTAURANT
    # ========================================================
    #
    # A restaurant can be supplied through:
    #
    #     /experiences/new?restaurant_id=123
    #
    # This is useful for restaurant rating QR codes and direct
    # "Share Experience" links.
    #
    # IMPORTANT:
    #
    # Query-string input is never trusted.
    #
    # The restaurant must pass the same server-side plan and
    # availability rules as every other experience submission.
    # ========================================================

    preselected_restaurant = None


    preselected_restaurant_id = (
        request.args.get(
            "restaurant_id",
            type=int,
        )
    )


    if preselected_restaurant_id:

        possible_restaurant = (
            RestaurantAdvert.query

            .filter_by(
                id=preselected_restaurant_id
            )

            .first()
        )


        # ====================================================
        # PRESELECTED RESTAURANT DOES NOT EXIST
        # ====================================================

        if not possible_restaurant:

            flash(
                (
                    "This restaurant is not currently "
                    "available for customer experiences."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "create_restaurant_experience"
                )
            )


        # ====================================================
        # PLAN + AVAILABILITY CHECK
        # ====================================================
        #
        # This prevents a Free restaurant from bypassing the
        # restaurant selector with:
        #
        #     ?restaurant_id=<free-restaurant-id>
        #
        # It also handles expired paid plans.
        # ====================================================

        if not restaurant_can_receive_experience_posts(
            possible_restaurant
        ):

            flash(
                (
                    "This restaurant is not currently "
                    "accepting customer experiences."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "create_restaurant_experience"
                )
            )


        preselected_restaurant = (
            possible_restaurant
        )


    # ========================================================
    # GET
    # ========================================================
    #
    # At this point:
    #
    #     no restaurant selected
    #
    # OR
    #
    #     preselected restaurant has already passed the
    #     restaurant plan + availability checks.
    # ========================================================

    if request.method == "GET":

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # POST
    # ========================================================
    #
    # IMPORTANT:
    #
    # Everything from the browser must be validated again.
    #
    # The GET checks are useful for UX.
    #
    # The POST restaurant eligibility check below is the
    # authoritative security check.
    # ========================================================


    # ========================================================
    # FORM VALUES
    # ========================================================

    poster_name = (
        request.form.get(
            "poster_name",
            "",
        )
        .strip()
    )


    rating_raw = (
        request.form.get(
            "rating",
            "",
        )
        .strip()
    )


    experience_text = (
        request.form.get(
            "experience_text",
            "",
        )
        .strip()
    )


    restaurant_advert_id = (
        request.form.get(
            "restaurant_advert_id",
            type=int,
        )
    )


    # ========================================================
    # RATING
    # ========================================================

    try:

        rating = int(
            rating_raw
        )

    except (
        TypeError,
        ValueError,
    ):

        rating = 0


    if rating not in {
        1,
        2,
        3,
        4,
        5,
    }:

        flash(
            (
                "Please choose a rating "
                "between 1 and 5 stars."
            ),
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # MULTIPLE MEDIA FILES
    # ========================================================

    media_files = [

        media

        for media
        in request.files.getlist(
            "experience_media"
        )

        if (
            media
            and
            media.filename
        )
    ]


    # ========================================================
    # NAME
    # ========================================================

    if not poster_name:

        flash(
            "Enter your name.",
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    if (
        len(
            poster_name
        )
        > 120
    ):

        flash(
            (
                "Your name must be "
                "120 characters or fewer."
            ),
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # EXPERIENCE TEXT
    # ========================================================

    if not experience_text:

        flash(
            (
                "Tell us about your "
                "experience."
            ),
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    if (
        len(
            experience_text
        )
        > 2000
    ):

        flash(
            (
                "Your experience must be "
                "2,000 characters or fewer."
            ),
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # RESTAURANT REQUIRED
    # ========================================================

    if not restaurant_advert_id:

        flash(
            "Choose the restaurant you visited.",
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # LOAD SUBMITTED RESTAURANT
    # ========================================================
    #
    # Never trust the restaurant ID submitted by the form.
    #
    # The browser could be modified manually.
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=restaurant_advert_id
        )

        .first()
    )


    # ========================================================
    # RESTAURANT EXISTS
    # ========================================================

    if not advert:

        flash(
            (
                "The selected restaurant "
                "is not available."
            ),
            "error",
        )

        return redirect(
            url_for(
                "create_restaurant_experience"
            )
        )


    # ========================================================
    # RESTAURANT PLAN + AVAILABILITY ENFORCEMENT
    # ========================================================
    #
    # This is the authoritative server-side security check.
    #
    # FREE
    # --------------------------------------------------------
    #
    # Profile                     YES
    # Campaign                    YES
    # Reel / Discovery            YES
    #
    # Customer experiences        NO
    #
    #
    # STANDARD
    # --------------------------------------------------------
    #
    # Active                      YES
    # 5-day grace                 YES
    #
    #
    # PREMIUM
    # --------------------------------------------------------
    #
    # Active                      YES
    # 5-day grace                 YES
    #
    #
    # AFTER GRACE
    # --------------------------------------------------------
    #
    # sync_restaurant_subscription() inside the helper
    # converts the restaurant to Free.
    #
    # Submission is therefore rejected.
    #
    #
    # IMPORTANT:
    #
    # Operational hours are NOT checked here.
    # ========================================================

    if not restaurant_can_receive_experience_posts(
        advert
    ):

        flash(
            (
                "This restaurant is not currently "
                "available for customer experiences."
            ),
            "error",
        )

        return redirect(
            url_for(
                "create_restaurant_experience"
            )
        )


    # ========================================================
    # QR / PRESELECTED RESTAURANT SAFETY
    # ========================================================
    #
    # When the customer entered through a restaurant-specific
    # QR/direct link, they must not be able to change the
    # restaurant ID in the submitted HTML form.
    # ========================================================

    if (
        preselected_restaurant
        and
        advert.id
        !=
        preselected_restaurant.id
    ):

        abort(400)


    # ========================================================
    # MEDIA REQUIRED
    # ========================================================

    if not media_files:

        flash(
            (
                "Upload between 1 and 3 photos "
                "or one short reel."
            ),
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # DETERMINE MEDIA TYPES
    # ========================================================

    media_types = []


    for media in media_files:

        media_type = (
            get_restaurant_experience_media_type(
                media.filename
            )
        )


        if not media_type:

            flash(
                (
                    "Use JPG, JPEG, PNG or WebP "
                    "photos, or an MP4, MOV, M4V "
                    "or WebM reel."
                ),
                "error",
            )

            return render_experience_form(
                preselected_restaurant
            )


        media_types.append(
            media_type
        )


    image_count = (
        media_types.count(
            "image"
        )
    )


    video_count = (
        media_types.count(
            "video"
        )
    )


    # ========================================================
    # CANNOT MIX PHOTOS + VIDEO
    # ========================================================

    if (
        image_count > 0
        and
        video_count > 0
    ):

        flash(
            (
                "Choose either photos or a reel. "
                "Photos and video cannot be mixed "
                "in the same experience post."
            ),
            "error",
        )

        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # PHOTO RULE
    # ========================================================

    if image_count:

        if (
            image_count < 1
            or
            image_count > 3
        ):

            flash(
                (
                    "You can upload a maximum "
                    "of 3 photos."
                ),
                "error",
            )

            return render_experience_form(
                preselected_restaurant
            )


    # ========================================================
    # REEL RULE
    # ========================================================

    if video_count:

        if (
            video_count != 1
            or
            len(
                media_files
            )
            != 1
        ):

            flash(
                (
                    "Only one reel can be uploaded "
                    "per experience."
                ),
                "error",
            )

            return render_experience_form(
                preselected_restaurant
            )


    # ========================================================
    # VALIDATE FILE SIZES BEFORE UPLOAD
    # ========================================================

    prepared_media = []


    for (
        media_order,
        media,
    ) in enumerate(
        media_files
    ):

        media_type = (
            media_types[
                media_order
            ]
        )


        media.stream.seek(
            0,
            os.SEEK_END,
        )


        file_size = (
            media.stream.tell()
        )


        media.stream.seek(
            0
        )


        # ====================================================
        # IMAGE SIZE
        # ====================================================

        if (
            media_type
            == "image"
        ):

            if (
                file_size
                >
                RESTAURANT_POSTER_MAX_FILE_BYTES
            ):

                flash(
                    (
                        "Each photo must be "
                        "8 MB or smaller."
                    ),
                    "error",
                )

                return render_experience_form(
                    preselected_restaurant
                )


        # ====================================================
        # VIDEO SIZE
        # ====================================================

        else:

            if (
                file_size
                >
                EVENT_REEL_MAX_FILE_BYTES
            ):

                flash(
                    (
                        "The reel must be "
                        "80 MB or smaller."
                    ),
                    "error",
                )

                return render_experience_form(
                    preselected_restaurant
                )


        prepared_media.append(
            {
                "file":
                    media,

                "media_type":
                    media_type,

                "media_order":
                    media_order,

                "file_size":
                    file_size,
            }
        )


    # ========================================================
    # FINAL ELIGIBILITY CHECK BEFORE WRITING DATA
    # ========================================================
    #
    # The restaurant was checked above before media
    # validation.
    #
    # We check once more immediately before creating the
    # database record / uploading media.
    #
    # This keeps the final write path protected by the
    # RestaurantAdvert subscription capability.
    # ========================================================

    if not restaurant_can_receive_experience_posts(
        advert
    ):

        flash(
            (
                "This restaurant is no longer "
                "available for customer experiences."
            ),
            "error",
        )

        return redirect(
            url_for(
                "create_restaurant_experience"
            )
        )


    # ========================================================
    # CLOUDINARY + DATABASE
    # ========================================================

    uploaded_assets = []


    try:

        # ====================================================
        # CREATE EXPERIENCE POST
        # ====================================================

        experience_post = (
            RestaurantExperiencePost(

                restaurant_advert_id=(
                    advert.id
                ),

                poster_name=(
                    poster_name
                ),

                experience_text=(
                    experience_text
                ),

                rating=(
                    rating
                ),

                moderation_status=(
                    "pending"
                ),

                active=True,
            )
        )


        db.session.add(
            experience_post
        )


        # ====================================================
        # GET EXPERIENCE ID
        # ====================================================
        #
        # We need the ID before Cloudinary upload so the media
        # can be stored under the correct restaurant /
        # experience folder.
        # ====================================================

        db.session.flush()


        # ====================================================
        # UPLOAD MEDIA
        # ====================================================

        for item in prepared_media:

            media = (
                item[
                    "file"
                ]
            )


            media_type = (
                item[
                    "media_type"
                ]
            )


            media_order = (
                item[
                    "media_order"
                ]
            )


            file_size = (
                item[
                    "file_size"
                ]
            )


            resource_type = (

                "image"

                if media_type
                == "image"

                else "video"
            )


            upload_result = (
                cloudinary.uploader.upload(
                    media,

                    resource_type=(
                        resource_type
                    ),

                    folder=(
                        "kalxa/"
                        f"restaurants/{advert.id}/"
                        "customer-experiences/"
                        f"{experience_post.id}"
                    ),

                    use_filename=True,

                    unique_filename=True,

                    overwrite=False,
                )
            )


            uploaded_public_id = (
                upload_result.get(
                    "public_id"
                )
            )


            secure_url = (
                upload_result.get(
                    "secure_url"
                )
            )


            if (
                not uploaded_public_id
                or
                not secure_url
            ):

                raise RuntimeError(
                    (
                        "Cloudinary did not return "
                        "the uploaded media."
                    )
                )


            # =================================================
            # TRACK UPLOAD FOR ROLLBACK
            # =================================================

            uploaded_assets.append(
                {
                    "public_id":
                        uploaded_public_id,

                    "resource_type":
                        resource_type,
                }
            )


            duration_seconds = (
                None
            )


            thumbnail_url = (
                None
            )


            # =================================================
            # VIDEO VALIDATION
            # =================================================

            if (
                media_type
                == "video"
            ):

                duration_seconds = float(
                    upload_result.get(
                        "duration",
                        0,
                    )
                    or 0
                )


                if (
                    duration_seconds
                    <= 0
                ):

                    raise RuntimeError(
                        (
                            "Kalxa could not determine "
                            "the reel duration."
                        )
                    )


                if (
                    duration_seconds
                    >
                    EVENT_REEL_MAX_DURATION_SECONDS
                ):

                    raise ValueError(
                        (
                            "Customer experience reels "
                            "must be 30 seconds or shorter."
                        )
                    )


                # =============================================
                # VIDEO THUMBNAIL
                # =============================================

                thumbnail_url = (
                    cloudinary.CloudinaryVideo(
                        uploaded_public_id
                    )
                    .build_url(
                        resource_type="video",

                        format="jpg",

                        start_offset="1",

                        width=720,

                        crop="limit",

                        secure=True,
                    )
                )


            # =================================================
            # MEDIA DATABASE ROW
            # =================================================

            media_record = (
                RestaurantExperienceMedia(

                    post_id=(
                        experience_post.id
                    ),

                    media_type=(
                        media_type
                    ),

                    media_order=(
                        media_order
                    ),

                    cloudinary_public_id=(
                        uploaded_public_id
                    ),

                    media_url=(
                        secure_url
                    ),

                    thumbnail_url=(
                        thumbnail_url
                    ),

                    duration_seconds=(
                        duration_seconds
                    ),

                    width=(
                        upload_result.get(
                            "width"
                        )
                    ),

                    height=(
                        upload_result.get(
                            "height"
                        )
                    ),

                    file_bytes=(
                        upload_result.get(
                            "bytes"
                        )
                        or
                        file_size
                    ),
                )
            )


            db.session.add(
                media_record
            )


        # ====================================================
        # SAVE EVERYTHING
        # ====================================================

        db.session.commit()


    # ========================================================
    # VALIDATION / VIDEO FAILURE
    # ========================================================

    except ValueError as error:

        db.session.rollback()


        # ====================================================
        # CLOUDINARY CLEANUP
        # ====================================================

        for asset in uploaded_assets:

            try:

                cloudinary.uploader.destroy(
                    asset[
                        "public_id"
                    ],

                    resource_type=(
                        asset[
                            "resource_type"
                        ]
                    ),
                )

            except Exception:

                current_app.logger.exception(
                    (
                        "[Restaurant Experience] "
                        "Cloudinary cleanup failed "
                        "public_id=%s"
                    ),
                    asset[
                        "public_id"
                    ],
                )


        flash(
            str(
                error
            ),
            "error",
        )


        return render_experience_form(
            preselected_restaurant
        )


    # ========================================================
    # GENERAL FAILURE
    # ========================================================

    except Exception as error:

        db.session.rollback()


        # ====================================================
        # CLOUDINARY CLEANUP
        # ====================================================

        for asset in uploaded_assets:

            try:

                cloudinary.uploader.destroy(
                    asset[
                        "public_id"
                    ],

                    resource_type=(
                        asset[
                            "resource_type"
                        ]
                    ),
                )

            except Exception:

                current_app.logger.exception(
                    (
                        "[Restaurant Experience] "
                        "Cloudinary cleanup failed "
                        "public_id=%s"
                    ),
                    asset[
                        "public_id"
                    ],
                )


        current_app.logger.exception(
            (
                "[Restaurant Experience] "
                "Submission failed "
                "restaurant_id=%s "
                "error=%s"
            ),
            advert.id,
            error,
        )


        flash(
            (
                "Kalxa could not submit your "
                "experience. Please try again."
            ),
            "error",
        )


        # ====================================================
        # RETURN TO SAME RESTAURANT WHEN PRESELECTED
        # ====================================================

        if preselected_restaurant:

            return redirect(
                url_for(
                    "create_restaurant_experience",

                    restaurant_id=(
                        preselected_restaurant.id
                    ),
                )
            )


        return redirect(
            url_for(
                "create_restaurant_experience"
            )
        )


    # ========================================================
    # SUCCESS
    # ========================================================

    flash(
        (
            "Your experience was submitted. "
            "It will appear on Kalxa after review."
        ),
        "success",
    )


    return redirect(
        url_for(
            "restaurant_experience_thank_you",

            restaurant_id=(
                advert.id
            ),
        )
    )

# ============================================================
# RESTAURANT RATING QR - DOWNLOAD
# ============================================================

def sync_restaurant_subscription(
    advert,
):

    # ========================================================
    # RESTAURANT REQUIRED
    # ========================================================

    if not advert:
        return False


    # ========================================================
    # DOWNGRADE AFTER GRACE PERIOD
    # ========================================================

    changed = (
        advert
        .downgrade_expired_restaurant_plan_to_free()
    )


    if not changed:
        return False


    # ========================================================
    # SAVE DOWNGRADE
    # ========================================================

    try:

        db.session.commit()


        current_app.logger.info(
            (
                "[Restaurant Subscription] "
                "Restaurant automatically downgraded "
                "to Free after grace period "
                "advert_id=%s"
            ),
            advert.id,
        )


        return True


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Subscription] "
                "Automatic downgrade failed "
                "advert_id=%s "
                "error=%s"
            ),
            advert.id,
            error,
        )


        return False  

# ============================================================
# ADMIN - MANAGE RESTAURANT
# ============================================================


          
# ============================================================
# ADMIN - PAUSE RESTAURANT ADVERT
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/pause",
    methods=[
        "POST",
    ],
)
def admin_pause_restaurant(
    advert_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    organizer = (
        get_current_organizer()
    )


    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=
                advert_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    advert.active = False


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Pause] "
                "Failed advert_id=%s error=%s"
            ),
            advert.id,
            error,
        )


        flash(
            "Restaurant advert could not be paused.",
            "error",
        )


        return redirect(
            url_for(
                "admin_manage_restaurant",

                advert_id=
                    advert.id,
            )
        )


    flash(
        "Restaurant advert paused.",
        "success",
    )


    return redirect(
        url_for(
            "admin_manage_restaurant",

            advert_id=
                advert.id,
        )
    )


# ============================================================
# ADMIN - RESUME RESTAURANT ADVERT
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/resume",
    methods=[
        "POST",
    ],
)
def admin_resume_restaurant(
    advert_id,
):

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    subscription_auth = (
        require_restaurant_subscription()
    )


    if subscription_auth:
        return subscription_auth


    organizer = (
        get_current_organizer()
    )


    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=
                advert_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    now = (
        datetime.utcnow()
    )


    if (
        advert.ends_at
        and advert.ends_at <= now
    ):

        flash(
            (
                "This campaign has expired. "
                "Edit the campaign schedule "
                "before resuming it."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_manage_restaurant",

                advert_id=
                    advert.id,
            )
        )


    if (
        organizer.subscription_expires_at
        and advert.ends_at
        and advert.ends_at
        > organizer.subscription_expires_at
    ):

        flash(
            (
                "The campaign extends beyond "
                "your current subscription. "
                "Edit its schedule first."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_manage_restaurant",

                advert_id=
                    advert.id,
            )
        )


    advert.active = True


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Resume] "
                "Failed advert_id=%s error=%s"
            ),
            advert.id,
            error,
        )


        flash(
            "Restaurant advert could not be resumed.",
            "error",
        )


        return redirect(
            url_for(
                "admin_manage_restaurant",

                advert_id=
                    advert.id,
            )
        )


    flash(
        "Restaurant advert resumed.",
        "success",
    )


    return redirect(
        url_for(
            "admin_manage_restaurant",

            advert_id=
                advert.id,
        )
    )
# ============================================================
# ORGANIZER - RESTAURANT REEL
# ============================================================


# ============================================================
# RESTAURANT REEL
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/reel",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_restaurant_reel(
    advert_id,
):

    # ========================================================
    # ORGANIZER AUTHENTICATION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    # ========================================================
    # RESTAURANT ACCOUNT ACCESS
    # ========================================================
    #
    # IMPORTANT:
    #
    # This must NOT require the legacy Organizer/Event SaaS
    # subscription.
    #
    # Free restaurants are allowed to use Reels.
    # ========================================================

    subscription_auth = (
        require_restaurant_subscription()
    )


    if subscription_auth:
        return subscription_auth


    organizer = (
        get_current_organizer()
    )


    if not organizer:

        flash(
            "Organizer account could not be found.",
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # ORGANIZER ACTIVE
    # ========================================================

    if not organizer.active:

        flash(
            "Your organizer account is inactive.",
            "error",
        )

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # RESTAURANT ACCOUNT TYPE
    # ========================================================

    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(403)


    # ========================================================
    # RESTAURANT + OWNERSHIP
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
            organizer_id=organizer.id,
        )

        .first_or_404()
    )


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # Free:
    #     Reel available.
    #
    # Standard:
    #     Reel available.
    #
    # Premium:
    #     Reel available.
    #
    # Paid grace expired:
    #     restaurant may be downgraded to Free,
    #     but Reel remains available because Free has Reel.
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # REEL CAPABILITY
    # ========================================================
    #
    # This is the RestaurantAdvert capability boundary.
    #
    # Do NOT use:
    #
    #     organizer.is_subscription_active
    #
    # Do NOT use:
    #
    #     organizer.subscription_expires_at
    # ========================================================

    if not advert.can_use_reel:

        abort(403)


    # ========================================================
    # EXISTING REEL
    # ========================================================

    reel = (
        RestaurantReel.query

        .filter_by(
            advert_id=advert.id,
            organizer_id=organizer.id,
        )

        .first()
    )


    # ========================================================
    # POST - UPLOAD / REPLACE
    # ========================================================

    if request.method == "POST":

        # ====================================================
        # RE-SYNC BEFORE MUTATION
        # ====================================================
        #
        # The form may have been open for some time.
        #
        # Always verify the current RestaurantAdvert
        # capability again before accepting the upload.
        # ====================================================

        sync_restaurant_subscription(
            advert
        )


        if not advert.can_use_reel:

            abort(403)


        # ====================================================
        # CLOUDINARY
        # ====================================================

        if not cloudinary_reels_configured():

            flash(
                (
                    "Restaurant Reel storage "
                    "is not configured yet."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_restaurant_reel",

                    advert_id=(
                        advert.id
                    ),
                )
            )


        # ====================================================
        # VIDEO
        # ====================================================

        video = (
            request.files.get(
                "reel_video"
            )
        )


        if (
            not video
            or
            not video.filename
        ):

            flash(
                "Choose a video to upload.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_restaurant_reel",

                    advert_id=(
                        advert.id
                    ),
                )
            )


        # ====================================================
        # VIDEO TYPE
        # ====================================================

        if not allowed_event_reel_filename(
            video.filename
        ):

            flash(
                (
                    "Use an MP4, MOV, M4V "
                    "or WebM video."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_restaurant_reel",

                    advert_id=(
                        advert.id
                    ),
                )
            )


        # ====================================================
        # FILE SIZE
        # ====================================================

        video.stream.seek(
            0,
            os.SEEK_END,
        )


        file_size = (
            video.stream.tell()
        )


        video.stream.seek(
            0
        )


        if (
            file_size
            >
            EVENT_REEL_MAX_FILE_BYTES
        ):

            flash(
                (
                    "The reel is too large. "
                    "Maximum size is 80 MB."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_restaurant_reel",

                    advert_id=(
                        advert.id
                    ),
                )
            )


        # ====================================================
        # CLOUDINARY TRACKING
        # ====================================================

        uploaded_public_id = None

        old_public_id = None


        try:

            # =================================================
            # CLOUDINARY VIDEO UPLOAD
            # =================================================

            upload_result = (
                cloudinary.uploader.upload(
                    video,

                    resource_type="video",

                    folder=(
                        "kalxa/"
                        f"organizers/{organizer.id}/"
                        f"restaurants/{advert.id}/"
                        "reels"
                    ),

                    use_filename=True,

                    unique_filename=True,

                    overwrite=False,
                )
            )


            uploaded_public_id = (
                upload_result.get(
                    "public_id"
                )
            )


            secure_url = (
                upload_result.get(
                    "secure_url"
                )
            )


            duration_seconds = (
                float(
                    upload_result.get(
                        "duration",
                        0,
                    )
                    or 0
                )
            )


            if (
                not uploaded_public_id
                or
                not secure_url
            ):

                raise RuntimeError(
                    (
                        "Cloudinary did not "
                        "return the uploaded video."
                    )
                )


            # =================================================
            # VALID DURATION
            # =================================================

            if (
                duration_seconds
                <= 0
            ):

                raise RuntimeError(
                    (
                        "Kalxa could not determine "
                        "the reel duration."
                    )
                )


            # =================================================
            # MAXIMUM 30 SECONDS
            # =================================================

            if (
                duration_seconds
                >
                EVENT_REEL_MAX_DURATION_SECONDS
            ):

                try:

                    delete_cloudinary_reel(
                        uploaded_public_id
                    )

                finally:

                    uploaded_public_id = None


                flash(
                    (
                        "Restaurant Reels must "
                        "be 30 seconds or shorter."
                    ),
                    "error",
                )


                return redirect(
                    url_for(
                        "admin_restaurant_reel",

                        advert_id=(
                            advert.id
                        ),
                    )
                )


            # =================================================
            # THUMBNAIL
            # =================================================

            thumbnail_url = (
                cloudinary.CloudinaryVideo(
                    uploaded_public_id
                )

                .build_url(
                    resource_type="video",

                    format="jpg",

                    start_offset="1",

                    width=720,

                    crop="limit",

                    secure=True,
                )
            )


            # =================================================
            # EXISTING CLOUDINARY VIDEO
            # =================================================

            old_public_id = (
                reel.cloudinary_public_id

                if reel

                else None
            )


            # =================================================
            # CREATE REEL
            # =================================================

            if reel is None:

                reel = (
                    RestaurantReel(

                        advert_id=(
                            advert.id
                        ),

                        organizer_id=(
                            organizer.id
                        ),

                        cloudinary_public_id=(
                            uploaded_public_id
                        ),

                        video_url=(
                            secure_url
                        ),

                        thumbnail_url=(
                            thumbnail_url
                        ),

                        duration_seconds=(
                            duration_seconds
                        ),

                        width=(
                            upload_result.get(
                                "width"
                            )
                        ),

                        height=(
                            upload_result.get(
                                "height"
                            )
                        ),

                        file_bytes=(
                            upload_result.get(
                                "bytes"
                            )
                        ),

                        active=True,
                    )
                )


                db.session.add(
                    reel
                )


            # =================================================
            # REPLACE EXISTING REEL
            # =================================================

            else:

                reel.cloudinary_public_id = (
                    uploaded_public_id
                )


                reel.video_url = (
                    secure_url
                )


                reel.thumbnail_url = (
                    thumbnail_url
                )


                reel.duration_seconds = (
                    duration_seconds
                )


                reel.width = (
                    upload_result.get(
                        "width"
                    )
                )


                reel.height = (
                    upload_result.get(
                        "height"
                    )
                )


                reel.file_bytes = (
                    upload_result.get(
                        "bytes"
                    )
                )


                reel.active = True


            # =================================================
            # SAVE
            # =================================================

            db.session.commit()


            # =================================================
            # REMOVE OLD CLOUDINARY VIDEO
            # ========================================================
            #
            # Only remove the previous Reel after the new
            # database state has committed successfully.
            # =================================================

            if (
                old_public_id
                and
                old_public_id
                != uploaded_public_id
            ):

                try:

                    delete_cloudinary_reel(
                        old_public_id
                    )

                except Exception:

                    current_app.logger.exception(
                        (
                            "[Restaurant Reel] "
                            "Old Cloudinary video "
                            "could not be removed."
                        )
                    )


            # =================================================
            # SUCCESS
            # =================================================

            flash(
                (
                    "Restaurant Reel published "
                    "successfully."
                ),
                "success",
            )


            return redirect(
                url_for(
                    "admin_restaurant_reel",

                    advert_id=(
                        advert.id
                    ),
                )
            )


        except Exception as error:

            # =================================================
            # DATABASE ROLLBACK
            # =================================================

            db.session.rollback()


            # =================================================
            # CLEAN NEW CLOUDINARY VIDEO
            # =================================================

            if uploaded_public_id:

                try:

                    delete_cloudinary_reel(
                        uploaded_public_id
                    )

                except Exception:

                    current_app.logger.exception(
                        (
                            "[Restaurant Reel] "
                            "Failed cleanup after "
                            "upload error."
                        )
                    )


            # =================================================
            # LOG ERROR
            # =================================================

            current_app.logger.exception(
                (
                    "[Restaurant Reel] "
                    "Upload failed "
                    "advert_id=%s "
                    "organizer_id=%s "
                    "error=%s"
                ),
                advert.id,
                organizer.id,
                error,
            )


            # =================================================
            # USER MESSAGE
            # =================================================

            flash(
                (
                    "Kalxa could not upload this "
                    "restaurant reel. "
                    "Please try again."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_restaurant_reel",

                    advert_id=(
                        advert.id
                    ),
                )
            )


    # ========================================================
    # GET
    # ========================================================

    return render_template(
        "admin/restaurant_reel.html",

        organizer=(
            organizer
        ),

        advert=(
            advert
        ),

        reel=(
            reel
        ),

        # ====================================================
        # RESTAURANT PLAN INFORMATION
        # ====================================================

        restaurant_plan=(
            advert.normalized_subscription_tier
        ),

        restaurant_plan_name=(
            advert.subscription_plan_name
        ),

        can_use_reel=(
            advert.can_use_reel
        ),
    )

# ============================================================
# RESTAURANT EXPERIENCE POSTS
# ============================================================
#
# Public customer-generated content.
#
# Users do NOT need a Kalxa account.
#
# Supported media:
#
# - image
# - short video / reel
#
# Images use the same 8 MB limit as restaurant posters.
# Videos use the same 80 MB / 30 second limits as event reels.
# ============================================================


# ============================================================
# EXPERIENCE MEDIA TYPE
# ============================================================

def get_restaurant_experience_media_type(
    filename,
):

    filename = (
        str(
            filename
            or ""
        )
        .strip()
        .lower()
    )


    if (
        "." not in filename
    ):

        return None


    extension = (
        filename
        .rsplit(
            ".",
            1,
        )[1]
    )


    if (
        extension
        in RESTAURANT_EXPERIENCE_IMAGE_EXTENSIONS
    ):

        return "image"


    if (
        extension
        in RESTAURANT_EXPERIENCE_VIDEO_EXTENSIONS
    ):

        return "video"


    return None


# ============================================================
# ANONYMOUS EXPERIENCE SESSION
# ============================================================
#
# Used for ❤️ loves.
#
# No Kalxa account is required.
#
# The random identifier is stored inside the user's Flask
# session cookie and does not contain their name, email
# or phone number.
# ============================================================

def get_restaurant_experience_session_id():

    session_key = (
        "kalxa_restaurant_experience_session"
    )


    anonymous_session_id = (
        session.get(
            session_key
        )
    )


    if not anonymous_session_id:

        anonymous_session_id = (
            secrets.token_urlsafe(
                32
            )
        )


        session[
            session_key
        ] = (
            anonymous_session_id
        )


    return anonymous_session_id




# ============================================================
# RESTAURANT TAGGING ELIGIBILITY
# ============================================================
#
# Final server-side permission check.
#
# Determines whether customers are allowed to:
#
# - select this restaurant in Share Experience
# - submit an experience for this restaurant
# - reach the Share Experience form through its QR code
#
# Restaurant plan rules:
#
# FREE:
#     customer experiences = NO
#
# STANDARD:
#     customer experiences = YES
#
# PREMIUM:
#     customer experiences = YES
#
# IMPORTANT:
#
# The restaurant dropdown is filtered by
# get_taggable_restaurants().
#
# This helper still performs the final security check because
# a user could manually submit a restaurant ID or manipulate
# the URL.
# ============================================================


    # ========================================================
    # ELIGIBLE
    # ========================================================


# ============================================================
# ORGANIZER - DELETE RESTAURANT REEL
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/reel/delete",
    methods=[
        "POST",
    ],
)
def admin_delete_restaurant_reel(
    advert_id,
):

    # ========================================================
    # ORGANIZER AUTH
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    # ========================================================
    # ACTIVE RESTAURANT SUBSCRIPTION REQUIRED
    # ========================================================

    subscription_auth = (
        require_restaurant_subscription()
    )


    if subscription_auth:
        return subscription_auth


    organizer = (
        get_current_organizer()
    )


    # ========================================================
    # OWNERSHIP
    # ========================================================

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=
                advert_id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    reel = (
        RestaurantReel.query
        .filter_by(
            advert_id=
                advert.id,

            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    public_id = (
        reel.cloudinary_public_id
    )


    # ========================================================
    # DELETE DATABASE RECORD
    # ========================================================

    try:

        db.session.delete(
            reel
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Reel Delete] "
                "Failed "
                "organizer_id=%s "
                "advert_id=%s "
                "error=%s"
            ),
            organizer.id,
            advert.id,
            error,
        )


        flash(
            (
                "Unable to remove the "
                "restaurant reel."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_restaurant_reel",

                advert_id=
                    advert.id,
            )
        )


    # ========================================================
    # DELETE CLOUDINARY VIDEO
    # ========================================================

    if public_id:

        try:

            delete_cloudinary_reel(
                public_id
            )


        except Exception as error:

            current_app.logger.warning(
                (
                    "[Restaurant Reel Delete] "
                    "Database reel was removed, "
                    "but Cloudinary cleanup failed "
                    "public_id=%s "
                    "error=%s"
                ),
                public_id,
                error,
            )


    # ========================================================
    # SUCCESS
    # ========================================================

    flash(
        "Restaurant Reel removed.",
        "success",
    )


    return redirect(
        url_for(
            "admin_restaurants"
        )
    )
# ============================================================
# PUBLIC ATTENDEE - ENABLE PUSH FROM HOME PAGE
# ============================================================

# ============================================================
# STAGE 6 - RESTAURANT EXPERIENCE VIEW ANALYTICS
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

    # ========================================================
    # ALREADY LOGGED IN
    # ========================================================

    existing_organizer = (
        get_current_organizer()
    )


    if existing_organizer:

        return redirect(
            url_for(
                organizer_home_endpoint(
                    existing_organizer
                )
            )
        )


    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    if request.method == "POST":

        # ====================================================
        # ACCOUNT TYPE
        # ====================================================

        account_type = (
            request.form.get(
                "account_type",
                "",
            )
            .strip()
            .lower()
        )


        if account_type not in {
            "event",
            "restaurant",
        }:

            flash(
                (
                    "Choose whether you are "
                    "creating an Event or "
                    "Restaurant account."
                ),
                "error",
            )

            return render_template(
                "organizer/signup.html"
            )


        # ====================================================
        # NAME
        # ====================================================

        name = (
            request.form.get(
                "name",
                "",
            )
            .strip()
        )


        # ====================================================
        # BUSINESS / BRAND NAME
        # ====================================================

        business_name = (
            request.form.get(
                "business_name",
                "",
            )
            .strip()
            or None
        )


        # ====================================================
        # EMAIL
        # ====================================================

        email = (
            normalize_email(
                request.form.get(
                    "email",
                    "",
                )
            )
        )


        # ====================================================
        # PHONE
        # ====================================================

        phone = (
            request.form.get(
                "phone",
                "",
            )
            .strip()
            or None
        )


        # ====================================================
        # PASSWORD
        # ====================================================

        password = (
            request.form.get(
                "password",
                "",
            )
        )


        password_confirm = (
            request.form.get(
                "password_confirm",
                "",
            )
        )


        # ====================================================
        # REQUIRED FIELDS
        # ====================================================

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


        # ====================================================
        # PASSWORD LENGTH
        # ====================================================

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


        # ====================================================
        # PASSWORD CONFIRMATION
        # ====================================================

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


        # ====================================================
        # EXISTING EMAIL
        # ====================================================

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
                    "An account already exists "
                    "with that email."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "organizer_login"
                )
            )


        # ====================================================
        # CREATE ORGANIZER
        # ====================================================
        #
        # IMPORTANT:
        #
        # account_type is stored explicitly.
        #
        # event
        # restaurant
        #
        # This prevents restaurant accounts from falling back
        # to the Organizer model's default "event" value.
        # ====================================================

        organizer = (
            Organizer(
                name=
                    name,

                business_name=
                    business_name,

                email=
                    email,

                phone=
                    phone,

                account_type=
                    account_type,

                active=
                    True,
            )
        )


        organizer.set_password(
            password
        )


        # ====================================================
        # SAVE
        # ====================================================

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
                    "email=%s "
                    "account_type=%s "
                    "error=%s"
                ),
                email,
                account_type,
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


        # ====================================================
        # SUCCESS
        # ====================================================

        session.clear()


        if (
            account_type
            == "restaurant"
        ):

            flash(
                (
                    "Restaurant advertiser account "
                    "created successfully. "
                    "Please sign in."
                ),
                "success",
            )

        else:

            flash(
                (
                    "Event organizer account "
                    "created successfully. "
                    "Please sign in."
                ),
                "success",
            )


        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # GET
    # ========================================================

    return render_template(
        "organizer/signup.html"
    )



def get_current_organizer():

    # ========================================================
    # ORGANIZER SESSION ID
    # ========================================================

    organizer_id = (
        session.get(
            ORGANIZER_SESSION_KEY
        )
    )


    if not organizer_id:

        return None


    # ========================================================
    # VALIDATE ORGANIZER ID
    # ========================================================

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


    # ========================================================
    # LOAD ORGANIZER
    # ========================================================

    organizer = (
        db.session.get(
            Organizer,
            organizer_id,
        )
    )


    # ========================================================
    # VALIDATE ORGANIZER
    # ========================================================

    if (
        not organizer
        or not organizer.active
    ):

        session.pop(
            ORGANIZER_SESSION_KEY,
            None,
        )

        return None


    # ========================================================
    # NORMALIZE ACCOUNT TYPE
    # ========================================================
    #
    # Existing database records may pre-date restaurant
    # accounts or contain inconsistent capitalization /
    # whitespace.
    #
    # Valid application values:
    #
    # event
    # restaurant
    #
    # IMPORTANT:
    # We do NOT automatically convert "event" to "restaurant".
    # That decision must come from the stored account record.
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    account_type = (
        str(
            account_type
        )
        .strip()
        .lower()
    )


    if account_type not in {
        "event",
        "restaurant",
    }:

        account_type = (
            "event"
        )


    organizer.account_type = (
        account_type
    )


    return organizer
# ============================================================
# ORGANIZER LOGIN
# ============================================================
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

    # ========================================================
    # ALREADY LOGGED IN
    # ========================================================

    existing_organizer = (
        get_current_organizer()
    )


    if existing_organizer:

        return redirect(
            url_for(
                organizer_home_endpoint(
                    existing_organizer
                )
            )
        )


    # ========================================================
    # LOGIN
    # ========================================================

    if request.method == "POST":

        email = (
            normalize_email(
                request.form.get(
                    "email",
                    "",
                )
            )
        )


        password = (
            request.form.get(
                "password",
                "",
            )
        )


        # ====================================================
        # FIND ORGANIZER
        # ====================================================

        organizer = (
            Organizer.query
            .filter_by(
                email=email
            )
            .first()
        )


        # ====================================================
        # SAFE ACCOUNT TYPE
        #
        # Existing deployments/accounts that do not yet expose
        # account_type are treated as event accounts.
        # ====================================================

        account_type = (
            getattr(
                organizer,
                "account_type",
                None,
            )
            or "event"
        )


        # ====================================================
        # VERIFY PASSWORD
        # ====================================================

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
                "email=%s "
                "found=%s "
                "active=%s "
                "account_type=%s "
                "password_ok=%s"
            ),
            email,
            organizer is not None,
            (
                organizer.active
                if organizer
                else None
            ),
            account_type,
            password_ok,
        )


        # ====================================================
        # INVALID LOGIN
        # ====================================================

        if not password_ok:

            flash(
                "Invalid email or password.",
                "error",
            )


            return render_template(
                "organizer/login.html"
            )


        # ====================================================
        # PRESERVE EXISTING KALXA BRIDGE SESSION VALUES
        # ====================================================

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


        # ====================================================
        # START CLEAN ORGANIZER SESSION
        # ====================================================

        session.clear()


        session[
            ORGANIZER_SESSION_KEY
        ] = organizer.id


        session.permanent = True


        current_app.logger.info(
            (
                "[Organizer Login] authenticated "
                "organizer_id=%s "
                "account_type=%s "
                "session_key=%s"
            ),
            organizer.id,
            account_type,
            session.get(
                ORGANIZER_SESSION_KEY
            ),
        )


        # ====================================================
        # RESTORE BRIDGE SESSION VALUES
        # ====================================================

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


        # ====================================================
        # CONNECT DISCOVERY ORGANIZER WHEN NEEDED
        # ====================================================

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


            except Exception as error:

                db.session.rollback()


                current_app.logger.exception(
                    (
                        "[Organizer Login] "
                        "Unable to connect discovery "
                        "organizer_id=%s error=%s"
                    ),
                    organizer.id,
                    error,
                )


        # ====================================================
        # SUCCESS MESSAGE
        # ====================================================

        if (
            account_type
            == "restaurant"
        ):

            flash(
                (
                    "Welcome back to your "
                    "Kalxa Restaurant dashboard."
                ),
                "success",
            )

        else:

            flash(
                (
                    "Welcome back to your "
                    "Kalxa Event dashboard."
                ),
                "success",
            )


        # ====================================================
        # ACCOUNT-TYPE REDIRECT
        # ====================================================

        return redirect(
            url_for(
                organizer_home_endpoint(
                    organizer
                )
            )
        )


    # ========================================================
    # GET
    # ========================================================

    return render_template(
        "organizer/login.html"
    )




# ============================================================
# ORGANIZER - FORGOT PASSWORD
# ============================================================

@app.route(
    "/organizer/forgot-password",
    methods=[
        "GET",
        "POST",
    ],
)
def organizer_forgot_password():

    if request.method == "POST":

        email = (
            normalize_email(
                request.form.get(
                    "email",
                    "",
                )
            )
        )


        if not email:

            flash(
                "Enter your email address.",
                "error",
            )


            return render_template(
                "organizer/forgot_password.html"
            )


        organizer = (
            Organizer.query
            .filter_by(
                email=email
            )
            .first()
        )


        # ====================================================
        # IMPORTANT:
        #
        # We intentionally give the same public response
        # whether the email exists or not.
        #
        # This prevents account/email enumeration.
        # ====================================================

        if organizer:

            try:

                token = (
                    create_organizer_password_reset_token(
                        organizer
                    )
                )


                reset_url = (
                    url_for(
                        "organizer_reset_password",

                        token=
                            token,

                        _external=
                            True,
                    )
                )


                send_organizer_password_reset_email(
                    organizer,
                    reset_url,
                )


                current_app.logger.info(
                    (
                        "[Password Reset] "
                        "Reset email sent "
                        "organizer_id=%s"
                    ),
                    organizer.id,
                )


            except Exception as error:

                current_app.logger.exception(
                    (
                        "[Password Reset] "
                        "Unable to send reset email "
                        "organizer_id=%s "
                        "error=%s"
                    ),
                    organizer.id,
                    error,
                )


        flash(
            (
                "If an account exists for that "
                "email address, a password-reset "
                "link has been sent."
            ),
            "success",
        )


        return redirect(
            url_for(
                "organizer_forgot_password"
            )
        )


    return render_template(
        "organizer/forgot_password.html"
    )


# ============================================================
# ORGANIZER - RESET PASSWORD
# ============================================================

@app.route(
    "/organizer/reset-password/<token>",
    methods=[
        "GET",
        "POST",
    ],
)
def organizer_reset_password(
    token,
):

    organizer, token_error = (
        verify_organizer_password_reset_token(
            token
        )
    )


    # ========================================================
    # INVALID / EXPIRED TOKEN
    # ========================================================

    if not organizer:

        if (
            token_error
            == "expired"
        ):

            flash(
                (
                    "That password-reset link "
                    "has expired. "
                    "Request a new one."
                ),
                "error",
            )

        else:

            flash(
                (
                    "That password-reset link "
                    "is invalid. "
                    "Request a new one."
                ),
                "error",
            )


        return redirect(
            url_for(
                "organizer_forgot_password"
            )
        )


    # ========================================================
    # SET NEW PASSWORD
    # ========================================================

    if request.method == "POST":

        password = (
            request.form.get(
                "password",
                "",
            )
        )


        password_confirm = (
            request.form.get(
                "password_confirm",
                "",
            )
        )


        if (
            not password
            or not password_confirm
        ):

            flash(
                (
                    "Enter and confirm "
                    "your new password."
                ),
                "error",
            )


            return render_template(
                "organizer/reset_password.html",

                token=
                    token,

                organizer=
                    organizer,
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
                "organizer/reset_password.html",

                token=
                    token,

                organizer=
                    organizer,
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
                "organizer/reset_password.html",

                token=
                    token,

                organizer=
                    organizer,
            )


        try:

            organizer.set_password(
                password
            )


            db.session.commit()


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Password Reset] "
                    "Unable to reset password "
                    "organizer_id=%s "
                    "error=%s"
                ),
                organizer.id,
                error,
            )


            flash(
                (
                    "Your password could not "
                    "be updated. Please try again."
                ),
                "error",
            )


            return render_template(
                "organizer/reset_password.html",

                token=
                    token,

                organizer=
                    organizer,
            )


        # ====================================================
        # REMOVE EXISTING LOGIN SESSION
        # ====================================================

        session.clear()


        flash(
            (
                "Your password has been updated. "
                "You can now sign in."
            ),
            "success",
        )


        return redirect(
            url_for(
                "organizer_login"
            )
        )


    return render_template(
        "organizer/reset_password.html",

        token=
            token,

        organizer=
            organizer,
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
# PUBLIC RESTAURANT PAGE
# ============================================================

# ============================================================
# PUBLIC - RESTAURANT PAGE
# ============================================================
#
# Restaurant plan behaviour:
#
# FREE
# ------------------------------------------------------------
# Profile                 YES
# Contact details         YES
# Gallery                 NO  -> template enforcement next
# Operational hours       NO
# Customer experiences    NO
# Stories                 NO
# Analytics dashboard     NO
#
# STANDARD
# ------------------------------------------------------------
# Profile                 YES
# Contact details         YES
# Gallery                 YES
# Operational hours       YES
# Customer experiences    YES
# Stories                 NO
# Analytics dashboard     NO
#
# PREMIUM
# ------------------------------------------------------------
# Profile                 YES
# Contact details         YES
# Gallery                 YES
# Operational hours       YES
# Customer experiences    YES
# Stories                 YES
# Analytics dashboard     YES
#
# IMPORTANT:
#
# Existing database rows are NOT deleted when a restaurant
# downgrades.
#
# Instead, paid features are hidden while the restaurant is
# on a plan that does not permit them.
#
# Example:
#
# Premium -> Free
#
# Existing gallery images, hours and customer experiences stay
# in the database but are no longer exposed publicly.
#
# If the restaurant upgrades again, the existing content can
# become available again.
# ============================================================
@app.route(
    "/restaurant/<int:advert_id>"
)
def restaurant_page(
    advert_id,
):

    # ========================================================
    # RESTAURANT
    # ========================================================
    #
    # The RestaurantAdvert itself remains available on every
    # restaurant plan, including Free.
    #
    # Restaurant plan permissions determine which additional
    # features are exposed on the public profile.
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=advert_id,
            active=True,
        )

        .first_or_404()
    )


    # ========================================================
    # SYNCHRONIZE RESTAURANT SUBSCRIPTION
    # ========================================================
    #
    # FREE
    #     -> always active
    #     -> profile/campaign/reel available
    #
    # STANDARD / PREMIUM ACTIVE
    #     -> paid features available
    #
    # STANDARD / PREMIUM EXPIRED <= 5 DAYS
    #     -> grace period
    #     -> paid features remain available
    #
    # STANDARD / PREMIUM EXPIRED > 5 DAYS
    #     -> automatically converted to Free
    #     -> paid content remains stored
    #     -> paid content is no longer exposed
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    now = (
        datetime.utcnow()
    )


    # ========================================================
    # ORGANIZER / ACCOUNT SAFETY
    # ========================================================
    #
    # IMPORTANT:
    #
    # Public restaurant visibility does NOT depend on:
    #
    #     organizer.is_subscription_active
    #
    # That property belongs to the legacy Organizer/Event SaaS
    # subscription system.
    #
    # A Free restaurant must remain publicly accessible.
    # ========================================================

    organizer = (
        advert.organizer
    )


    if not organizer:

        abort(404)


    if not organizer.active:

        abort(404)


    if (
        getattr(
            organizer,
            "account_type",
            None,
        )
        != "restaurant"
    ):

        abort(404)


    # ========================================================
    # RESTAURANT PROFILE PERMISSION
    # ========================================================
    #
    # FREE       -> YES
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    can_use_profile = (
        advert.can_use_profile
    )


    if not can_use_profile:

        abort(404)


    # ========================================================
    # CAMPAIGN DATE SAFETY
    # ========================================================
    #
    # Campaign visibility is separate from operational hours.
    #
    # A Free restaurant is allowed to publish and display its
    # restaurant campaign even though regular operational
    # hours are unavailable on Free.
    # ========================================================

    if (
        advert.starts_at
        and
        advert.starts_at > now
    ):

        abort(404)


    if (
        advert.ends_at
        and
        advert.ends_at <= now
    ):

        abort(404)


    # ========================================================
    # RESTAURANT PLAN PERMISSIONS
    # ========================================================
    #
    # These values are calculated once and then used
    # throughout the route.
    #
    # FREE:
    #
    #     profile                 YES
    #     reel / campaign         YES
    #     gallery                 NO
    #     opening hours           NO
    #     customer experiences    NO
    #     stories                 NO
    #     analytics dashboard     NO
    #
    # STANDARD:
    #
    #     profile                 YES
    #     reel / campaign         YES
    #     gallery                 YES
    #     opening hours           YES
    #     customer experiences    YES
    #     stories                 NO
    #     analytics dashboard     NO
    #
    # PREMIUM:
    #
    #     all restaurant features
    # ========================================================

    can_use_reel = (
        advert.can_use_reel
    )


    can_use_gallery = (
        advert.can_use_gallery
    )


    can_use_opening_hours = (
        advert.can_use_opening_hours
    )


    can_receive_customer_experiences = (
        advert.can_receive_customer_experiences
    )


    can_use_stories = (
        advert.can_use_stories
    )


    can_view_analytics = (
        advert.can_view_analytics
    )


    # ========================================================
    # GRACE PERIOD INFORMATION
    # ========================================================

    restaurant_subscription_in_grace = (
        advert
        .is_restaurant_subscription_in_grace_period
    )


    restaurant_subscription_grace_ends_at = (
        advert
        .restaurant_subscription_grace_ends_at
    )


    # ========================================================
    # STORIES ATTRIBUTION
    # ========================================================
    #
    # Attribution tracking may still be captured when somebody
    # reaches the restaurant from another Kalxa surface.
    #
    # This does NOT grant Stories access.
    # Stories access remains controlled by:
    #
    #     can_use_stories
    # ========================================================

    restaurant_attribution = (
        capture_restaurant_attribution(
            advert
        )
    )


    # ========================================================
    # ANONYMOUS RESTAURANT SESSION
    # ========================================================

    anonymous_session_id = (
        get_restaurant_experience_session_id()
    )


    # ========================================================
    # RESTAURANT VIEW ANALYTICS EVENT
    # ========================================================
    #
    # IMPORTANT:
    #
    # We may still collect platform-level restaurant view
    # events for Kalxa internally.
    #
    # can_view_analytics controls whether the restaurant owner
    # can access the restaurant analytics product/dashboard.
    #
    # It does not need to stop Kalxa from collecting basic
    # platform telemetry.
    # ========================================================

    record_restaurant_analytics_event(
        restaurant_id=advert.id,

        event_type="restaurant_view",

        metadata={
            "page":
                "restaurant",

            "attributed":
                bool(
                    restaurant_attribution
                ),

            "restaurant_plan":
                advert.normalized_subscription_tier,

            "subscription_grace":
                restaurant_subscription_in_grace,
        },
    )


    # ========================================================
    # CUSTOMER EXPERIENCES
    # ========================================================
    #
    # FREE:
    #
    #     Do NOT load customer experience posts.
    #
    # STANDARD / PREMIUM:
    #
    #     Load approved customer experience posts.
    #
    # This is stronger than merely hiding the HTML section.
    # Free profiles do not even receive the experience records
    # in the Jinja template context.
    # ========================================================

    experience_posts = []


    if can_receive_customer_experiences:

        experience_posts = (
            RestaurantExperiencePost.query

            .filter_by(
                restaurant_advert_id=advert.id,
                active=True,
                moderation_status="approved",
            )

            .order_by(
                RestaurantExperiencePost
                .created_at
                .desc()
            )

            .all()
        )


    # ========================================================
    # RESTAURANT RATING SUMMARY
    # ========================================================
    #
    # Ratings come from customer experience posts.
    #
    # Therefore Free restaurants must not expose a rating
    # summary from stored paid-plan experience data.
    # ========================================================

    restaurant_rating_count = (
        0
    )


    restaurant_average_rating = (
        None
    )


    if can_receive_customer_experiences:

        restaurant_ratings = [

            post.rating

            for post
            in experience_posts

            if post.rating is not None
        ]


        restaurant_rating_count = (
            len(
                restaurant_ratings
            )
        )


        if restaurant_rating_count > 0:

            restaurant_average_rating = (
                sum(
                    restaurant_ratings
                )
                /
                restaurant_rating_count
            )


    # ========================================================
    # CUSTOMER EXPERIENCE LOVES
    # ========================================================
    #
    # No experience engagement data is loaded for Free.
    # ========================================================

    loved_experience_post_ids = (
        set()
    )


    if (
        can_receive_customer_experiences
        and
        experience_posts
    ):

        experience_post_ids = [

            post.id

            for post
            in experience_posts
        ]


        loved_experience_post_ids = {

            love.post_id

            for love
            in (
                RestaurantExperienceLove.query

                .filter(
                    RestaurantExperienceLove
                    .post_id
                    .in_(
                        experience_post_ids
                    )
                )

                .filter(
                    RestaurantExperienceLove
                    .anonymous_session_id
                    ==
                    anonymous_session_id
                )

                .all()
            )
        }


    # ========================================================
    # CONTACT LINKS
    # ========================================================
    #
    # Contact details belong to the basic restaurant profile.
    #
    # FREE       -> YES
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    raw_whatsapp_url = (
        build_restaurant_whatsapp_url(
            advert.whatsapp_number
        )
    )


    raw_phone_url = (
        build_restaurant_phone_url(
            advert.phone_number
        )
    )


    raw_directions_url = (
        valid_restaurant_directions_url(
            advert.directions_url
        )
    )


    whatsapp_url = (

        url_for(
            "restaurant_whatsapp_action",
            advert_id=advert.id,
        )

        if raw_whatsapp_url

        else None
    )


    phone_url = (

        url_for(
            "restaurant_phone_action",
            advert_id=advert.id,
        )

        if raw_phone_url

        else None
    )


    directions_url = (

        url_for(
            "restaurant_directions_action",
            advert_id=advert.id,
        )

        if raw_directions_url

        else None
    )


    # ========================================================
    # RESTAURANT HOURS
    # ========================================================
    #
    # FREE:
    #
    #     restaurant_hours_payload = None
    #
    # STANDARD / PREMIUM:
    #
    #     operational hours are loaded.
    #
    # IMPORTANT:
    #
    # Existing hours are NOT deleted when a restaurant falls
    # back to Free. They simply stop being exposed.
    #
    # If the restaurant upgrades again, the stored hours can
    # become available again.
    # ========================================================

    restaurant_hours_payload = (
        None
    )


    if can_use_opening_hours:

        restaurant_hours_payload = (
            build_restaurant_hours_payload(
                advert
            )
        )


    # ========================================================
    # CURRENT ORGANIZER
    # ========================================================

    current_organizer = (
        get_current_organizer()
    )


    current_organizer_id = (

        current_organizer.id

        if current_organizer

        else None
    )


    # ========================================================
    # RESTAURANT MANAGEMENT PERMISSION
    # ========================================================
    #
    # Free restaurant owners must still be able to manage:
    #
    #     profile
    #     contact information
    #     restaurant campaign
    #     main poster
    #     reel/discovery
    #
    # Ownership therefore does NOT depend on:
    #
    #     organizer.is_subscription_active
    # ========================================================

    can_manage_restaurant = (
        False
    )


    if (
        current_organizer_id
        and
        advert.organizer_id
        ==
        current_organizer_id
        and
        organizer.active
        and
        getattr(
            organizer,
            "account_type",
            None,
        )
        == "restaurant"
    ):

        can_manage_restaurant = (
            True
        )


    # ========================================================
    # HOURS MANAGEMENT
    # ========================================================
    #
    # FREE       -> NO
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    can_manage_restaurant_hours = (
        can_manage_restaurant
        and
        can_use_opening_hours
    )


    # ========================================================
    # RATING QR MANAGEMENT
    # ========================================================
    #
    # Rating QR exists to collect customer experiences.
    #
    # FREE       -> NO
    # STANDARD   -> YES
    # PREMIUM    -> YES
    # ========================================================

    can_manage_restaurant_rating_qr = (
        can_manage_restaurant
        and
        can_receive_customer_experiences
    )


    # ========================================================
    # RESTAURANT RATING QR
    # ========================================================
    #
    # Do not even load the QR record for a Free restaurant.
    #
    # This allows an expired paid restaurant's QR record to
    # remain safely stored without exposing it while the
    # restaurant is on Free.
    # ========================================================

    restaurant_rating_qr = (
        None
    )


    restaurant_rating_url = (
        ""
    )


    if can_manage_restaurant_rating_qr:

        restaurant_rating_qr = (
            RestaurantRatingQRCode.query

            .filter_by(
                restaurant_advert_id=advert.id,
                placement_type="main",
            )

            .order_by(
                RestaurantRatingQRCode
                .created_at
                .asc()
            )

            .first()
        )


        if restaurant_rating_qr:

            restaurant_rating_url = (
                url_for(
                    "restaurant_rating_qr_page",

                    public_code=(
                        restaurant_rating_qr
                        .public_code
                    ),

                    _external=True,
                )
            )


    # ========================================================
    # ATTRIBUTION VALUES
    # ========================================================

    attribution_source = (
        restaurant_attribution.get(
            "source"
        )

        if restaurant_attribution

        else None
    )


    source_article_id = (
        restaurant_attribution.get(
            "article_id"
        )

        if restaurant_attribution

        else None
    )


    source_restaurant_id = (
        restaurant_attribution.get(
            "restaurant_id"
        )

        if restaurant_attribution

        else None
    )


    source_session_id = (
        restaurant_attribution.get(
            "source_session_id"
        )

        if restaurant_attribution

        else None
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "restaurant.html",

        advert=advert,


        # ====================================================
        # RESTAURANT PLAN
        # ====================================================

        restaurant_plan=(
            advert.normalized_subscription_tier
        ),

        restaurant_plan_name=(
            advert.subscription_plan_name
        ),

        restaurant_plan_price=(
            advert.subscription_price
        ),

        restaurant_subscription_in_grace=(
            restaurant_subscription_in_grace
        ),

        restaurant_subscription_grace_ends_at=(
            restaurant_subscription_grace_ends_at
        ),


        # ====================================================
        # FEATURE CAPABILITIES
        # ====================================================

        can_use_profile=(
            can_use_profile
        ),

        can_use_reel=(
            can_use_reel
        ),

        can_use_gallery=(
            can_use_gallery
        ),

        can_use_opening_hours=(
            can_use_opening_hours
        ),

        can_receive_customer_experiences=(
            can_receive_customer_experiences
        ),

        can_use_stories=(
            can_use_stories
        ),

        can_view_analytics=(
            can_view_analytics
        ),


        # ====================================================
        # CONTACT
        # ====================================================

        whatsapp_url=(
            whatsapp_url
        ),

        phone_url=(
            phone_url
        ),

        directions_url=(
            directions_url
        ),


        # ====================================================
        # HOURS
        # ====================================================

        restaurant_hours_payload=(
            restaurant_hours_payload
        ),

        can_manage_restaurant=(
            can_manage_restaurant
        ),

        can_manage_restaurant_hours=(
            can_manage_restaurant_hours
        ),

        restaurant_hours_update_url=(

            url_for(
                "update_restaurant_hours",
                advert_id=advert.id,
            )

            if can_manage_restaurant_hours

            else ""
        ),


        # ====================================================
        # CUSTOMER EXPERIENCES
        # ====================================================

        experience_posts=(
            experience_posts
        ),

        loved_experience_post_ids=(
            loved_experience_post_ids
        ),

        restaurant_average_rating=(
            restaurant_average_rating
        ),

        restaurant_rating_count=(
            restaurant_rating_count
        ),


        # ====================================================
        # RATING QR
        # ====================================================

        can_manage_restaurant_rating_qr=(
            can_manage_restaurant_rating_qr
        ),

        restaurant_rating_qr=(
            restaurant_rating_qr
        ),

        restaurant_rating_url=(
            restaurant_rating_url
        ),

        restaurant_rating_qr_create_url=(

            url_for(
                "create_restaurant_rating_qr",
                advert_id=advert.id,
            )

            if can_manage_restaurant_rating_qr

            else ""
        ),


        # ====================================================
        # ATTRIBUTION
        # ====================================================

        attribution_source=(
            attribution_source
        ),

        source_article_id=(
            source_article_id
        ),

        source_restaurant_id=(
            source_restaurant_id
        ),

        source_session_id=(
            source_session_id
        ),
    )

# ============================================================
# STAGE 6 - WHATSAPP CONVERSION
# ============================================================

@app.route(
    "/restaurant/<int:advert_id>/action/whatsapp"
)
def restaurant_whatsapp_action(
    advert_id,
):

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=advert_id,
            active=True,
        )
        .first_or_404()
    )


    whatsapp_url = (
        build_restaurant_whatsapp_url(
            advert.whatsapp_number
        )
    )


    if not whatsapp_url:

        abort(404)


    record_restaurant_analytics_event(
        advert=advert,
        event_type="whatsapp_click",
        metadata={
            "action":
                "whatsapp",
        },
        deduplicate=False,
    )


    return redirect(
        whatsapp_url
    )


# ============================================================
# STAGE 6 - PHONE CONVERSION
# ============================================================

@app.route(
    "/restaurant/<int:advert_id>/action/phone"
)
def restaurant_phone_action(
    advert_id,
):

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=advert_id,
            active=True,
        )
        .first_or_404()
    )


    phone_url = (
        build_restaurant_phone_url(
            advert.phone_number
        )
    )


    if not phone_url:

        abort(404)


    record_restaurant_analytics_event(
        advert=advert,
        event_type="phone_click",
        metadata={
            "action":
                "phone",
        },
        deduplicate=False,
    )


    return redirect(
        phone_url
    )


# ============================================================
# STAGE 6 - DIRECTIONS CONVERSION
# ============================================================

@app.route(
    "/restaurant/<int:advert_id>/action/directions"
)
def restaurant_directions_action(
    advert_id,
):

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=advert_id,
            active=True,
        )
        .first_or_404()
    )


    directions_url = (
        valid_restaurant_directions_url(
            advert.directions_url
        )
    )


    if not directions_url:

        abort(404)


    record_restaurant_analytics_event(
        advert=advert,
        event_type="directions_click",
        metadata={
            "action":
                "directions",
        },
        deduplicate=False,
    )


    return redirect(
        directions_url
    )
# ============================================================
# CREATE / GET RESTAURANT RATING QR
# ============================================================




@app.route("/experiences/thank-you")
def restaurant_experience_thank_you():

    restaurant_id = request.args.get(
        "restaurant_id",
        type=int,
    )

    restaurant = None

    if restaurant_id:
        restaurant = (
            RestaurantAdvert.query
            .filter_by(id=restaurant_id)
            .first()
        )

    return render_template(
        "restaurant_experience_thank_you.html",
        restaurant=restaurant,
    )

# ============================================================
# PUBLIC RESTAURANT RATING QR PAGE
# ============================================================

# ============================================================
# PUBLIC RESTAURANT RATING QR
# ============================================================


# ============================================================
# RESTAURANT RATING QR HELPERS
# ============================================================


def generate_restaurant_rating_public_code():
    """
    Generate a short public Kalxa restaurant QR code.

    Example:

        KX-A7F92C4D

    The database ID is intentionally not exposed in the
    customer-facing QR URL.
    """

    while True:

        public_code = (
            "KX-"
            + secrets.token_hex(4).upper()
        )

        existing_qr = (
            RestaurantRatingQRCode.query
            .filter_by(
                public_code=public_code
            )
            .first()
        )

        if not existing_qr:
            return public_code


def get_or_create_restaurant_main_qr(
    advert,
):
    """
    Return the restaurant's permanent main QR record.

    If one does not exist yet, create it.

    The same restaurant should continue using the same QR
    instead of generating a different code every time the
    owner opens the page.
    """

    restaurant_qr = (
        RestaurantRatingQRCode.query

        .filter_by(
            restaurant_advert_id=
                advert.id,

            placement_type=
                "main",
        )

        .order_by(
            RestaurantRatingQRCode.created_at.asc()
        )

        .first()
    )


    if restaurant_qr:

        # If it was previously disabled, keep the existing
        # permanent code but activate it again.
        if not restaurant_qr.active:

            restaurant_qr.active = True

            db.session.commit()

        return restaurant_qr


    restaurant_qr = (
        RestaurantRatingQRCode(
            restaurant_advert_id=
                advert.id,

            public_code=
                generate_restaurant_rating_public_code(),

            placement_type=
                "main",

            placement_label=
                "Main restaurant QR",

            active=
                True,
        )
    )


    db.session.add(
        restaurant_qr
    )

    db.session.commit()


    return restaurant_qr


# ============================================================
# RESTAURANT EXPERIENCE VIEW ANALYTICS
# ============================================================

@app.route(
    (
        "/restaurant/<int:advert_id>"
        "/analytics/experience/"
        "<int:post_id>/view"
    ),
    methods=["POST"],
)
def restaurant_experience_view_analytics(
    advert_id,
    post_id,
):

    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=advert_id,
            active=True,
        )
        .first_or_404()
    )


    # ========================================================
    # EXPERIENCE POST
    #
    # Only approved, active experiences belonging to this
    # restaurant can generate an experience_view event.
    # ========================================================

    post = (
        RestaurantExperiencePost.query
        .filter_by(
            id=post_id,
            restaurant_advert_id=advert.id,
            active=True,
            moderation_status="approved",
        )
        .first_or_404()
    )


    # ========================================================
    # RECORD ANALYTICS
    #
    # Attribution already lives in the Ticketing session.
    #
    # If this visitor arrived from Kalxa Stories, the existing
    # record_restaurant_analytics_event() helper automatically
    # attaches:
    #
    # source = kalxa_stories
    # source_article_id
    # source_restaurant_id
    # source_session_id
    #
    # We keep the experience post ID inside event_metadata
    # because RestaurantAnalyticsEvent currently has no
    # dedicated experience_post_id column.
    # ========================================================

    recorded = (
        record_restaurant_analytics_event(
            restaurant_id=advert.id,
            event_type="experience_view",
            metadata={
                "experience_post_id":
                    post.id,
            },
            deduplicate=True,
        )
    )


    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify({
        "ok": True,

        "recorded":
            bool(
                recorded
            ),

        "event_type":
            "experience_view",

        "restaurant_id":
            advert.id,

        "experience_post_id":
            post.id,
    })
# ============================================================
# RESTAURANT RATING QR - PNG IMAGE
# ============================================================

@app.route(
    "/restaurant/<int:advert_id>/rating-qr.png"
)
def restaurant_rating_qr_image(
    advert_id,
):

    # ========================================================
    # ORGANIZER AUTHENTICATION
    # ========================================================

    current_organizer = (
        get_current_organizer()
    )


    if not current_organizer:

        abort(401)


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query

        .filter_by(
            id=
                advert_id
        )

        .first_or_404()
    )


    # ========================================================
    # OWNERSHIP
    # ========================================================

    if (
        advert.organizer_id
        !=
        current_organizer.id
    ):

        abort(403)


    # ========================================================
    # SUBSCRIPTION
    # ========================================================

    if (
        not advert.organizer
        or
        not advert.organizer.is_subscription_active
    ):

        abort(403)


    # ========================================================
    # GET OR CREATE PERMANENT QR
    # ========================================================

    restaurant_qr = (
        get_or_create_restaurant_main_qr(
            advert
        )
    )


    # ========================================================
    # PUBLIC QR DESTINATION
    # ========================================================

    rating_url = (
        url_for(
            "restaurant_rating_qr_page",

            public_code=
                restaurant_qr.public_code,

            _external=True,

            _scheme="https",
        )
    )


    # ========================================================
    # GENERATE QR
    # ========================================================

    qr = qrcode.QRCode(
        version=None,

        error_correction=
            qrcode.constants.ERROR_CORRECT_M,

        box_size=12,

        border=4,
    )


    qr.add_data(
        rating_url
    )


    qr.make(
        fit=True
    )


    qr_image = (
        qr.make_image(
            fill_color="black",
            back_color="white",
        )
    )


    # ========================================================
    # WRITE PNG INTO MEMORY
    # ========================================================

    image_buffer = (
        io.BytesIO()
    )


    qr_image.save(
        image_buffer,
        format="PNG",
    )


    image_buffer.seek(
        0
    )


    # ========================================================
    # DOWNLOAD FILE NAME
    # ========================================================

    safe_business_name = (
        "".join(
            character
            if (
                character.isalnum()
                or character in {
                    "-",
                    "_",
                }
            )
            else "-"
            for character
            in advert.business_name
        )
        .strip("-")
        .lower()
    )


    if not safe_business_name:

        safe_business_name = (
            f"restaurant-{advert.id}"
        )


    filename = (
        f"kalxa-{safe_business_name}-rating-qr.png"
    )


    # ========================================================
    # RETURN PNG
    # ========================================================

    return send_file(
        image_buffer,

        mimetype=
            "image/png",

        as_attachment=
            False,

        download_name=
            filename,

        max_age=
            0,
    )



# ============================================================
# KALXA INTERNAL ANALYTICS API
# ============================================================
#
# This API allows trusted Kalxa services such as
# Kalxa Stories to retrieve aggregated Ticketing conversion
# data.
#
# IMPORTANT:
#
# - This is NOT a public analytics endpoint.
# - It returns aggregate counts only.
# - It does NOT return session IDs.
# - It does NOT return source session IDs.
# - It does NOT return individual analytics events.
# ============================================================


KALXA_INTERNAL_API_KEY = (
    os.getenv(
        "KALXA_INTERNAL_API_KEY",
        "",
    )
    .strip()
)


# ============================================================
# VERIFY INTERNAL API KEY
# ============================================================

def kalxa_internal_api_authorized():
    """
    Verify that the request came from another trusted
    Kalxa service.

    The caller must send:

        X-Kalxa-Internal-Key: <secret>

    hmac.compare_digest() is used instead of normal string
    comparison.
    """

    configured_key = (
        KALXA_INTERNAL_API_KEY
    )


    if not configured_key:

        current_app.logger.error(
            "KALXA_INTERNAL_API_KEY "
            "is not configured."
        )

        return False


    supplied_key = (
        request.headers
        .get(
            "X-Kalxa-Internal-Key",
            "",
        )
        .strip()
    )


    if not supplied_key:

        return False


    return hmac.compare_digest(
        configured_key,
        supplied_key,
    )


# ============================================================
# PARSE STORY IDS
# ============================================================

def parse_internal_story_ids(
    raw_value,
):
    """
    Convert:

        1,2,3

    into:

        [1, 2, 3]

    Invalid values are ignored.

    A maximum of 100 story IDs is accepted per request.
    """

    if not raw_value:

        return []


    story_ids = []


    for raw_id in raw_value.split(","):

        raw_id = (
            raw_id.strip()
        )


        if not raw_id:

            continue


        try:

            story_id = int(
                raw_id
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        if story_id <= 0:

            continue


        if story_id in story_ids:

            continue


        story_ids.append(
            story_id
        )


        if len(
            story_ids
        ) >= 100:

            break


    return story_ids


# ============================================================
# PRIVATE RESTAURANT ANALYTICS
# ============================================================

@app.route(
    "/api/internal/restaurant-analytics",
    methods=["GET"],
)
def internal_restaurant_analytics():
    """
    Return aggregated Kalxa Ticketing restaurant analytics
    attributed to Kalxa Stories.

    Example request:

        /api/internal/restaurant-analytics
            ?story_ids=1,2,3

    Required header:

        X-Kalxa-Internal-Key: <secret>

    The endpoint intentionally returns aggregate data only.
    """


    # ========================================================
    # AUTHENTICATION
    # ========================================================

    if not kalxa_internal_api_authorized():

        return jsonify(
            {
                "ok": False,
                "error":
                    "unauthorized",
            }
        ), 401


    # ========================================================
    # STORY IDS
    # ========================================================

    story_ids = (
        parse_internal_story_ids(
            request.args.get(
                "story_ids",
                "",
            )
        )
    )


    if not story_ids:

        return jsonify(
            {
                "ok": False,
                "error":
                    "story_ids_required",
            }
        ), 400


    # ========================================================
    # SUPPORTED CONVERSION EVENTS
    # ========================================================

    supported_events = (
        "restaurant_view",
        "experience_view",
        "whatsapp_click",
        "phone_click",
        "directions_click",
    )


    # ========================================================
    # QUERY
    # ========================================================
    #
    # Only events carrying verified Kalxa Stories attribution
    # are included.
    #
    # Group by:
    #
    #     story
    #     restaurant
    #     event type
    #
    # This keeps the response small even when the underlying
    # event table eventually contains millions of events.
    # ========================================================

    rows = (
        db.session.query(

            RestaurantAnalyticsEvent
            .source_article_id
            .label(
                "story_id"
            ),

            RestaurantAnalyticsEvent
            .restaurant_id
            .label(
                "restaurant_id"
            ),

            RestaurantAnalyticsEvent
            .event_type
            .label(
                "event_type"
            ),

            db.func.count(
                RestaurantAnalyticsEvent.id
            )
            .label(
                "event_count"
            ),
        )

        .filter(
            RestaurantAnalyticsEvent.source
            == "kalxa_stories",

            RestaurantAnalyticsEvent
            .source_article_id
            .in_(
                story_ids
            ),

            RestaurantAnalyticsEvent
            .event_type
            .in_(
                supported_events
            ),
        )

        .group_by(
            RestaurantAnalyticsEvent
            .source_article_id,

            RestaurantAnalyticsEvent
            .restaurant_id,

            RestaurantAnalyticsEvent
            .event_type,
        )

        .all()
    )


    # ========================================================
    # UNIQUE ATTRIBUTED STORIES VISITORS
    # ========================================================
    #
    # source_session_id originates from the anonymous Stories
    # session.
    #
    # We count it here but never expose the IDs themselves.
    # ========================================================

    unique_rows = (
        db.session.query(

            RestaurantAnalyticsEvent
            .source_article_id
            .label(
                "story_id"
            ),

            RestaurantAnalyticsEvent
            .restaurant_id
            .label(
                "restaurant_id"
            ),

            db.func.count(
                db.func.distinct(
                    RestaurantAnalyticsEvent
                    .source_session_id
                )
            )
            .label(
                "unique_sessions"
            ),
        )

        .filter(
            RestaurantAnalyticsEvent.source
            == "kalxa_stories",

            RestaurantAnalyticsEvent
            .source_article_id
            .in_(
                story_ids
            ),

            RestaurantAnalyticsEvent
            .source_session_id
            .isnot(
                None
            ),
        )

        .group_by(
            RestaurantAnalyticsEvent
            .source_article_id,

            RestaurantAnalyticsEvent
            .restaurant_id,
        )

        .all()
    )


    # ========================================================
    # RESPONSE STRUCTURE
    # ========================================================

    results = {}


    def get_result(
        story_id,
        restaurant_id,
    ):

        story_key = str(
            story_id
        )

        restaurant_key = str(
            restaurant_id
        )


        if story_key not in results:

            results[
                story_key
            ] = {
                "story_id":
                    story_id,

                "restaurants":
                    {},
            }


        restaurants = (
            results[
                story_key
            ][
                "restaurants"
            ]
        )


        if (
            restaurant_key
            not in restaurants
        ):

            restaurants[
                restaurant_key
            ] = {
                "restaurant_id":
                    restaurant_id,

                "restaurant_views":
                    0,

                "experience_views":
                    0,

                "whatsapp_clicks":
                    0,

                "phone_clicks":
                    0,

                "directions_clicks":
                    0,

                "meaningful_actions":
                    0,

                "unique_sessions":
                    0,
            }


        return restaurants[
            restaurant_key
        ]


    # ========================================================
    # MAP EVENT COUNTS
    # ========================================================

    event_field_map = {
        "restaurant_view":
            "restaurant_views",

        "experience_view":
            "experience_views",

        "whatsapp_click":
            "whatsapp_clicks",

        "phone_click":
            "phone_clicks",

        "directions_click":
            "directions_clicks",
    }


    for row in rows:

        result = get_result(
            story_id=(
                row.story_id
            ),

            restaurant_id=(
                row.restaurant_id
            ),
        )


        field_name = (
            event_field_map.get(
                row.event_type
            )
        )


        if field_name:

            result[
                field_name
            ] = int(
                row.event_count
                or
                0
            )


    # ========================================================
    # UNIQUE SESSIONS
    # ========================================================

    for row in unique_rows:

        result = get_result(
            story_id=(
                row.story_id
            ),

            restaurant_id=(
                row.restaurant_id
            ),
        )


        result[
            "unique_sessions"
        ] = int(
            row.unique_sessions
            or
            0
        )


    # ========================================================
    # MEANINGFUL ACTIONS
    # ========================================================
    #
    # Restaurant views and experience views represent
    # engagement.
    #
    # The following represent stronger customer intent:
    #
    #     WhatsApp
    #     phone
    #     directions
    # ========================================================

    for story in results.values():

        for restaurant in (
            story[
                "restaurants"
            ]
            .values()
        ):

            restaurant[
                "meaningful_actions"
            ] = (
                restaurant[
                    "whatsapp_clicks"
                ]
                +
                restaurant[
                    "phone_clicks"
                ]
                +
                restaurant[
                    "directions_clicks"
                ]
            )


    # ========================================================
    # CONVERT RESTAURANT DICTS TO LISTS
    # ========================================================

    response_stories = []


    for story_id in story_ids:

        story_key = str(
            story_id
        )


        story = (
            results.get(
                story_key,
                {
                    "story_id":
                        story_id,

                    "restaurants":
                        {},
                },
            )
        )


        restaurants = list(
            story[
                "restaurants"
            ]
            .values()
        )


        # ====================================================
        # STORY TOTALS
        # ====================================================

        totals = {
            "restaurant_views":
                sum(
                    restaurant[
                        "restaurant_views"
                    ]
                    for restaurant
                    in restaurants
                ),

            "experience_views":
                sum(
                    restaurant[
                        "experience_views"
                    ]
                    for restaurant
                    in restaurants
                ),

            "whatsapp_clicks":
                sum(
                    restaurant[
                        "whatsapp_clicks"
                    ]
                    for restaurant
                    in restaurants
                ),

            "phone_clicks":
                sum(
                    restaurant[
                        "phone_clicks"
                    ]
                    for restaurant
                    in restaurants
                ),

            "directions_clicks":
                sum(
                    restaurant[
                        "directions_clicks"
                    ]
                    for restaurant
                    in restaurants
                ),

            "meaningful_actions":
                sum(
                    restaurant[
                        "meaningful_actions"
                    ]
                    for restaurant
                    in restaurants
                ),
        }


        response_stories.append(
            {
                "story_id":
                    story_id,

                "totals":
                    totals,

                "restaurants":
                    restaurants,
            }
        )


    # ========================================================
    # SUCCESS
    # ========================================================

    return jsonify(
        {
            "ok":
                True,

            "source":
                "kalxa_stories",

            "stories":
                response_stories,
        }
    ), 200

# ============================================================
# PUBLIC - POST RESTAURANT EXPERIENCE
# ============================================================
# ============================================================
# PUBLIC - POST RESTAURANT EXPERIENCE
# ============================================================



# ============================================================
# PUBLIC - LOVE / UNLOVE RESTAURANT EXPERIENCE
# ============================================================

@app.route(
    "/experiences/<int:post_id>/love",
    methods=[
        "POST",
    ],
)
def love_restaurant_experience(
    post_id,
):

    experience_post = (
        RestaurantExperiencePost.query

        .filter_by(
            id=
                post_id,

            active=
                True,

            moderation_status=
                "approved",
        )

        .first_or_404()
    )


    anonymous_session_id = (
        get_restaurant_experience_session_id()
    )


    existing_love = (
        RestaurantExperienceLove.query

        .filter_by(
            post_id=
                experience_post.id,

            anonymous_session_id=
                anonymous_session_id,
        )

        .first()
    )


    loved = False


    try:

        # ====================================================
        # UNLOVE
        # ====================================================

        if existing_love:

            db.session.delete(
                existing_love
            )


            loved = False


        # ====================================================
        # LOVE
        # ====================================================

        else:

            love = (
                RestaurantExperienceLove(

                    post_id=
                        experience_post.id,

                    anonymous_session_id=
                        anonymous_session_id,
                )
            )


            db.session.add(
                love
            )


            loved = True


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Restaurant Experience Love] "
                "Failed post_id=%s error=%s"
            ),
            experience_post.id,
            error,
        )


        return jsonify(
            {
                "ok": False,
                "message": (
                    "Unable to update love."
                ),
            }
        ), 500


    love_count = (
        RestaurantExperienceLove.query

        .filter_by(
            post_id=
                experience_post.id
        )

        .count()
    )


    return jsonify(
        {
            "ok": True,

            "post_id":
                experience_post.id,

            "loved":
                loved,

            "love_count":
                love_count,
        }
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


                current_phase = ticket_type.current_sale_phase

                if ticket_type.active_sale_phases and current_phase is None:
                    flash(f"{ticket_type.name} is not currently on sale.", "error")
                    return render_template("reserve_ticket.html", event=event, ticket_types=ticket_types, processing_rate=PAYSTACK_EFT_EFFECTIVE_FEE_RATE)

                if current_phase and current_phase.remaining_quantity is not None and quantity > current_phase.remaining_quantity:
                    flash(f"Only {current_phase.remaining_quantity} {ticket_type.name} ticket(s) remain in {current_phase.name}.", "error")
                    return render_template("reserve_ticket.html", event=event, ticket_types=ticket_types, processing_rate=PAYSTACK_EFT_EFFECTIVE_FEE_RATE)

                effective_price = current_phase.price if current_phase else ticket_type.price

                attendee_names = []

                for attendee_index in range(
                    1,
                    quantity + 1,
                ):

                    attendee_name = (
                        request.form.get(
                            (
                                f"attendee_"
                                f"{ticket_type.id}_"
                                f"{attendee_index}"
                            ),
                            "",
                        )
                        .strip()
                    )

                    if not attendee_name:

                        flash(
                            (
                                f"Enter the attendee name for "
                                f"every {ticket_type.name} ticket."
                            ),
                            "error",
                        )

                        return render_template(
                            "reserve_ticket.html",
                            event=event,
                            ticket_types=ticket_types,
                            processing_rate=
                                PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
                        )

                    attendee_names.append(
                        attendee_name
                    )



                basket.append({
                    "ticket_type": ticket_type,
                    "sale_phase": current_phase,
                    "name": ticket_type.name,
                    "price": Decimal(str(effective_price)),
                    "quantity": quantity,
                    "attendee_names": attendee_names,
                })


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

                attendee_names = []

                for attendee_index in range(
                    1,
                    quantity + 1,
                ):

                    attendee_name = (
                        request.form.get(
                            f"attendee_general_{attendee_index}",
                            "",
                        )
                        .strip()
                    )

                    if not attendee_name:

                        flash(
                            "Enter the attendee name for every General ticket.",
                            "error",
                        )

                        return render_template(
                            "reserve_ticket.html",
                            event=event,
                            ticket_types=[],
                            processing_rate=
                                PAYSTACK_EFT_EFFECTIVE_FEE_RATE,
                        )

                    attendee_names.append(
                        attendee_name
                    )



                basket.append(
                    {
                        "ticket_type":
                            None,
                        "name":
                            "General",              
                        "attendee_names": 
                            attendee_names,
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



                line_total = (
                    item["price"]
                    * item["quantity"]
                ).quantize(
                    Decimal("0.01")
                )

                db.session.add(
                    TicketOrderItem(
                        order_id=order.id,
                        ticket_type_id=(
                            item["ticket_type"].id
                            if item["ticket_type"]
                            else None
                        ),
                        sale_phase_id=(
                            item["sale_phase"].id
                            if item.get("sale_phase")
                            else None
                        ),
                        sale_phase_name=(
                            item["sale_phase"].name
                            if item.get("sale_phase")
                            else None
                        ),
                        ticket_name=item["name"],
                        unit_price=item["price"],
                        quantity=item["quantity"],
                        line_total=line_total,
                        attendee_names=(
                            item.get("attendee_names")
                            or []
                        ),
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
                    "unit_price": str(item["price"]),
                    "sale_phase": (item["sale_phase"].name if item.get("sale_phase") else None),
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

    # ========================================================
    # PAYSTACK CONFIGURATION
    # ========================================================

    if not PAYSTACK_SECRET_KEY:

        abort(503)


    # ========================================================
    # RAW WEBHOOK BODY
    # ========================================================
    #
    # IMPORTANT:
    #
    # The exact raw body received from Paystack must be used
    # when calculating the webhook signature.
    #
    # Do not JSON-decode and then re-encode the payload before
    # calculating the HMAC.
    # ========================================================

    raw_body = (
        request.get_data()
    )


    # ========================================================
    # VERIFY PAYSTACK SIGNATURE
    # ========================================================

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

        current_app.logger.warning(
            (
                "[Paystack Webhook] "
                "Rejected webhook with invalid signature."
            )
        )

        abort(400)


    # ========================================================
    # PARSE PAYSTACK PAYLOAD
    # ========================================================

    try:

        payload = json.loads(
            raw_body.decode(
                "utf-8"
            )
        )


    except Exception as error:

        current_app.logger.warning(
            (
                "[Paystack Webhook] "
                "Unable to parse webhook payload "
                "error=%s"
            ),
            error,
        )

        abort(400)


    # ========================================================
    # ONLY PROCESS SUCCESSFUL CHARGES
    # ========================================================

    event_type = (
        payload.get(
            "event"
        )
    )


    if event_type != "charge.success":

        return (
            "",
            200,
        )


    # ========================================================
    # TRANSACTION DATA
    # ========================================================

    transaction_data = (
        payload.get(
            "data"
        )
        or {}
    )


    # ========================================================
    # PAYMENT REFERENCE
    # ========================================================

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

        current_app.logger.warning(
            (
                "[Paystack Webhook] "
                "charge.success received without "
                "a payment reference."
            )
        )

        return (
            "",
            200,
        )


    # ========================================================
    # 1. TICKET ORDER
    # ========================================================
    #
    # Customer pays for event tickets.
    #
    # Money may be settled to the organizer through the
    # organizer's Paystack subaccount.
    # ========================================================

    order = (
        TicketOrder.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if order:

        try:

            finalize_paystack_ticket_order(
                order,
                transaction_data,
            )


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Paystack Ticket Webhook] "
                    "Failed "
                    "reference=%s "
                    "order_id=%s "
                    "error=%s"
                ),
                reference,
                order.id,
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


    # ========================================================
    # 2. RESTAURANT SUBSCRIPTION PAYMENT
    # ========================================================
    #
    # Restaurant owner pays Kalxa for:
    #
    #     Standard
    #         R219
    #
    #     Premium
    #         R299
    #
    # This is completely separate from the legacy Organizer
    # SaaS subscription.
    # ========================================================

    restaurant_subscription_payment = (
        RestaurantSubscriptionPayment.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if restaurant_subscription_payment:

        # ====================================================
        # CANCELLED RESTAURANT PAYMENT
        # ====================================================
        #
        # An old checkout may have been cancelled because:
        #
        #     price changed
        #     owner selected another plan
        #     checkout was replaced
        #
        # If the old Paystack checkout somehow succeeds later,
        # acknowledge it but DO NOT activate the restaurant.
        # ====================================================

        if (
            restaurant_subscription_payment.payment_status
            == "cancelled"
        ):

            current_app.logger.warning(
                (
                    "[Restaurant Subscription Webhook] "
                    "Ignoring successful transaction for "
                    "cancelled payment "
                    "reference=%s "
                    "restaurant_id=%s "
                    "organizer_id=%s "
                    "payment_id=%s"
                ),
                reference,
                restaurant_subscription_payment.restaurant_advert_id,
                restaurant_subscription_payment.organizer_id,
                restaurant_subscription_payment.id,
            )


            return (
                "",
                200,
            )


        # ====================================================
        # FINALIZE RESTAURANT SUBSCRIPTION
        # ====================================================

        try:

            finalize_restaurant_subscription_payment(
                restaurant_subscription_payment,
                transaction_data,
            )


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Restaurant Subscription Webhook] "
                    "Finalization failed "
                    "reference=%s "
                    "restaurant_id=%s "
                    "payment_id=%s "
                    "error=%s"
                ),
                reference,
                restaurant_subscription_payment.restaurant_advert_id,
                restaurant_subscription_payment.id,
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


    # ========================================================
    # 3. LEGACY / ORGANIZER SUBSCRIPTION PAYMENT
    # ========================================================
    #
    # This is the existing SubscriptionPayment table.
    #
    # IMPORTANT:
    #
    # This activates Organizer SaaS access.
    #
    # It does NOT control:
    #
    #     RestaurantAdvert.subscription_tier
    #
    # Restaurant Standard/Premium payments are handled by the
    # RestaurantSubscriptionPayment branch above.
    # ========================================================

    subscription_payment = (
        SubscriptionPayment.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if subscription_payment:

        # ====================================================
        # CANCELLED ORGANIZER SUBSCRIPTION PAYMENT
        # ====================================================

        if (
            subscription_payment.payment_status
            == "cancelled"
        ):

            current_app.logger.warning(
                (
                    "[Paystack Subscription Webhook] "
                    "Ignoring successful transaction for "
                    "cancelled organizer subscription "
                    "reference=%s "
                    "organizer_id=%s "
                    "payment_id=%s"
                ),
                reference,
                subscription_payment.organizer_id,
                subscription_payment.id,
            )


            return (
                "",
                200,
            )


        # ====================================================
        # FINALIZE ORGANIZER SUBSCRIPTION
        # ====================================================

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
                    "Finalization failed "
                    "reference=%s "
                    "organizer_id=%s "
                    "payment_id=%s "
                    "error=%s"
                ),
                reference,
                subscription_payment.organizer_id,
                subscription_payment.id,
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


    # ========================================================
    # 4. EVENT BOOST
    # ========================================================

    boost = (
        EventBoost.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if boost:

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
                    "Finalization failed "
                    "reference=%s "
                    "boost_id=%s "
                    "error=%s"
                ),
                reference,
                boost.id,
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


    # ========================================================
    # 5. FEATURED LISTING
    # ========================================================

    featured_listing = (
        FeaturedListing.query
        .filter_by(
            payment_reference=
                reference
        )
        .first()
    )


    if featured_listing:

        try:

            finalize_featured_listing_payment(
                featured_listing,
                transaction_data,
            )


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Paystack Featured Listing Webhook] "
                    "Finalization failed "
                    "reference=%s "
                    "featured_listing_id=%s "
                    "error=%s"
                ),
                reference,
                featured_listing.id,
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


    # ========================================================
    # UNKNOWN PAYMENT REFERENCE
    # ========================================================
    #
    # The webhook is valid and signed by Paystack, but Kalxa
    # does not currently have a matching payment record.
    #
    # We return 200 so Paystack does not repeatedly resend a
    # transaction that Kalxa cannot associate with a record.
    # ========================================================

    current_app.logger.warning(
        (
            "[Paystack Webhook] "
            "No Kalxa payment record found "
            "for reference=%s"
        ),
        reference,
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
# ORGANIZER EVENT REEL
# ============================================================
@app.route(
    "/admin/events/<int:event_id>/reel",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_event_reel(
    event_id,
):

    auth = require_ticketing_organizer()

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
            organizer_deleted=False,
        )
        .first_or_404()
    )


    reel = (
        EventReel.query
        .filter_by(
            event_id=event.id,
        )
        .first()
    )


    # ========================================================
    # UPLOAD / REPLACE REEL
    # ========================================================

    if request.method == "POST":

        if not cloudinary_reels_configured():

            flash(
                (
                    "Event Reel storage is not "
                    "configured yet."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_event_reel",
                    event_id=event.id,
                )
            )


        video = (
            request.files.get(
                "reel_video"
            )
        )


        if (
            not video
            or not video.filename
        ):

            flash(
                "Choose a video to upload.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_event_reel",
                    event_id=event.id,
                )
            )


        if not allowed_event_reel_filename(
            video.filename
        ):

            flash(
                (
                    "Use an MP4, MOV, M4V "
                    "or WebM video."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_event_reel",
                    event_id=event.id,
                )
            )


        video.stream.seek(
            0,
            os.SEEK_END,
        )

        file_size = (
            video.stream.tell()
        )

        video.stream.seek(0)


        if (
            file_size
            > EVENT_REEL_MAX_FILE_BYTES
        ):

            flash(
                (
                    "The reel is too large. "
                    "Maximum size is 80 MB."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_event_reel",
                    event_id=event.id,
                )
            )


        uploaded_public_id = None


        try:

            upload_result = (
                cloudinary.uploader.upload(
                    video,
                    resource_type="video",
                    folder=(
                        "kalxa/"
                        f"organizers/{organizer.id}/"
                        f"events/{event.id}/reels"
                    ),
                    use_filename=True,
                    unique_filename=True,
                    overwrite=False,
                )
            )


            uploaded_public_id = (
                upload_result.get(
                    "public_id"
                )
            )


            duration_seconds = float(
                upload_result.get(
                    "duration",
                    0,
                )
                or 0
            )


            if (
                duration_seconds <= 0
            ):

                raise ValueError(
                    "Unable to determine video duration."
                )


            if (
                duration_seconds
                > EVENT_REEL_MAX_DURATION_SECONDS
            ):

                delete_cloudinary_reel(
                    uploaded_public_id
                )

                flash(
                    (
                        "Your Event Reel must be "
                        "30 seconds or shorter."
                    ),
                    "error",
                )

                return redirect(
                    url_for(
                        "admin_event_reel",
                        event_id=event.id,
                    )
                )


            secure_url = (
                upload_result.get(
                    "secure_url"
                )
            )


            if not secure_url:

                raise ValueError(
                    (
                        "Cloudinary did not return "
                        "a secure video URL."
                    )
                )


            # Cloudinary image thumbnail generated
            # from the first useful video frame.
            thumbnail_url = (
                cloudinary.CloudinaryVideo(
                    uploaded_public_id
                )
                .build_url(
                    resource_type="video",
                    format="jpg",
                    start_offset="1",
                    width=720,
                    crop="limit",
                    secure=True,
                )
            )


            old_public_id = (
                reel.cloudinary_public_id
                if reel
                else None
            )


            if reel is None:

                reel = EventReel(
                    event_id=event.id,
                    organizer_id=organizer.id,
                    cloudinary_public_id=uploaded_public_id,
                    video_url=secure_url,
                    thumbnail_url=thumbnail_url,
                    duration_seconds=duration_seconds,
                    width=upload_result.get(
                        "width"
                    ),
                    height=upload_result.get(
                        "height"
                    ),
                    file_bytes=upload_result.get(
                        "bytes"
                    ),
                    active=True,
                )

                db.session.add(
                    reel
                )

            else:

                reel.cloudinary_public_id = (
                    uploaded_public_id
                )

                reel.video_url = (
                    secure_url
                )

                reel.thumbnail_url = (
                    thumbnail_url
                )

                reel.duration_seconds = (
                    duration_seconds
                )

                reel.width = (
                    upload_result.get(
                        "width"
                    )
                )

                reel.height = (
                    upload_result.get(
                        "height"
                    )
                )

                reel.file_bytes = (
                    upload_result.get(
                        "bytes"
                    )
                )

                reel.active = True


            db.session.commit()


            if (
                old_public_id
                and old_public_id
                != uploaded_public_id
            ):

                delete_cloudinary_reel(
                    old_public_id
                )


            flash(
                "Event Reel published successfully.",
                "success",
            )


            return redirect(
                url_for(
                    "admin_event_reel",
                    event_id=event.id,
                )
            )


        except Exception as error:

            db.session.rollback()


            if uploaded_public_id:

                delete_cloudinary_reel(
                    uploaded_public_id
                )


            current_app.logger.exception(
                (
                    "[Event Reel] Upload failed "
                    "event_id=%s "
                    "organizer_id=%s "
                    "error=%s"
                ),
                event.id,
                organizer.id,
                error,
            )


            flash(
                (
                    "Kalxa could not upload this "
                    "reel. Please try again."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_event_reel",
                    event_id=event.id,
                )
            )


    # ========================================================
    # REEL ANALYTICS
    # ========================================================

    reel_analytics = {
        "impressions": 0,
        "plays": 0,
        "opens": 0,
        "half_watched": 0,
        "completed": 0,
        "view_event": 0,
    }


    if reel:

        analytics_rows = (
            db.session.query(
                EventReelAnalytics.event_type,
                db.func.count(
                    EventReelAnalytics.id
                ),
            )
            .filter(
                EventReelAnalytics.reel_id
                == reel.id,

                EventReelAnalytics.organizer_id
                == organizer.id,

                EventReelAnalytics.event_id
                == event.id,
            )
            .group_by(
                EventReelAnalytics.event_type
            )
            .all()
        )


        analytics_counts = {
            event_type: count
            for event_type, count
            in analytics_rows
        }


        reel_analytics = {
            "impressions":
                analytics_counts.get(
                    "impression",
                    0,
                ),

            "plays":
                analytics_counts.get(
                    "play",
                    0,
                ),

            "opens":
                analytics_counts.get(
                    "open",
                    0,
                ),

            "half_watched":
                analytics_counts.get(
                    "half_watched",
                    0,
                ),

            "completed":
                analytics_counts.get(
                    "completed",
                    0,
                ),

            "view_event":
                analytics_counts.get(
                    "view_event",
                    0,
                ),
        }


    # ========================================================
    # TEMPLATE
    # ========================================================

    return render_template(
        "admin/event_reel.html",
        organizer=organizer,
        event=event,
        reel=reel,
        reel_analytics=reel_analytics,
    )
   
@app.route(
    "/admin/events/<int:event_id>/reel/delete",
    methods=[
        "POST",
    ],
)
def admin_delete_event_reel(
    event_id,
):

    auth = require_ticketing_organizer()

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
            organizer_deleted=False,
        )
        .first_or_404()
    )


    reel = (
        EventReel.query
        .filter_by(
            event_id=event.id,
            organizer_id=organizer.id,
        )
        .first()
    )


    if not reel:

        flash(
            "This event does not have a reel.",
            "error",
        )

        return redirect(
            url_for(
                "admin_event_reel",
                event_id=event.id,
            )
        )


    public_id = (
        reel.cloudinary_public_id
    )


    try:

        db.session.delete(
            reel
        )

        db.session.commit()


        delete_cloudinary_reel(
            public_id
        )


        flash(
            "Event Reel removed.",
            "success",
        )


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Event Reel] Delete failed "
                "event_id=%s error=%s"
            ),
            event.id,
            error,
        )

        flash(
            "Unable to remove Event Reel.",
            "error",
        )


    return redirect(
        url_for(
            "admin_event_reel",
            event_id=event.id,
        )
    )   


# ============================================================
# PUBLIC EVENT REEL ANALYTICS
# ============================================================

REEL_ANALYTICS_EVENT_TYPES = {
    "impression",
    "play",
    "open",
    "half_watched",
    "completed",
    "view_event",
}


@app.route(
    "/analytics/reels/track",
    methods=["POST"],
)
def track_event_reel():

    payload = (
        request.get_json(
            silent=True,
        )
        or {}
    )


    # ========================================================
    # INPUT
    # ========================================================

    reel_id = payload.get(
        "reel_id"
    )

    event_type = (
        str(
            payload.get(
                "event_type",
                "",
            )
        )
        .strip()
        .lower()
    )

    anonymous_session_id = (
        str(
            payload.get(
                "session_id",
                "",
            )
        )
        .strip()
    )


    # ========================================================
    # BASIC VALIDATION
    # ========================================================

    if not isinstance(
        reel_id,
        int,
    ):
        return {
            "ok": False,
            "error": "Invalid reel.",
        }, 400


    if (
        event_type
        not in REEL_ANALYTICS_EVENT_TYPES
    ):
        return {
            "ok": False,
            "error": "Invalid analytics event.",
        }, 400


    if (
        not anonymous_session_id
        or len(
            anonymous_session_id
        ) > 80
    ):
        return {
            "ok": False,
            "error": "Invalid analytics session.",
        }, 400


    # ========================================================
    # FIND PUBLIC REEL
    # ========================================================

    reel = (
        EventReel.query
        .filter_by(
            id=reel_id,
            active=True,
        )
        .first()
    )


    if (
        not reel
        or not reel.event
    ):
        return {
            "ok": False,
        }, 404


    event = reel.event


    # ========================================================
    # VERIFY EVENT IS PUBLIC
    # ========================================================

    today_sa = (
        datetime.now(
            ZoneInfo(
                "Africa/Johannesburg"
            )
        )
        .date()
    )


    if (
        not event.active
        or event.status != "published"
        or event.organizer_deleted
        or (
            event.event_date
            and event.event_date
            < today_sa
        )
    ):
        return {
            "ok": False,
        }, 404


    # ========================================================
    # RECORD ANONYMOUS ANALYTICS
    # ========================================================

    analytics_event = (
        EventReelAnalytics(
            reel_id=reel.id,
            event_id=event.id,
            organizer_id=reel.organizer_id,
            event_type=event_type,
            anonymous_session_id=(
                anonymous_session_id
            ),
        )
    )


    try:

        db.session.add(
            analytics_event
        )

        db.session.commit()


    except IntegrityError:

        # Same session already generated this exact
        # analytics event for this reel.
        #
        # Treat duplicate tracking as successful.
        db.session.rollback()


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Event Reel Analytics] "
                "tracking failed "
                "reel_id=%s "
                "event_type=%s "
                "error=%s"
            ),
            reel.id,
            event_type,
            error,
        )

        return {
            "ok": False,
        }, 500


    return {
        "ok": True,
    }
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


    # ========================================================
    # ACCOUNT-SPECIFIC SUBSCRIPTION PRICE
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if (
        account_type
        == "restaurant"
    ):

        subscription_price = (
            KALXA_RESTAURANT_SUBSCRIPTION_PRICE
        )

    else:

        subscription_price = (
            KALXA_SUBSCRIPTION_PRICE
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
            subscription_price,

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


    # ========================================================
    # ACCOUNT-SPECIFIC SUBSCRIPTION PRICE
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if (
        account_type
        == "restaurant"
    ):

        subscription_price = (
            KALXA_RESTAURANT_SUBSCRIPTION_PRICE
        )

    else:

        subscription_price = (
            KALXA_SUBSCRIPTION_PRICE
        )


    # ========================================================
    # SUSPENSION CHECK
    # ========================================================

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


    # ========================================================
    # PAYSTACK CONFIGURATION
    # ========================================================

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


    # ========================================================
    # EXISTING PENDING PAYMENT
    # ========================================================

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


    # ========================================================
    # IMPORTANT:
    #
    # If an old pending payment exists with a different price,
    # do not reuse it.
    #
    # Example:
    #
    # Restaurant previously had a pending R199 payment,
    # but restaurant pricing is now R219.
    #
    # That old checkout must not be reused.
    # ========================================================

    if (
        payment
        and
        Decimal(
            str(
                payment.amount
            )
        )
        !=
        Decimal(
            str(
                subscription_price
            )
        )
    ):

        payment.payment_status = (
            "cancelled"
        )


        try:

            db.session.commit()


        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Subscription Paystack] "
                    "Failed to cancel outdated pending payment "
                    "organizer_id=%s payment_id=%s error=%s"
                ),
                organizer.id,
                payment.id,
                error,
            )


            flash(
                (
                    "Unable to update your subscription payment. "
                    "Please try again."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_subscription"
                )
            )


        payment = None


    # ========================================================
    # REUSE VALID PENDING PAYSTACK CHECKOUT
    # ========================================================

    if (
        payment
        and payment.paystack_authorization_url
    ):

        return redirect(
            payment.paystack_authorization_url
        )


    # ========================================================
    # CREATE SUBSCRIPTION PAYMENT
    # ========================================================

    if not payment:

        payment = SubscriptionPayment(

            organizer_id=
                organizer.id,

            plan_name=
                KALXA_SUBSCRIPTION_PLAN_NAME,

            amount=
                subscription_price,

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


    # ========================================================
    # PAYSTACK CALLBACK
    # ========================================================

    callback_url = url_for(
        "paystack_subscription_callback",
        _external=
            True,
        _scheme=
            "https",
    )


    # ========================================================
    # PAYSTACK PAYLOAD
    # ========================================================

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

                    "account_type":
                        account_type,

                    "plan_name":
                        payment.plan_name,

                    "period_days":
                        payment.period_days,

                    "subscription_amount":
                        str(
                            payment.amount
                        ),
                }
            ),
    }


    # ========================================================
    # INITIALIZE PAYSTACK CHECKOUT
    # ========================================================

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


    # ========================================================
    # REDIRECT TO PAYSTACK
    # ========================================================

    return redirect(
        authorization_url
    )
    
    
    
# ============================================================
# RESTAURANT SUBSCRIPTION CHECKOUT
# ============================================================

@app.route(
    "/admin/restaurants/<int:advert_id>/subscription/checkout/<plan_tier>",
    methods=[
        "POST",
    ],
)
def admin_restaurant_subscription_checkout(
    advert_id,
    plan_tier,
):

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )


    if auth:

        return auth


    organizer = (
        get_current_organizer()
    )


    if not organizer:

        return redirect(
            url_for(
                "organizer_login"
            )
        )


    # ========================================================
    # RESTAURANT ACCOUNT ONLY
    # ========================================================

    account_type = (
        getattr(
            organizer,
            "account_type",
            None,
        )
        or "event"
    )


    if account_type != "restaurant":

        abort(403)


    if not organizer.active:

        flash(
            "Your restaurant account is currently inactive.",
            "error",
        )

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # RESTAURANT
    # ========================================================

    advert = (
        RestaurantAdvert.query
        .filter_by(
            id=advert_id,
            organizer_id=organizer.id,
        )
        .first_or_404()
    )


    # ========================================================
    # SYNCHRONIZE EXISTING PLAN
    # ========================================================

    sync_restaurant_subscription(
        advert
    )


    # ========================================================
    # VALIDATE REQUESTED PLAN
    # ========================================================
    #
    # Never accept the price from HTML.
    #
    # The browser only supplies:
    #
    #     standard
    #     premium
    #
    # Price comes from server-side constants.
    # ========================================================

    requested_plan = (
        plan_tier
        or ""
    ).strip().lower()


    if requested_plan not in RESTAURANT_PAYABLE_PLANS:

        abort(400)


    plan_config = (
        RESTAURANT_PAYABLE_PLANS[
            requested_plan
        ]
    )


    plan_name = (
        plan_config[
            "name"
        ]
    )


    plan_price = (
        Decimal(
            str(
                plan_config[
                    "price"
                ]
            )
        )
    )


    # ========================================================
    # PAYSTACK CONFIGURATION
    # ========================================================

    if not paystack_is_configured():

        flash(
            "Paystack is not configured on Kalxa yet.",
            "error",
        )

        return redirect(
            url_for(
                "admin_manage_restaurant",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # FIND EXISTING PENDING PAYMENT
    # ========================================================

    payment = (
        RestaurantSubscriptionPayment.query
        .filter_by(
            restaurant_advert_id=advert.id,
            organizer_id=organizer.id,
            plan_tier=requested_plan,
            payment_status="pending",
        )
        .order_by(
            RestaurantSubscriptionPayment.created_at.desc()
        )
        .first()
    )


    # ========================================================
    # CANCEL OUTDATED PENDING PAYMENT
    # ========================================================

    if payment:

        existing_amount = (
            Decimal(
                str(
                    payment.amount
                )
            )
        )


        if existing_amount != plan_price:

            payment.payment_status = (
                "cancelled"
            )


            try:

                db.session.commit()


            except Exception as error:

                db.session.rollback()

                current_app.logger.exception(
                    (
                        "[Restaurant Subscription] "
                        "Unable to cancel outdated checkout "
                        "restaurant_id=%s "
                        "payment_id=%s "
                        "error=%s"
                    ),
                    advert.id,
                    payment.id,
                    error,
                )


                flash(
                    (
                        "Unable to update your restaurant "
                        "subscription checkout."
                    ),
                    "error",
                )


                return redirect(
                    url_for(
                        "admin_manage_restaurant",
                        advert_id=advert.id,
                    )
                )


            payment = None


    # ========================================================
    # REUSE EXISTING PAYSTACK CHECKOUT
    # ========================================================

    if (
        payment
        and
        payment.paystack_authorization_url
    ):

        return redirect(
            payment.paystack_authorization_url
        )


    # ========================================================
    # CREATE PAYMENT RECORD
    # ========================================================

    if not payment:

        payment = (
            RestaurantSubscriptionPayment(

                restaurant_advert_id=
                    advert.id,

                organizer_id=
                    organizer.id,

                plan_tier=
                    requested_plan,

                plan_name=
                    plan_name,

                amount=
                    plan_price,

                currency=
                    "ZAR",

                period_days=
                    RESTAURANT_SUBSCRIPTION_PERIOD_DAYS,

                payment_reference=
                    generate_restaurant_subscription_payment_reference(),

                payment_method=
                    "paystack",

                payment_status=
                    "pending",
            )
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
                    "[Restaurant Subscription] "
                    "Unable to create payment "
                    "restaurant_id=%s "
                    "plan=%s "
                    "error=%s"
                ),
                advert.id,
                requested_plan,
                error,
            )


            flash(
                (
                    "Unable to start restaurant "
                    "subscription payment."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_manage_restaurant",
                    advert_id=advert.id,
                )
            )


    # ========================================================
    # CALLBACK
    # ========================================================

    callback_url = url_for(
        "paystack_restaurant_subscription_callback",
        _external=True,
        _scheme="https",
    )


    # ========================================================
    # CANCEL URL
    # ========================================================

    cancel_url = url_for(
        "admin_manage_restaurant",
        advert_id=advert.id,
        _external=True,
        _scheme="https",
    )


    # ========================================================
    # PAYSTACK AMOUNT
    # ========================================================

    amount_cents = int(
        (
            plan_price
            * 100
        )
        .quantize(
            Decimal("1"),
            rounding=ROUND_UP,
        )
    )


    # ========================================================
    # PAYSTACK PAYLOAD
    # ========================================================
    #
    # IMPORTANT:
    #
    # There is NO restaurant subaccount here.
    #
    # Restaurant subscriptions are payments from the
    # restaurant TO Kalxa.
    # ========================================================

    payload = {

        "email":
            organizer.email,

        "amount":
            str(
                amount_cents
            ),

        "currency":
            "ZAR",

        "reference":
            payment.payment_reference,

        "callback_url":
            callback_url,

        "channels": [
            "eft",
            "capitec_pay",
        ],

        "metadata":
            json.dumps(
                {

                    "payment_type":
                        "restaurant_subscription",

                    "restaurant_subscription_payment_id":
                        payment.id,

                    "restaurant_advert_id":
                        advert.id,

                    "organizer_id":
                        organizer.id,

                    "restaurant_plan":
                        requested_plan,

                    "plan_name":
                        plan_name,

                    "amount":
                        str(
                            plan_price
                        ),

                    "period_days":
                        RESTAURANT_SUBSCRIPTION_PERIOD_DAYS,

                    "cancel_action":
                        cancel_url,
                }
            ),
    }


    # ========================================================
    # INITIALIZE PAYSTACK
    # ========================================================

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
                (
                    "Paystack did not return "
                    "a checkout URL."
                )
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
                "[Restaurant Subscription] "
                "Paystack initialization failed "
                "restaurant_id=%s "
                "payment_id=%s "
                "plan=%s "
                "error=%s"
            ),
            advert.id,
            payment.id,
            requested_plan,
            error,
        )


        flash(
            (
                "Secure Paystack checkout could not "
                "be started. Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_manage_restaurant",
                advert_id=advert.id,
            )
        )


    # ========================================================
    # REDIRECT TO PAYSTACK
    # ========================================================

    return redirect(
        authorization_url
    )  
    
# ============================================================
# RESTAURANT SUBSCRIPTION PAYSTACK CALLBACK
# ============================================================

@app.route(
    "/payments/paystack/restaurant-subscription/callback"
)
def paystack_restaurant_subscription_callback():

    # ========================================================
    # REFERENCE
    # ========================================================

    reference = (
        request.args.get(
            "reference",
            "",
        )
        .strip()
    )


    if not reference:

        abort(400)


    # ========================================================
    # PAYMENT
    # ========================================================

    payment = (
        RestaurantSubscriptionPayment.query
        .filter_by(
            payment_reference=reference
        )
        .first_or_404()
    )


    # ========================================================
    # VERIFY WITH PAYSTACK
    # ========================================================

    try:

        result = (
            paystack_api_request(
                "GET",
                (
                    "/transaction/verify/"
                    +
                    urllib.parse.quote(
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


        finalize_restaurant_subscription_payment(
            payment,
            transaction_data,
        )


        flash(
            (
                f"{payment.plan_name} payment confirmed. "
                "Your restaurant plan is now active."
            ),
            "success",
        )


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Restaurant Subscription Callback] "
                "Verification failed "
                "reference=%s "
                "error=%s"
            ),
            reference,
            error,
        )


        flash(
            (
                "Your restaurant subscription payment "
                "is still being verified. "
                "Please refresh shortly."
            ),
            "error",
        )


    # ========================================================
    # RETURN TO RESTAURANT
    # ========================================================

    return redirect(
        url_for(
            "admin_manage_restaurant",
            advert_id=
                payment.restaurant_advert_id,
        )
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

    if (
      organizer.account_type
      == "restaurant"
    ):

      return redirect(
        url_for(
            "admin_restaurants"
        )
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

    event_reel = (
        EventReel.query
        .filter_by(
            event_id=event.id,
            organizer_id=organizer.id,
        )
        .first()
    )

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
        event_reel=event_reel,
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
# ORGANIZER - FEATURED LISTING
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/featured"
)
def admin_featured_listing(event_id):

    auth = require_ticketing_organizer()
    if auth:
        return auth

    organizer = get_current_organizer()

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
            id=event_id,
            organizer_id=organizer.id,
        )
        .first_or_404()
    )

    active_listing = (
        get_active_featured_listing(
            event.id
        )
    )

    latest_listing = (
        FeaturedListing.query
        .filter_by(
            event_id=event.id,
            organizer_id=organizer.id,
        )
        .order_by(
            FeaturedListing.created_at.desc()
        )
        .first()
    )

    images = list(
        event.featured_images
    )[:FEATURED_IMAGE_MAX_COUNT]

    return render_template(
        "admin/featured_listing.html",
        organizer=organizer,
        event=event,
        active_listing=active_listing,
        latest_listing=latest_listing,
        images=images,
        plans=FEATURED_LISTING_PLANS,
        max_images=FEATURED_IMAGE_MAX_COUNT,
    )


@app.route(
    "/admin/events/<int:event_id>/featured/images",
    methods=["POST"],
)
def admin_save_featured_images(event_id):

    auth = require_ticketing_organizer()
    if auth:
        return auth

    organizer = get_current_organizer()

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
            id=event_id,
            organizer_id=organizer.id,
        )
        .first_or_404()
    )

    uploaded = [
        file
        for file in request.files.getlist(
            "featured_images"
        )
        if file and file.filename
    ]

    if not uploaded:
        flash(
            "Choose between 1 and 3 featured poster images.",
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    if len(uploaded) > FEATURED_IMAGE_MAX_COUNT:
        flash(
            "You can upload a maximum of 3 featured poster images.",
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    try:
        prepared = [
            validate_featured_image_upload(
                image
            )
            for image in uploaded
        ]
    except ValueError as error:
        flash(
            str(error),
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    try:

        for existing in list(
            event.featured_images
        ):
            db.session.delete(
                existing
            )

        db.session.flush()

        for index, image in enumerate(
            prepared,
            start=1,
        ):
            db.session.add(
                FeaturedListingImage(
                    event_id=event.id,
                    image_order=index,
                    image_data=image["data"],
                    image_mimetype=image[
                        "mimetype"
                    ],
                    image_filename=image[
                        "filename"
                    ],
                )
            )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Featured Listing] "
                "Failed saving images "
                "event_id=%s error=%s"
            ),
            event.id,
            error,
        )

        flash(
            "Featured posters could not be saved.",
            "error",
        )

        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    flash(
        (
            f"{len(prepared)} featured poster"
            f"{'s' if len(prepared) != 1 else ''} saved."
        ),
        "success",
    )

    return redirect(
        url_for(
            "admin_featured_listing",
            event_id=event.id,
        )
    )


@app.route(
    "/admin/events/<int:event_id>/featured/purchase/<plan_code>",
    methods=["POST"],
)
def admin_purchase_featured_listing(
    event_id,
    plan_code,
):

    auth = require_ticketing_organizer()
    if auth:
        return auth

    organizer = get_current_organizer()

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
            id=event_id,
            organizer_id=organizer.id,
        )
        .first_or_404()
    )

    try:
        plan = featured_listing_plan(
            plan_code
        )
    except ValueError:
        abort(400)

    if (
        event.status != "published"
        or not event.active
    ):
        flash(
            "Publish the event before buying a Featured Listing.",
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    if (
        event.event_date
        and event.event_date < date.today()
    ):
        flash(
            "Past events cannot be featured.",
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    if get_active_featured_listing(
        event.id
    ):
        flash(
            (
                "This event already has an active Featured Listing. "
                "Buy another package after it expires."
            ),
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    if (
        not event.featured_images
        and not event.poster_image_mimetype
        and not event.image_url
    ):
        flash(
            (
                "Upload at least one featured poster image "
                "or add a normal event poster first."
            ),
            "error",
        )
        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    pending = (
        FeaturedListing.query
        .filter_by(
            event_id=event.id,
            organizer_id=organizer.id,
            status="pending",
        )
        .order_by(
            FeaturedListing.created_at.desc()
        )
        .first()
    )

    if (
        pending
        and pending.plan_code != plan_code
    ):
        db.session.delete(
            pending
        )
        db.session.commit()
        pending = None

    if not pending:

        pending = FeaturedListing(
            event_id=event.id,
            organizer_id=organizer.id,
            plan_code=plan_code,
            plan_name=plan["name"],
            price=plan["price"],
            duration_days=plan[
                "duration_days"
            ],
            status="pending",
            payment_reference=
                generate_featured_listing_reference(),
            payment_provider="paystack",
        )

        db.session.add(
            pending
        )
        db.session.commit()

    if pending.paystack_authorization_url:
        return redirect(
            pending.paystack_authorization_url
        )

    callback_url = url_for(
        "paystack_featured_listing_callback",
        _external=True,
        _scheme="https",
    )

    payload = {
        "email": organizer.email,
        "amount": str(
            int(
                (
                    Decimal(
                        str(pending.price)
                    )
                    * 100
                )
                .quantize(
                    Decimal("1"),
                    rounding=ROUND_UP,
                )
            )
        ),
        "currency": "ZAR",
        "reference":
            pending.payment_reference,
        "callback_url":
            callback_url,
        "channels": [
            "eft",
            "capitec_pay",
        ],
        "metadata": json.dumps(
            {
                "payment_type":
                    "kalxa_featured_listing",
                "featured_listing_id":
                    pending.id,
                "event_id":
                    event.id,
                "organizer_id":
                    organizer.id,
                "plan_code":
                    pending.plan_code,
            }
        ),
    }

    try:

        result = paystack_api_request(
            "POST",
            "/transaction/initialize",
            payload,
        )

        data = result.get(
            "data"
        ) or {}

        authorization_url = data.get(
            "authorization_url"
        )

        if not authorization_url:
            raise RuntimeError(
                "Paystack did not return a Featured Listing checkout URL."
            )

        pending.paystack_access_code = (
            data.get("access_code")
            or None
        )

        pending.paystack_authorization_url = (
            authorization_url
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Featured Listing Paystack] "
                "Checkout initialization failed "
                "listing_id=%s event_id=%s error=%s"
            ),
            pending.id,
            event.id,
            error,
        )

        flash(
            (
                "Featured Listing checkout could not be started. "
                "Please try again."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_featured_listing",
                event_id=event.id,
            )
        )

    return redirect(
        authorization_url
    )


@app.route(
    "/payments/paystack/featured/callback"
)
def paystack_featured_listing_callback():

    reference = (
        request.args.get(
            "reference",
            "",
        )
        .strip()
    )

    if not reference:
        abort(400)

    listing = (
        FeaturedListing.query
        .filter_by(
            payment_reference=reference
        )
        .first_or_404()
    )

    try:

        result = paystack_api_request(
            "GET",
            (
                "/transaction/verify/"
                + urllib.parse.quote(
                    reference,
                    safe="",
                )
            ),
        )

        transaction_data = (
            result.get("data")
            or {}
        )

        finalize_featured_listing_payment(
            listing,
            transaction_data,
        )

        flash(
            (
                f"{listing.plan_name} activated. "
                "Your event is now featured at the top of Kalxa."
            ),
            "success",
        )

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Featured Listing Callback] "
                "Verification failed reference=%s error=%s"
            ),
            reference,
            error,
        )

        flash(
            (
                "Your Featured Listing payment is still being "
                "verified. Please refresh shortly."
            ),
            "error",
        )

    return redirect(
        url_for(
            "admin_featured_listing",
            event_id=listing.event_id,
        )
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
# ORGANIZER - PHASE ANALYTICS OVERVIEW
# ============================================================

@app.route(
    "/admin/sales-phases/analytics"
)
def admin_sales_phase_analytics_overview():

    auth = require_ticketing_organizer()
    if auth:
        return auth

    organizer = get_current_organizer()

    subscription_auth = require_active_subscription(
        organizer
    )
    if subscription_auth:
        return subscription_auth

    events = (
        TicketEvent.query
        .filter_by(
            organizer_id=organizer.id,
        )
        .order_by(
            TicketEvent.event_date.desc(),
            TicketEvent.created_at.desc(),
        )
        .all()
    )

    event_rows = []

    overall_tickets = 0
    overall_revenue = Decimal("0.00")
    overall_phases = 0
    events_with_phases = 0

    for event in events:

        phase_count = sum(
            len(ticket_type.sale_phases)
            for ticket_type in event.ticket_types
        )

        if phase_count:
            events_with_phases += 1

        paid_orders = [
            order
            for order in event.orders
            if order.payment_status == "paid"
        ]

        phased_tickets = 0
        phased_revenue = Decimal("0.00")

        for order in paid_orders:
            for item in order.order_items:

                if not item.sale_phase_name:
                    continue

                phased_tickets += int(
                    item.quantity or 0
                )

                phased_revenue += Decimal(
                    str(
                        item.line_total or 0
                    )
                )

        current_phases = []

        for ticket_type in event.ticket_types:

            phase = (
                ticket_type.current_sale_phase
            )

            if phase:

                current_phases.append(
                    {
                        "ticket_type":
                            ticket_type.name,
                        "phase":
                            phase.name,
                        "price":
                            phase.price,
                    }
                )

        event_rows.append(
            {
                "event": event,
                "phase_count": phase_count,
                "paid_orders": len(paid_orders),
                "tickets_sold": phased_tickets,
                "revenue": phased_revenue,
                "current_phases": current_phases,
            }
        )

        overall_tickets += phased_tickets
        overall_revenue += phased_revenue
        overall_phases += phase_count

    return render_template(
        "admin/phase_analytics_overview.html",
        event_rows=event_rows,
        overall_tickets=overall_tickets,
        overall_revenue=overall_revenue,
        overall_phases=overall_phases,
        events_with_phases=events_with_phases,
    )


# ============================================================
# ORGANIZER - SALES PHASE PERFORMANCE ANALYTICS
# ============================================================

@app.route(
    "/admin/events/<int:event_id>/sales-phases/analytics"
)
def admin_sales_phase_analytics(event_id):

    auth = require_ticketing_organizer()
    if auth:
        return auth

    organizer = get_current_organizer()

    subscription_auth = require_active_subscription(
        organizer
    )
    if subscription_auth:
        return subscription_auth

    event = (
        TicketEvent.query
        .filter_by(
            id=event_id,
            organizer_id=organizer.id,
        )
        .first_or_404()
    )

    # Paid orders are the source of truth for performance.
    paid_orders = (
        TicketOrder.query
        .filter_by(
            event_id=event.id,
            payment_status="paid",
        )
        .order_by(TicketOrder.created_at.asc())
        .all()
    )

    paid_order_ids = {
        order.id
        for order in paid_orders
    }

    # All ticket types / phases are included so phases with zero sales
    # still appear in the organizer report.
    ticket_types = list(event.ticket_types)

    phase_rows = []
    row_lookup = {}

    for ticket_type in ticket_types:
        for phase in ticket_type.sale_phases:
            row = {
                "phase_id": phase.id,
                "ticket_type_id": ticket_type.id,
                "ticket_type": ticket_type.name,
                "phase_name": phase.name,
                "status": phase.sale_status,
                "configured_price": phase.price,
                "quantity_limit": phase.quantity_limit,
                "tickets_sold": 0,
                "revenue": Decimal("0.00"),
                "orders": set(),
                "buyers": set(),
                "first_sale_at": None,
                "last_sale_at": None,
            }
            phase_rows.append(row)
            row_lookup[(ticket_type.id, phase.id)] = row

    # Historical order-item snapshots mean analytics remain correct even
    # after an organizer changes a phase's current price/name.
    historical_only = {}

    for order in paid_orders:
        for item in order.order_items:

            if not item.sale_phase_name:
                continue

            key = (
                item.ticket_type_id,
                item.sale_phase_id,
            )

            row = row_lookup.get(key)

            if row is None:
                history_key = (
                    item.ticket_type_id,
                    item.sale_phase_id,
                    item.ticket_name,
                    item.sale_phase_name,
                )

                row = historical_only.get(history_key)

                if row is None:
                    row = {
                        "phase_id": item.sale_phase_id,
                        "ticket_type_id": item.ticket_type_id,
                        "ticket_type": item.ticket_name,
                        "phase_name": item.sale_phase_name,
                        "status": "historical",
                        "configured_price": item.unit_price,
                        "quantity_limit": None,
                        "tickets_sold": 0,
                        "revenue": Decimal("0.00"),
                        "orders": set(),
                        "buyers": set(),
                        "first_sale_at": None,
                        "last_sale_at": None,
                    }
                    historical_only[history_key] = row
                    phase_rows.append(row)

            quantity = int(item.quantity or 0)
            line_total = Decimal(str(item.line_total or 0))

            row["tickets_sold"] += quantity
            row["revenue"] += line_total
            row["orders"].add(order.id)

            buyer_key = (
                (order.customer_email or "").strip().lower()
                or (order.customer_phone or "").strip()
                or f"order:{order.id}"
            )
            row["buyers"].add(buyer_key)

            sale_at = order.paid_at or order.created_at

            if sale_at:
                if (
                    row["first_sale_at"] is None
                    or sale_at < row["first_sale_at"]
                ):
                    row["first_sale_at"] = sale_at

                if (
                    row["last_sale_at"] is None
                    or sale_at > row["last_sale_at"]
                ):
                    row["last_sale_at"] = sale_at

    total_phase_tickets = sum(
        row["tickets_sold"]
        for row in phase_rows
    )

    total_phase_revenue = sum(
        (row["revenue"] for row in phase_rows),
        Decimal("0.00"),
    )

    for row in phase_rows:
        row["order_count"] = len(row.pop("orders"))
        row["buyer_count"] = len(row.pop("buyers"))

        row["avg_ticket_price"] = (
            row["revenue"] / row["tickets_sold"]
            if row["tickets_sold"]
            else Decimal("0.00")
        )

        row["ticket_share"] = (
            (row["tickets_sold"] / total_phase_tickets) * 100
            if total_phase_tickets
            else 0
        )

        row["revenue_share"] = (
            (float(row["revenue"]) / float(total_phase_revenue)) * 100
            if total_phase_revenue
            else 0
        )

        if row["quantity_limit"]:
            row["sell_through"] = min(
                (row["tickets_sold"] / row["quantity_limit"]) * 100,
                100,
            )
            row["remaining_in_phase"] = max(
                row["quantity_limit"] - row["tickets_sold"],
                0,
            )
        else:
            row["sell_through"] = None
            row["remaining_in_phase"] = None

    phase_rows.sort(
        key=lambda row: (
            str(row["ticket_type"]).lower(),
            row["phase_id"] or 10**9,
        )
    )

    # Ticket-type rollup.
    ticket_type_rows = []

    for ticket_type in ticket_types:
        related = [
            row
            for row in phase_rows
            if row["ticket_type_id"] == ticket_type.id
        ]

        tickets = sum(
            row["tickets_sold"]
            for row in related
        )
        revenue = sum(
            (row["revenue"] for row in related),
            Decimal("0.00"),
        )

        ticket_type_rows.append({
            "name": ticket_type.name,
            "tickets_sold": tickets,
            "revenue": revenue,
            "phase_count": len(related),
        })

    # Best-performing phase is descriptive: highest paid ticket volume.
    phases_with_sales = [
        row
        for row in phase_rows
        if row["tickets_sold"] > 0
    ]

    highest_volume_phase = (
        max(
            phases_with_sales,
            key=lambda row: row["tickets_sold"],
        )
        if phases_with_sales
        else None
    )

    highest_revenue_phase = (
        max(
            phases_with_sales,
            key=lambda row: row["revenue"],
        )
        if phases_with_sales
        else None
    )

    return render_template(
        "admin/sales_phase_analytics.html",
        event=event,
        phase_rows=phase_rows,
        ticket_type_rows=ticket_type_rows,
        total_phase_tickets=total_phase_tickets,
        total_phase_revenue=total_phase_revenue,
        paid_order_count=len(paid_orders),
        highest_volume_phase=highest_volume_phase,
        highest_revenue_phase=highest_revenue_phase,
    )


# ============================================================
# ORGANIZER - SALES PHASES / EARLY BIRD PRICING
# ============================================================
@app.route("/admin/events/<int:event_id>/sales-phases", methods=["GET", "POST"])
def admin_sales_phases(event_id):
    auth = require_ticketing_organizer()
    if auth: return auth
    organizer = get_current_organizer()
    subscription_auth = require_active_subscription(organizer)
    if subscription_auth: return subscription_auth
    event = TicketEvent.query.filter_by(id=event_id, organizer_id=organizer.id).first_or_404()
    ticket_types = [t for t in event.ticket_types if t.active]

    if request.method == "POST":
        raw_tt = str(request.form.get("ticket_type_id", "")).strip()
        if not raw_tt.isdigit(): abort(400)
        ticket_type = TicketType.query.filter_by(id=int(raw_tt), event_id=event.id).first_or_404()
        names=request.form.getlist("phase_name"); prices=request.form.getlist("phase_price")
        starts=request.form.getlist("phase_start_at"); ends=request.form.getlist("phase_end_at")
        limits=request.form.getlist("phase_quantity_limit"); ids=request.form.getlist("phase_id")
        count=max(len(names),len(prices),len(starts),len(ends),len(limits),len(ids))
        if count < 1 or count > 10:
            flash("Choose between 1 and 10 sales phases per ticket type.","error")
            return redirect(url_for("admin_sales_phases",event_id=event.id,ticket_type_id=ticket_type.id))
        rows=[]; seen=set()
        try:
            for index in range(count):
                name=names[index].strip() if index<len(names) else ""
                raw_price=prices[index].strip() if index<len(prices) else ""
                raw_start=starts[index].strip() if index<len(starts) else ""
                raw_end=ends[index].strip() if index<len(ends) else ""
                raw_limit=limits[index].strip() if index<len(limits) else ""
                raw_id=ids[index].strip() if index<len(ids) else ""
                if not any([name,raw_price,raw_start,raw_end,raw_limit,raw_id]): continue
                if not name: raise ValueError("Every sales phase needs a name.")
                key=name.casefold()
                if key in seen: raise ValueError("Sales phase names must be unique for this ticket type.")
                seen.add(key)
                try: price=Decimal(raw_price).quantize(Decimal("0.01"))
                except (InvalidOperation,ValueError) as error: raise ValueError(f"Enter a valid price for {name}.") from error
                if price<0: raise ValueError(f"{name} price cannot be negative.")
                quantity_limit=None
                if raw_limit:
                    try: quantity_limit=int(raw_limit)
                    except ValueError as error: raise ValueError(f"Enter a valid quantity limit for {name}.") from error
                    if quantity_limit<1: raise ValueError(f"{name} quantity limit must be at least 1.")
                phase_id=None
                if raw_id:
                    try: phase_id=int(raw_id)
                    except ValueError: raise ValueError("Invalid sales phase identifier.")
                rows.append({"id":phase_id,"name":name,"price":price,"start_at":parse_phase_datetime(raw_start),"end_at":parse_phase_datetime(raw_end),"quantity_limit":quantity_limit,"sort_order":index})
            if not rows: raise ValueError("Add at least one sales phase.")
            validate_ticket_phase_sequence(ticket_type,rows)
        except ValueError as error:
            flash(str(error),"error")
            return redirect(url_for("admin_sales_phases",event_id=event.id,ticket_type_id=ticket_type.id))

        existing={p.id:p for p in ticket_type.sale_phases}; submitted=set()
        for row in rows:
            if row["id"] is not None:
                if row["id"] not in existing: abort(400)
                phase=existing[row["id"]]; submitted.add(phase.id)
                if row["quantity_limit"] is not None and row["quantity_limit"] < phase.sold_quantity:
                    flash(f"{phase.name} quantity limit cannot be lower than tickets already sold in that phase.","error")
                    return redirect(url_for("admin_sales_phases",event_id=event.id,ticket_type_id=ticket_type.id))
                phase.name=row["name"]; phase.price=row["price"]; phase.start_at=row["start_at"]; phase.end_at=row["end_at"]; phase.quantity_limit=row["quantity_limit"]; phase.sort_order=row["sort_order"]; phase.active=True
            else:
                db.session.add(TicketSalePhase(ticket_type_id=ticket_type.id,name=row["name"],price=row["price"],start_at=row["start_at"],end_at=row["end_at"],quantity_limit=row["quantity_limit"],active=True,sort_order=row["sort_order"]))
        for phase in list(ticket_type.sale_phases):
            if phase.id and phase.id not in submitted:
                if phase.sold_quantity>0: phase.active=False
                else: db.session.delete(phase)
        try: db.session.commit()
        except Exception as error:
            db.session.rollback(); current_app.logger.exception("[Sales Phases] Save failed event_id=%s ticket_type_id=%s error=%s",event.id,ticket_type.id,error)
            flash("Unable to save sales phases.","error")
            return redirect(url_for("admin_sales_phases",event_id=event.id,ticket_type_id=ticket_type.id))
        flash(f"Sales phases saved for {ticket_type.name}.","success")
        return redirect(url_for("admin_sales_phases",event_id=event.id,ticket_type_id=ticket_type.id))

    selected_id=request.args.get("ticket_type_id",type=int)
    selected=next((t for t in ticket_types if t.id==selected_id),None) if selected_id else None
    if not selected and ticket_types: selected=ticket_types[0]
    phase_rows=[serialize_phase_for_form(p) for p in selected.sale_phases if p.active] if selected else []
    return render_template("admin/sales_phases.html",event=event,ticket_types=ticket_types,selected_ticket_type=selected,phase_rows=phase_rows)

@app.route("/admin/events/<int:event_id>/sales-phases/<int:ticket_type_id>/clear",methods=["POST"])
def admin_clear_sales_phases(event_id,ticket_type_id):
    auth=require_ticketing_organizer()
    if auth:return auth
    organizer=get_current_organizer(); subscription_auth=require_active_subscription(organizer)
    if subscription_auth:return subscription_auth
    ticket_type=(TicketType.query.join(TicketEvent).filter(TicketType.id==ticket_type_id,TicketType.event_id==event_id,TicketEvent.organizer_id==organizer.id).first_or_404())
    for phase in list(ticket_type.sale_phases):
        if phase.sold_quantity>0: phase.active=False
        else: db.session.delete(phase)
    db.session.commit()
    flash(f"Sales phases disabled for {ticket_type.name}. Its normal price is active again.","success")
    return redirect(url_for("admin_sales_phases",event_id=event_id,ticket_type_id=ticket_type.id))


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
# ATOMIC TICKET CHECK-IN
# ============================================================

def perform_ticket_checkin(
    pass_id,
    organizer_id,
    checked_in_by,
    staff_account_id=None,
    allowed_event_ids=None,
):

    query = (
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
            == organizer_id
        )
    )


    if allowed_event_ids is not None:

        if not allowed_event_ids:

            return (
                False,
                "You are not assigned to this event.",
                None,
            )

        query = query.filter(
            TicketEvent.id.in_(
                allowed_event_ids
            )
        )


    entry_pass = (
        query.first()
    )


    if not entry_pass:

        return (
            False,
            "Ticket not found for your assigned events.",
            None,
        )


    if (
        not entry_pass.order
        or not entry_pass.order.event
    ):

        return (
            False,
            "This ticket record is incomplete.",
            entry_pass,
        )


    if (
        entry_pass.order.payment_status
        != "paid"
    ):

        return (
            False,
            (
                "This ticket cannot be checked in "
                "because payment has not been confirmed."
            ),
            entry_pass,
        )


    now = (
        datetime.utcnow()
    )


    # Atomic state transition prevents two gate devices from
    # accepting the same QR at the same time.
    updated = (
        EntryPass.query

        .filter(
            EntryPass.id
            == entry_pass.id
        )

        .filter(
            EntryPass.status
            == "valid"
        )

        .filter(
            EntryPass.checked_in_at
            .is_(None)
        )

        .update(
            {
                EntryPass.status:
                    "used",

                EntryPass.checked_in_at:
                    now,
            },
            synchronize_session=
                False,
        )
    )


    if updated != 1:

        db.session.rollback()

        return (
            False,
            (
                "This ticket has already been checked in "
                "or is no longer valid."
            ),
            entry_pass,
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

        db.session.rollback()

        return (
            False,
            "This ticket has already been checked in.",
            entry_pass,
        )


    checkin = CheckIn(

        entry_pass_id=
            entry_pass.id,

        checked_in_at=
            now,

        checked_in_by=
            checked_in_by,

        staff_account_id=
            staff_account_id,
    )


    db.session.add(
        checkin
    )


    try:

        db.session.commit()


    except Exception:

        db.session.rollback()
        raise


    entry_pass = (
        db.session.get(
            EntryPass,
            entry_pass.id,
        )
    )


    return (
        True,
        "Ticket checked in successfully.",
        entry_pass,
    )


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


    try:

        (
            success,
            message,
            entry_pass,
        ) = perform_ticket_checkin(

            pass_id=
                pass_id,

            organizer_id=
                organizer.id,

            checked_in_by=(
                f"organizer:{organizer.id}"
            ),
        )


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Ticketing Check-In] Organizer "
                "check-in failed organizer_id=%s "
                "pass_id=%s error=%s"
            ),
            organizer.id,
            pass_id,
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
        message,
        (
            "success"
            if success
            else "error"
        ),
    )


    return redirect(
        url_for(
            "admin_checkin"
        )
    )


# ============================================================
# STAFF ACCOUNT MANAGEMENT
# ============================================================

@app.route(
    "/admin/staff"
)
def admin_staff():

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


    staff_accounts = (
        StaffAccount.query
        .filter_by(
            organizer_id=
                organizer.id
        )
        .order_by(
            StaffAccount.active.desc(),
            StaffAccount.name.asc(),
        )
        .all()
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
            TicketEvent.event_date.desc(),
            TicketEvent.created_at.desc(),
        )
        .all()
    )


    return render_template(
        "admin/staff.html",

        organizer=
            organizer,

        staff_accounts=
            staff_accounts,

        events=
            events,
    )


@app.route(
    "/admin/staff/new",
    methods=[
        "POST",
    ],
)
def admin_staff_new():

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


    name = (
        request.form.get(
            "name",
            "",
        )
        .strip()
    )

    username = (
        normalize_staff_username(
            request.form.get(
                "username",
                "",
            )
        )
    )

    password = (
        request.form.get(
            "password",
            ""
        )
    )

    event_ids_raw = (
        request.form.getlist(
            "event_ids"
        )
    )


    if not name:

        flash(
            "Staff name is required.",
            "error",
        )

        return redirect(
            url_for(
                "admin_staff"
            )
        )


    if (
        len(username) < 3
        or len(username) > 120
        or any(
            character.isspace()
            for character in username
        )
    ):

        flash(
            (
                "Username must be 3–120 characters "
                "with no spaces."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_staff"
            )
        )


    if len(password) < 8:

        flash(
            (
                "Staff password must contain "
                "at least 8 characters."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_staff"
            )
        )


    existing = (
        StaffAccount.query
        .filter_by(
            username=
                username
        )
        .first()
    )


    if existing:

        flash(
            "That staff username is already in use.",
            "error",
        )

        return redirect(
            url_for(
                "admin_staff"
            )
        )


    valid_events = (
        TicketEvent.query
        .filter(
            TicketEvent.organizer_id
            == organizer.id
        )
        .filter(
            TicketEvent.id.in_(
                [
                    int(value)
                    for value in event_ids_raw
                    if str(value).isdigit()
                ]
                or [-1]
            )
        )
        .all()
    )


    if not valid_events:

        flash(
            (
                "Assign this staff member to "
                "at least one of your events."
            ),
            "error",
        )

        return redirect(
            url_for(
                "admin_staff"
            )
        )


    staff = StaffAccount(

        organizer_id=
            organizer.id,

        name=
            name,

        username=
            username,

        active=
            True,
    )


    staff.set_password(
        password
    )


    db.session.add(
        staff
    )

    db.session.flush()


    for event in valid_events:

        db.session.add(
            StaffEventAccess(
                staff_id=
                    staff.id,
                event_id=
                    event.id,
            )
        )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Staff] Creation failed "
                "organizer_id=%s error=%s"
            ),
            organizer.id,
            error,
        )

        flash(
            "Unable to create staff account.",
            "error",
        )

        return redirect(
            url_for(
                "admin_staff"
            )
        )


    flash(
        (
            f"Staff account created for {name}. "
            "They can now sign in at /staff/login."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_staff"
        )
    )


@app.route(
    "/admin/staff/<int:staff_id>/edit",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_staff_edit(
    staff_id,
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


    staff = (
        StaffAccount.query
        .filter_by(
            id=
                staff_id,
            organizer_id=
                organizer.id,
        )
        .first_or_404()
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
            TicketEvent.event_date.desc(),
            TicketEvent.created_at.desc(),
        )
        .all()
    )


    if request.method == "POST":

        name = (
            request.form.get(
                "name",
                "",
            )
            .strip()
        )

        password = (
            request.form.get(
                "password",
                ""
            )
        )

        event_ids = {
            int(value)
            for value
            in request.form.getlist(
                "event_ids"
            )
            if str(value).isdigit()
        }


        valid_event_ids = {
            event.id
            for event in events
            if event.id in event_ids
        }


        if not name:

            flash(
                "Staff name is required.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_staff_edit",
                    staff_id=
                        staff.id,
                )
            )


        if not valid_event_ids:

            flash(
                "Assign at least one event.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_staff_edit",
                    staff_id=
                        staff.id,
                )
            )


        if password and len(
            password
        ) < 8:

            flash(
                (
                    "New password must contain "
                    "at least 8 characters."
                ),
                "error",
            )

            return redirect(
                url_for(
                    "admin_staff_edit",
                    staff_id=
                        staff.id,
                )
            )


        staff.name = (
            name
        )


        if password:

            staff.set_password(
                password
            )


        StaffEventAccess.query.filter_by(
            staff_id=
                staff.id
        ).delete(
            synchronize_session=
                False
        )


        for event_id in sorted(
            valid_event_ids
        ):

            db.session.add(
                StaffEventAccess(
                    staff_id=
                        staff.id,
                    event_id=
                        event_id,
                )
            )


        try:

            db.session.commit()


        except Exception as error:

            db.session.rollback()

            current_app.logger.exception(
                (
                    "[Staff] Update failed "
                    "organizer_id=%s staff_id=%s error=%s"
                ),
                organizer.id,
                staff.id,
                error,
            )

            flash(
                "Unable to update staff account.",
                "error",
            )

            return redirect(
                url_for(
                    "admin_staff_edit",
                    staff_id=
                        staff.id,
                )
            )


        flash(
            "Staff account updated.",
            "success",
        )


        return redirect(
            url_for(
                "admin_staff"
            )
        )


    return render_template(
        "admin/staff_edit.html",

        organizer=
            organizer,

        staff=
            staff,

        events=
            events,

        assigned_event_ids=
            set(
                staff.assigned_event_ids
            ),
    )


@app.route(
    "/admin/staff/<int:staff_id>/toggle",
    methods=[
        "POST",
    ],
)
def admin_staff_toggle(
    staff_id,
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


    staff = (
        StaffAccount.query
        .filter_by(
            id=
                staff_id,
            organizer_id=
                organizer.id,
        )
        .first_or_404()
    )


    staff.active = (
        not staff.active
    )


    db.session.commit()


    flash(
        (
            f"{staff.name} is now "
            f"{'active' if staff.active else 'disabled'}."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_staff"
        )
    )


# ============================================================
# STAFF LOGIN / LOGOUT
# ============================================================

@app.route(
    "/staff/login",
    methods=[
        "GET",
        "POST",
    ],
)
def staff_login():

    if get_current_staff():

        return redirect(
            url_for(
                "staff_dashboard"
            )
        )


    if request.method == "POST":

        username = (
            normalize_staff_username(
                request.form.get(
                    "username",
                    "",
                )
            )
        )

        password = (
            request.form.get(
                "password",
                ""
            )
        )


        staff = (
            StaffAccount.query
            .filter_by(
                username=
                    username,
            )
            .first()
        )


        if (
            not staff
            or not staff.active
            or not staff.check_password(
                password
            )
        ):

            flash(
                "Invalid staff login details.",
                "error",
            )

            return render_template(
                "staff/login.html"
            )


        if (
            not staff.organizer
            or not staff.organizer.is_subscription_active
        ):

            flash(
                (
                    "This organizer's Kalxa subscription "
                    "is not currently active."
                ),
                "error",
            )

            return render_template(
                "staff/login.html"
            )


        session.clear()

        session[
            STAFF_SESSION_KEY
        ] = (
            staff.id
        )


        staff.last_login_at = (
            datetime.utcnow()
        )

        db.session.commit()


        return redirect(
            url_for(
                "staff_dashboard"
            )
        )


    return render_template(
        "staff/login.html"
    )


@app.route(
    "/staff/logout"
)
def staff_logout():

    session.clear()

    return redirect(
        url_for(
            "staff_login"
        )
    )

@app.route(
    "/staff"
)
def staff_dashboard():

    auth = require_staff_account()
    if auth:
        return auth

    staff = get_current_staff()
    event_ids = get_staff_event_ids(staff)

    events = (
        TicketEvent.query
        .filter(
            TicketEvent.id.in_(
                event_ids or [-1]
            )
        )
        .order_by(
            TicketEvent.event_date.asc(),
            TicketEvent.event_time.asc(),
        )
        .all()
    )

    event_rows = []

    for event in events:

        passes = (
            EntryPass.query
            .join(
                TicketOrder,
                EntryPass.order_id
                == TicketOrder.id,
            )
            .filter(
                TicketOrder.event_id
                == event.id,
                TicketOrder.payment_status
                == "paid",
            )
            .all()
        )

        total = len(passes)
        checked_in = sum(
            1
            for entry_pass in passes
            if entry_pass.is_used
        )

        groups = {}

        for entry_pass in passes:
            ticket_name = (
                entry_pass.ticket_type_name
                or "General"
            )

            if ticket_name not in groups:
                groups[ticket_name] = {
                    "name": ticket_name,
                    "total": 0,
                    "checked_in": 0,
                    "remaining": 0,
                }

            groups[ticket_name]["total"] += 1

            if entry_pass.is_used:
                groups[ticket_name]["checked_in"] += 1
            else:
                groups[ticket_name]["remaining"] += 1

        event_rows.append({
            "event": event,
            "total": total,
            "checked_in": checked_in,
            "remaining": max(0, total - checked_in),
            "groups": sorted(
                groups.values(),
                key=lambda row: row["name"].lower(),
            ),
        })

    return render_template(
        "staff/dashboard.html",
        staff=staff,
        events=events,
        event_rows=event_rows,
    )


# ============================================================
# STAFF LIVE GUEST LIST
# ============================================================

@app.route(
    "/staff/events/<int:event_id>/guest-list"
)
def staff_event_guest_list(event_id):

    auth = require_staff_account()
    if auth:
        return auth

    staff = get_current_staff()
    event_ids = get_staff_event_ids(staff)

    if event_id not in set(event_ids or []):
        abort(403)

    event = (
        TicketEvent.query
        .filter_by(
            id=event_id,
            organizer_id=staff.organizer_id,
        )
        .first_or_404()
    )

    q = (
        request.args.get(
           "q",
           "",
        )
        .strip()
    )


    if q:

        like = f"%{q}%"

        base_query = base_query.filter(
          or_(
            EntryPass.entry_code.ilike(
                like
            ),
            EntryPass.attendee_name.ilike(
                like
            ),
            TicketOrder.customer_name.ilike(
                like
            ),
            TicketOrder.customer_phone.ilike(
                like
            ),
            TicketOrder.customer_email.ilike(
                like
            ),
          )
        )

    ticket_type = (
        request.args.get(
            "ticket_type",
            "all",
        )
        .strip()
    )

    status_filter = (
        request.args.get(
            "status",
            "all",
        )
        .strip()
        .lower()
    )

    base_query = (
        EntryPass.query
        .join(
            TicketOrder,
            EntryPass.order_id
            == TicketOrder.id,
        )
        .outerjoin(
            TicketOrderItem,
            EntryPass.order_item_id
            == TicketOrderItem.id,
        )
        .filter(
            TicketOrder.event_id
            == event.id,
            TicketOrder.payment_status
            == "paid",
        )
    )

    all_passes = (
        base_query
        .order_by(
            TicketOrderItem.ticket_name.asc(),
            TicketOrder.customer_name.asc(),
            EntryPass.id.asc(),
        )
        .all()
    )

    ticket_type_names = sorted({
        (
            entry_pass.ticket_type_name
            or "General"
        )
        for entry_pass in all_passes
    }, key=str.lower)

    total_count = len(all_passes)
    checked_in_count = sum(
        1
        for entry_pass in all_passes
        if entry_pass.is_used
    )
    remaining_count = max(
        0,
        total_count - checked_in_count,
    )

    if q:
        like = f"%{q}%"

        base_query = base_query.filter(
            or_(
                EntryPass.entry_code.ilike(like),
                TicketOrder.customer_name.ilike(like),
                TicketOrder.customer_phone.ilike(like),
                TicketOrder.customer_email.ilike(like),
            )
        )

    if ticket_type and ticket_type != "all":
        base_query = base_query.filter(
            TicketOrderItem.ticket_name
            == ticket_type
        )

    if status_filter == "done":
        base_query = base_query.filter(
            or_(
                EntryPass.status == "used",
                EntryPass.checked_in_at.isnot(None),
            )
        )
    elif status_filter == "waiting":
        base_query = base_query.filter(
            EntryPass.status == "valid",
            EntryPass.checked_in_at.is_(None),
        )

    filtered_passes = (
        base_query
        .order_by(
            TicketOrderItem.ticket_name.asc(),
            TicketOrder.customer_name.asc(),
            EntryPass.id.asc(),
        )
        .all()
    )

    grouped_passes = []
    group_map = {}

    for entry_pass in filtered_passes:

        name = (
            entry_pass.ticket_type_name
            or "General"
        )

        if name not in group_map:
            group = {
                "name": name,
                "passes": [],
                "total": 0,
                "checked_in": 0,
                "remaining": 0,
            }
            group_map[name] = group
            grouped_passes.append(group)

        group = group_map[name]
        group["passes"].append(entry_pass)
        group["total"] += 1

        if entry_pass.is_used:
            group["checked_in"] += 1
        else:
            group["remaining"] += 1

    return render_template(
        "staff/guest_list.html",
        staff=staff,
        event=event,
        grouped_passes=grouped_passes,
        ticket_type_names=ticket_type_names,
        total_count=total_count,
        checked_in_count=checked_in_count,
        remaining_count=remaining_count,
        q=q,
        selected_ticket_type=ticket_type,
        selected_status=status_filter,
    )


# ============================================================
# STAFF CHECK-IN — QR / CODE LOOKUP
# ============================================================

@app.route(
    "/staff/checkin",
    methods=[
        "GET",
        "POST",
    ],
)
def staff_checkin():

    auth = require_staff_account()
    if auth:
        return auth

    staff = get_current_staff()
    event_ids = get_staff_event_ids(staff)

    assigned_events = (
        TicketEvent.query
        .filter(
            TicketEvent.id.in_(
                event_ids or [-1]
            )
        )
        .order_by(
            TicketEvent.event_date.asc(),
            TicketEvent.event_time.asc(),
        )
        .all()
    )

    selected_event_id = request.args.get(
        "event_id",
        type=int,
    )

    if request.method == "POST":
        selected_event_id = request.form.get(
            "event_id",
            type=int,
        )

    if (
        selected_event_id
        and selected_event_id
        not in set(event_ids or [])
    ):
        abort(403)

    entry_pass = None
    message = None

    if request.method == "POST":

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

        else:

            entry_code = raw_value.upper()

            if "/TICKET/" in entry_code:
                entry_code = (
                    entry_code
                    .split(
                        "/TICKET/",
                        1,
                    )[1]
                    .split("?", 1)[0]
                    .split("#", 1)[0]
                    .strip()
                )

            lookup = (
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
                    == entry_code,
                    TicketEvent.organizer_id
                    == staff.organizer_id,
                    TicketEvent.id.in_(
                        event_ids or [-1]
                    ),
                )
            )

            if selected_event_id:
                lookup = lookup.filter(
                    TicketEvent.id
                    == selected_event_id
                )

            entry_pass = lookup.first()

            if not entry_pass:
                message = (
                    "Ticket not found for your assigned events."
                )
            elif (
                entry_pass.order.payment_status
                != "paid"
            ):
                message = (
                    "Payment has not been confirmed."
                )
            elif entry_pass.is_used:
                message = (
                    "This ticket has already been used."
                )
            elif not entry_pass.is_valid:
                message = (
                    "This ticket is not valid."
                )

    return render_template(
        "staff/checkin.html",
        staff=staff,
        assigned_events=assigned_events,
        selected_event_id=selected_event_id,
        entry_pass=entry_pass,
        message=message,
    )


@app.route(
    "/staff/checkin/<int:pass_id>",
    methods=["POST"],
)
def staff_confirm_checkin(pass_id):

    auth = require_staff_account()
    if auth:
        return auth

    staff = get_current_staff()
    event_ids = get_staff_event_ids(staff)

    return_event_id = request.form.get(
        "event_id",
        type=int,
    )

    try:

        success, message, entry_pass = (
            perform_ticket_checkin(
                pass_id=pass_id,
                organizer_id=staff.organizer_id,
                checked_in_by=(
                    f"staff:{staff.id}:{staff.username}"
                ),
                staff_account_id=staff.id,
                allowed_event_ids=event_ids,
            )
        )

    except Exception as error:

        db.session.rollback()

        current_app.logger.exception(
            (
                "[Staff Check-In] Failed "
                "staff_id=%s pass_id=%s error=%s"
            ),
            staff.id,
            pass_id,
            error,
        )

        flash(
            "Ticket check-in failed. Please try again.",
            "error",
        )

        if (
            return_event_id
            and return_event_id
            in set(event_ids or [])
        ):
            return redirect(
                url_for(
                    "staff_event_guest_list",
                    event_id=return_event_id,
                )
            )

        return redirect(
            url_for("staff_checkin")
        )

    flash(
        message,
        "success" if success else "error",
    )

    if (
        return_event_id
        and return_event_id
        in set(event_ids or [])
    ):
        return redirect(
            url_for(
                "staff_event_guest_list",
                event_id=return_event_id,
            )
        )

    event_id = (
        entry_pass.event.id
        if entry_pass
        and entry_pass.event
        else None
    )

    return redirect(
        url_for(
            "staff_checkin",
            event_id=event_id,
        )
    )




# ============================================================
# ATTENDEE CRM-LITE HELPERS
# ============================================================

def parse_crm_date(
    value,
):

    value = (
        str(
            value
            or ""
        )
        .strip()
    )


    if not value:

        return None


    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d",
        )


    except ValueError:

        return None


def build_attendee_crm(
    organizer,
    args,
):

    event_id_raw = (
        str(
            args.get(
                "event_id",
                ""
            )
        )
        .strip()
    )

    ticket_type_filter = (
        str(
            args.get(
                "ticket_type",
                ""
            )
        )
        .strip()
    )

    payment_status = (
        str(
            args.get(
                "payment_status",
                "paid",
            )
        )
        .strip()
        .lower()
    )

    checkin_status = (
        str(
            args.get(
                "checkin_status",
                "all",
            )
        )
        .strip()
        .lower()
    )

    search_value = (
        str(
            args.get(
                "q",
                ""
            )
        )
        .strip()
    )

    date_from_raw = (
        str(
            args.get(
                "date_from",
                ""
            )
        )
        .strip()
    )

    date_to_raw = (
        str(
            args.get(
                "date_to",
                ""
            )
        )
        .strip()
    )


    events = (
        TicketEvent.query
        .filter_by(
            organizer_id=
                organizer.id,
        )
        .order_by(
            TicketEvent.event_date.desc(),
            TicketEvent.created_at.desc(),
        )
        .all()
    )


    event_ids = [
        event.id
        for event in events
    ]


    query = (
        TicketOrder.query
        .filter(
            TicketOrder.event_id.in_(
                event_ids
                or [-1]
            )
        )
    )


    selected_event_id = None


    if event_id_raw.isdigit():

        candidate = int(
            event_id_raw
        )

        if candidate in set(
            event_ids
        ):

            selected_event_id = (
                candidate
            )

            query = query.filter(
                TicketOrder.event_id
                == candidate
            )


    if payment_status in {
        "paid",
        "pending",
        "cancelled",
    }:

        query = query.filter(
            TicketOrder.payment_status
            == payment_status
        )

    else:

        payment_status = (
            "all"
        )


    date_from = (
        parse_crm_date(
            date_from_raw
        )
    )

    date_to = (
        parse_crm_date(
            date_to_raw
        )
    )


    if date_from:

        query = query.filter(
            TicketOrder.created_at
            >= date_from
        )


    if date_to:

        query = query.filter(
            TicketOrder.created_at
            < (
                date_to
                + timedelta(
                    days=1
                )
            )
        )


    if search_value:

        pattern = (
            "%"
            + search_value
            + "%"
        )

        query = query.filter(
            or_(
                TicketOrder.customer_name.ilike(
                    pattern
                ),
                TicketOrder.customer_email.ilike(
                    pattern
                ),
                TicketOrder.customer_phone.ilike(
                    pattern
                ),
                TicketOrder.payment_reference.ilike(
                    pattern
                ),
            )
        )


    orders = (
        query
        .order_by(
            TicketOrder.created_at.desc()
        )
        .all()
    )


    rows = []


    for order in orders:

        event = (
            order.event
        )


        if not event:

            continue


        if order.order_items:

            line_items = (
                order.order_items
            )

        else:

            line_items = [
                None
            ]


        for item in line_items:

            ticket_name = (
                item.ticket_name
                if item
                else "General"
            )

            quantity = (
                item.quantity
                if item
                else (
                    order.quantity
                    or 1
                )
            )

            unit_price = (
                item.unit_price
                if item
                else order.ticket_price
            )

            line_total = (
                item.line_total
                if item
                else order.total_amount
            )

            passes = (
                item.entry_passes
                if item
                else order.entry_passes
            )


            checked_in_count = sum(
                1
                for entry_pass in passes
                if entry_pass.is_used
            )


            if checked_in_count <= 0:

                row_checkin_status = (
                    "not_checked_in"
                )

            elif checked_in_count >= quantity:

                row_checkin_status = (
                    "checked_in"
                )

            else:

                row_checkin_status = (
                    "partial"
                )


            if (
                ticket_type_filter
                and ticket_name.casefold()
                != ticket_type_filter.casefold()
            ):

                continue


            if (
                checkin_status
                in {
                    "checked_in",
                    "not_checked_in",
                    "partial",
                }
                and row_checkin_status
                != checkin_status
            ):

                continue


            rows.append(
                {
                    "event":
                        event.title,

                    "event_id":
                        event.id,

                    "customer_name":
                        order.customer_name,

                    "customer_email":
                        order.customer_email
                        or "",

                    "customer_phone":
                        order.customer_phone
                        or "",

                    "booking_reference":
                        order.payment_reference,

                    "ticket_type":
                        ticket_name,

                    "quantity":
                        quantity,

                    "checked_in_count":
                        checked_in_count,

                    "not_checked_in_count":
                        max(
                            0,
                            quantity
                            - checked_in_count,
                        ),

                    "checkin_status":
                        row_checkin_status,

                    "payment_status":
                        order.payment_status,

                    "unit_price":
                        unit_price,

                    "line_total":
                        line_total,

                    "purchase_date":
                        order.created_at,

                    "paid_at":
                        order.paid_at,
                }
            )


    ticket_types = sorted(
        {
            (
                item.ticket_name
                if item
                else "General"
            )
            for order in (
                TicketOrder.query
                .filter(
                    TicketOrder.event_id.in_(
                        event_ids
                        or [-1]
                    )
                )
                .all()
            )
            for item in (
                order.order_items
                or [None]
            )
        },
        key=lambda value:
            value.casefold(),
    )


    filters = {
        "event_id":
            (
                str(
                    selected_event_id
                )
                if selected_event_id
                else ""
            ),

        "ticket_type":
            ticket_type_filter,

        "payment_status":
            payment_status,

        "checkin_status":
            checkin_status,

        "date_from":
            date_from_raw,

        "date_to":
            date_to_raw,

        "q":
            search_value,
    }


    summary = {
        "rows":
            len(
                rows
            ),

        "tickets":
            sum(
                int(
                    row[
                        "quantity"
                    ]
                    or 0
                )
                for row in rows
            ),

        "checked_in":
            sum(
                int(
                    row[
                        "checked_in_count"
                    ]
                    or 0
                )
                for row in rows
            ),

        "revenue":
            sum(
                (
                    Decimal(
                        str(
                            row[
                                "line_total"
                            ]
                            or 0
                        )
                    )
                    for row in rows
                    if row[
                        "payment_status"
                    ] == "paid"
                ),
                Decimal(
                    "0.00"
                ),
            ),
    }


    return {
        "rows":
            rows,

        "events":
            events,

        "ticket_types":
            ticket_types,

        "filters":
            filters,

        "summary":
            summary,
    }


# ============================================================
# ATTENDEE CRM-LITE
# ============================================================

@app.route(
    "/admin/attendees"
)
def admin_attendees():

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


    crm = (
        build_attendee_crm(
            organizer,
            request.args,
        )
    )


    return render_template(
        "admin/attendees.html",

        organizer=
            organizer,

        **crm,
    )


@app.route(
    "/admin/attendees/export.csv"
)
def admin_attendees_export_csv():

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


    crm = (
        build_attendee_crm(
            organizer,
            request.args,
        )
    )


    output = io.StringIO(
        newline=""
    )

    writer = csv.writer(
        output
    )


    writer.writerow(
        [
            "Event",
            "Attendee / Buyer",
            "Email",
            "Phone",
            "Booking Reference",
            "Ticket Type",
            "Quantity",
            "Checked In",
            "Not Checked In",
            "Check-In Status",
            "Payment Status",
            "Unit Price",
            "Line Total",
            "Purchased At",
            "Paid At",
        ]
    )


    for row in crm[
        "rows"
    ]:

        writer.writerow(
            [
                row[
                    "event"
                ],
                row[
                    "customer_name"
                ],
                row[
                    "customer_email"
                ],
                row[
                    "customer_phone"
                ],
                row[
                    "booking_reference"
                ],
                row[
                    "ticket_type"
                ],
                row[
                    "quantity"
                ],
                row[
                    "checked_in_count"
                ],
                row[
                    "not_checked_in_count"
                ],
                row[
                    "checkin_status"
                ],
                row[
                    "payment_status"
                ],
                (
                    f"{Decimal(str(row['unit_price'] or 0)):.2f}"
                ),
                (
                    f"{Decimal(str(row['line_total'] or 0)):.2f}"
                ),
                (
                    row[
                        "purchase_date"
                    ].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if row[
                        "purchase_date"
                    ]
                    else ""
                ),
                (
                    row[
                        "paid_at"
                    ].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if row[
                        "paid_at"
                    ]
                    else ""
                ),
            ]
        )


    filename = (
        "kalxa-attendees-"
        + datetime.utcnow().strftime(
            "%Y%m%d-%H%M"
        )
        + ".csv"
    )


    return Response(
        "\ufeff"
        + output.getvalue(),

        mimetype=(
            "text/csv; charset=utf-8"
        ),

        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


@app.route(
    "/admin/attendees/export.xlsx"
)
def admin_attendees_export_xlsx():

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


    crm = (
        build_attendee_crm(
            organizer,
            request.args,
        )
    )


    workbook = Workbook()

    worksheet = (
        workbook.active
    )

    worksheet.title = (
        "Attendees"
    )


    headers = [
        "Event",
        "Attendee / Buyer",
        "Email",
        "Phone",
        "Booking Reference",
        "Ticket Type",
        "Quantity",
        "Checked In",
        "Not Checked In",
        "Check-In Status",
        "Payment Status",
        "Unit Price",
        "Line Total",
        "Purchased At",
        "Paid At",
    ]


    worksheet.append(
        headers
    )


    for row in crm[
        "rows"
    ]:

        worksheet.append(
            [
                row[
                    "event"
                ],
                row[
                    "customer_name"
                ],
                row[
                    "customer_email"
                ],
                row[
                    "customer_phone"
                ],
                row[
                    "booking_reference"
                ],
                row[
                    "ticket_type"
                ],
                int(
                    row[
                        "quantity"
                    ]
                    or 0
                ),
                int(
                    row[
                        "checked_in_count"
                    ]
                    or 0
                ),
                int(
                    row[
                        "not_checked_in_count"
                    ]
                    or 0
                ),
                row[
                    "checkin_status"
                ],
                row[
                    "payment_status"
                ],
                float(
                    Decimal(
                        str(
                            row[
                                "unit_price"
                            ]
                            or 0
                        )
                    )
                ),
                float(
                    Decimal(
                        str(
                            row[
                                "line_total"
                            ]
                            or 0
                        )
                    )
                ),
                row[
                    "purchase_date"
                ],
                row[
                    "paid_at"
                ],
            ]
        )


    worksheet.freeze_panes = (
        "A2"
    )

    worksheet.auto_filter.ref = (
        worksheet.dimensions
    )


    widths = {
        "A": 28,
        "B": 24,
        "C": 30,
        "D": 18,
        "E": 22,
        "F": 18,
        "G": 12,
        "H": 12,
        "I": 16,
        "J": 18,
        "K": 16,
        "L": 14,
        "M": 14,
        "N": 20,
        "O": 20,
    }


    for column, width in (
        widths.items()
    ):

        worksheet.column_dimensions[
            column
        ].width = width


    for cell in (
        worksheet[
            "L"
        ][1:]
        +
        worksheet[
            "M"
        ][1:]
    ):

        cell.number_format = (
            'R #,##0.00'
        )


    buffer = (
        io.BytesIO()
    )

    workbook.save(
        buffer
    )

    buffer.seek(
        0
    )


    filename = (
        "kalxa-attendees-"
        + datetime.utcnow().strftime(
            "%Y%m%d-%H%M"
        )
        + ".xlsx"
    )


    return send_file(
        buffer,

        as_attachment=
            True,

        download_name=
            filename,

        mimetype=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
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
