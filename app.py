
# ============================================================
# KALXA TICKETING - APP
# ============================================================

import io
import json
import os
import secrets
import string
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

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
    KalxaBridgeTokenUse,
    Organizer,
    PushCampaign,
    PushDelivery,
    PushSubscription,
    SubscriptionPayment,
    TicketEvent,
    TicketOrder,
    db,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


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

        .join(
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
            AttendeeContact.notification_consent
            .is_(True)
        )

        .filter(
            AttendeeContact.opted_out_at
            .is_(None)
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
                "url":
                    campaign.target_url
                    or "/",

                "campaign_id":
                    str(
                        campaign.id
                    ),
            },

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
# They are separate from attendee ticket-payment bank details.
# Configure the bank fields in Render Environment.
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


    subscriptions = (
        get_active_push_subscriptions()
    )


    if not subscriptions:

        flash(
            (
                "There are currently no active "
                "push-notification subscribers."
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
                organizer.id
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

    events = (
        TicketEvent.query
        .filter_by(
            active=True,
            status="published",
        )
        .order_by(
            TicketEvent.event_date.asc(),
            TicketEvent.created_at.desc(),
        )
        .all()
    )


    return render_template(
        "event.html",
        events=events,
        event=None,
    )


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
            id=event_id,
            active=True,
            status="published",
        )
        .first_or_404()
    )


    if not event.sales_open:

        flash(
            (
                "Ticket sales are currently paused "
                "for this event."
            ),
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
            or None
        )


        quantity = request.form.get(
            "quantity",
            type=int,
        )


        if (
            not customer_name
            or not customer_phone
        ):

            flash(
                (
                    "Name and phone number "
                    "are required."
                ),
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=event,
            )


        if (
            not quantity
            or quantity < 1
            or quantity > 10
        ):

            flash(
                (
                    "Please choose between "
                    "1 and 10 tickets."
                ),
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=event,
            )


        if (
            event.ticket_capacity
            is not None
        ):

            remaining = (
                event.remaining_tickets
            )


            if quantity > remaining:

                flash(
                    (
                        "There are not enough "
                        "tickets remaining."
                    ),
                    "error",
                )

                return render_template(
                    "reserve_ticket.html",
                    event=event,
                )


        ticket_price = (
            event.ticket_price
        )


        total_amount = (
            ticket_price
            *
            quantity
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
                quantity,

            ticket_price=
                ticket_price,

            total_amount=
                total_amount,

            payment_reference=
                reference,

            payment_status=
                "pending",
        )


        try:

            db.session.add(
                order
            )

            db.session.commit()


        except Exception as error:

            db.session.rollback()


            current_app.logger.exception(
                (
                    "[Ticket Order] "
                    "Unable to create order "
                    "event_id=%s error=%s"
                ),
                event.id,
                error,
            )


            flash(
                (
                    "Unable to reserve your tickets. "
                    "Please try again."
                ),
                "error",
            )

            return render_template(
                "reserve_ticket.html",
                event=event,
            )


        return redirect(
            url_for(
                "booking_status",
                reference=reference,
            )
        )


    return render_template(
        "reserve_ticket.html",
        event=event,
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


messaging.onBackgroundMessage(
    (payload) => {{

        const notification =
            payload.notification
            || {{}};

        const data =
            payload.data
            || {{}};

        const title =
            notification.title
            || "Kalxa Ticketing";

        const options = {{

            body:
                notification.body
                || data.body
                || "",

            icon:
                data.icon
                || "/static/icons/lac-192.png",

            badge:
                data.badge
                || "/static/icons/lac-192.png",

            data: {{

                url:
                    data.url
                    || "/",
            }},
        }};


        self.registration.showNotification(
            title,
            options
        );
    }}
);


self.addEventListener(
    "notificationclick",
    (event) => {{

        event.notification.close();


        const targetUrl =
            (
                event.notification.data
                && event.notification.data.url
            )
            || "/";


        event.waitUntil(

            clients.matchAll(
                {{
                    type: "window",
                    includeUncontrolled: true,
                }}
            )
            .then(
                (clientList) => {{

                    for (
                        const client
                        of clientList
                    ) {{

                        if (
                            "focus"
                            in client
                        ) {{

                            client.navigate(
                                targetUrl
                            );

                            return (
                                client.focus()
                            );
                        }}
                    }}


                    if (
                        clients.openWindow
                    ) {{

                        return (
                            clients.openWindow(
                                targetUrl
                            )
                        );
                    }}
                }}
            )
        );
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
    methods=[
        "POST",
    ],
)
def notification_subscribe():

    if not firebase_web_push_configured():

        return {
            "ok": False,
            "error": (
                "Firebase Web Push is not configured."
            ),
        }, 503


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


    if (
        len(
            installation_id
        )
        > 255
    ):

        return {
            "ok": False,
            "error": (
                "Invalid Firebase installation ID."
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


    if not phone_normalized:

        return {
            "ok": False,
            "error": (
                "A valid attendee phone number "
                "is required."
            ),
        }, 400


    now = (
        datetime.utcnow()
    )


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

            name=
                order.customer_name,

            phone=
                order.customer_phone,

            phone_normalized=
                phone_normalized,

            email=
                order.customer_email,

            notification_consent=
                True,

            consented_at=
                now,

            opted_out_at=
                None,
        )


        db.session.add(
            contact
        )

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

        contact.notification_consent = (
            True
        )

        contact.consented_at = (
            now
        )

        contact.opted_out_at = (
            None
        )


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

            contact_id=
                contact.id,

            firebase_installation_id=
                installation_id,

            active=
                True,

            registered_at=
                now,

            last_seen_at=
                now,

            disabled_at=
                None,
        )


        db.session.add(
            subscription
        )


    else:

        subscription.contact_id = (
            contact.id
        )

        subscription.active = (
            True
        )

        subscription.last_seen_at = (
            now
        )

        subscription.disabled_at = (
            None
        )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Push Subscribe] Failed "
                "reference=%s error=%s"
            ),
            reference,
            error,
        )


        return {
            "ok": False,
            "error": (
                "Notification subscription could "
                "not be saved."
            ),
        }, 500


    return {
        "ok": True,
        "message": (
            "Future-event notifications are enabled."
        ),
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
# ORGANIZER - REQUEST SUBSCRIPTION PAYMENT
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
                "Subscription renewal cannot be requested "
                "until the account is reactivated."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_subscription"
            )
        )


    existing_pending = (
        SubscriptionPayment.query
        .filter_by(
            organizer_id=
                organizer.id,

            payment_status=
                "pending",
        )
        .first()
    )


    if existing_pending:

        flash(
            (
                "You already have a pending subscription "
                "payment request. Use the existing payment "
                "reference."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_subscription"
            )
        )


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
            "manual_bank",

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
                "[Subscription] Failed to create "
                "payment request organizer_id=%s error=%s"
            ),
            organizer.id,
            error,
        )


        flash(
            (
                "Unable to create your subscription "
                "payment request. Please try again."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_subscription"
            )
        )


    flash(
        (
            "Subscription payment request created. "
            "Pay using the reference shown below."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin_subscription"
        )
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
            )
            .first()
        )


    events = (
        TicketEvent.query
        .filter_by(
            organizer_id=
                organizer.id
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
    # TICKET PRICE
    # ========================================================

    try:

        ticket_price = float(
            request.form.get(
                "ticket_price",
                0,
            )
            or 0
        )


    except (
        TypeError,
        ValueError,
    ):

        flash(
            (
                "Please enter a valid "
                "ticket price."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    if ticket_price < 0:

        flash(
            "Ticket price cannot be negative.",
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # TICKET CAPACITY
    # ========================================================

    ticket_capacity = (
        request.form.get(
            "ticket_capacity",
            type=int,
        )
    )


    if (
        ticket_capacity is not None
        and ticket_capacity < 1
    ):

        flash(
            (
                "Ticket capacity must be at least "
                "1 when provided."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # EVENT POSTER
    # ========================================================

    poster_image = (
        request.files.get(
            "poster_image"
        )
    )


    image_url = None
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


        if (
            "."
            not in original_filename
        ):

            flash(
                (
                    "Poster must be a JPG, JPEG, "
                    "PNG or WEBP image."
                ),
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


        allowed_extensions = {
            "jpg",
            "jpeg",
            "png",
            "webp",
        }


        if (
            extension
            not in allowed_extensions
        ):

            flash(
                (
                    "Poster must be a JPG, JPEG, "
                    "PNG or WEBP image."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        filename = (
            f"{uuid.uuid4().hex}.{extension}"
        )


        upload_folder = (
            os.path.join(
                current_app.root_path,
                "static",
                "uploads",
                "events",
            )
        )


        os.makedirs(
            upload_folder,
            exist_ok=True,
        )


        poster_path = (
            os.path.join(
                upload_folder,
                filename,
            )
        )


        try:

            poster_image.save(
                poster_path
            )


        except Exception as error:

            current_app.logger.exception(
                (
                    "[Ticketing] Failed to save "
                    "event poster "
                    "organizer_id=%s error=%s"
                ),
                organizer.id,
                error,
            )


            flash(
                (
                    "The event poster could not be "
                    "uploaded. Please try again."
                ),
                "error",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        image_url = (
            url_for(
                "static",
                filename=(
                    f"uploads/events/{filename}"
                ),
            )
        )


    # ========================================================
    # MANUAL PAYMENT / BANK DETAILS
    # ========================================================

    bank_name = (
        request.form.get(
            "bank_name",
            "",
        )
        .strip()
        or None
    )


    account_holder = (
        request.form.get(
            "account_holder",
            "",
        )
        .strip()
        or None
    )


    account_number = (
        request.form.get(
            "account_number",
            "",
        )
        .strip()
        or None
    )


    branch_code = (
        request.form.get(
            "branch_code",
            "",
        )
        .strip()
        or None
    )


    payment_instructions = (
        request.form.get(
            "payment_instructions",
            "",
        )
        .strip()
        or None
    )


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

        event_date=
            event_date,

        event_time=
            event_time,

        organizer_name=
            organizer.display_name,

        organizer_phone=
            organizer.phone,

        image_url=
            image_url,

        ticket_price=
            ticket_price,

        ticket_capacity=
            ticket_capacity,

        bank_name=
            bank_name,

        account_holder=
            account_holder,

        account_number=
            account_number,

        branch_code=
            branch_code,

        payment_instructions=
            payment_instructions,

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
    )


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


        try:

            ticket_price = Decimal(
                str(
                    request.form.get(
                        "ticket_price",
                        "0",
                    )
                    or "0"
                )
            )

        except InvalidOperation:

            flash(
                "Please enter a valid ticket price.",
                "error",
            )

            return render_template(
                "admin/edit_event.html",
                event=
                    event,
            )


        if ticket_price < 0:

            flash(
                "Ticket price cannot be negative.",
                "error",
            )

            return render_template(
                "admin/edit_event.html",
                event=
                    event,
            )


        ticket_capacity = (
            request.form.get(
                "ticket_capacity",
                type=int,
            )
        )


        if (
            ticket_capacity is not None
            and ticket_capacity < 1
        ):

            flash(
                (
                    "Ticket capacity must be at least "
                    "1 when provided."
                ),
                "error",
            )

            return render_template(
                "admin/edit_event.html",
                event=
                    event,
            )


        if (
            ticket_capacity is not None
            and ticket_capacity
            < event.paid_ticket_count
        ):

            flash(
                (
                    "Ticket capacity cannot be lower "
                    "than tickets already sold."
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
                    (
                        "Poster must be a JPG, JPEG, "
                        "PNG or WEBP image."
                    ),
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


            allowed_extensions = {
                "jpg",
                "jpeg",
                "png",
                "webp",
            }


            if extension not in allowed_extensions:

                flash(
                    (
                        "Poster must be a JPG, JPEG, "
                        "PNG or WEBP image."
                    ),
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


            filename = (
                f"{uuid.uuid4().hex}.{extension}"
            )


            upload_folder = (
                os.path.join(
                    current_app.root_path,
                    "static",
                    "uploads",
                    "events",
                )
            )


            os.makedirs(
                upload_folder,
                exist_ok=True,
            )


            new_poster_path = (
                os.path.join(
                    upload_folder,
                    filename,
                )
            )


            try:

                poster_image.save(
                    new_poster_path
                )

            except Exception as error:

                current_app.logger.exception(
                    (
                        "[Ticketing] Failed to update "
                        "event poster event_id=%s error=%s"
                    ),
                    event.id,
                    error,
                )

                flash(
                    "Unable to upload the new poster.",
                    "error",
                )

                return render_template(
                    "admin/edit_event.html",
                    event=
                        event,
                )


            new_image_url = (
                url_for(
                    "static",
                    filename=(
                        f"uploads/events/{filename}"
                    ),
                )
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

        event.event_date = (
            event_date
        )

        event.event_time = (
            event_time
        )

        event.ticket_price = (
            ticket_price
        )

        event.ticket_capacity = (
            ticket_capacity
        )

        event.bank_name = (
            request.form.get(
                "bank_name",
                "",
            )
            .strip()
            or None
        )

        event.account_holder = (
            request.form.get(
                "account_holder",
                "",
            )
            .strip()
            or None
        )

        event.account_number = (
            request.form.get(
                "account_number",
                "",
            )
            .strip()
            or None
        )

        event.branch_code = (
            request.form.get(
                "branch_code",
                "",
            )
            .strip()
            or None
        )

        event.payment_instructions = (
            request.form.get(
                "payment_instructions",
                "",
            )
            .strip()
            or None
        )

        event.organizer_name = (
            organizer.display_name
        )

        event.organizer_phone = (
            organizer.phone
        )


        if new_image_url:

            event.image_url = (
                new_image_url
            )


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


    return render_template(
        "admin/orders.html",

        event=
            event,

        orders=
            orders,
    )


# ============================================================
# MARK PAYMENT PAID
# ============================================================

@app.route(
    "/admin/orders/<int:order_id>/mark-paid",
    methods=[
        "POST",
    ],
)
def admin_mark_paid(
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
        order.payment_status
        == "paid"
    ):

        flash(
            "Order is already marked as paid.",
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
        event.ticket_capacity
        is not None
    ):

        remaining = (
            event.remaining_tickets
        )


        if (
            order.quantity
            > remaining
        ):

            flash(
                (
                    "Cannot confirm payment because "
                    "there are not enough tickets remaining."
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


    now = (
        datetime.utcnow()
    )


    order.payment_status = (
        "paid"
    )


    order.paid_at = (
        now
    )


    existing_pass_count = (
        len(
            order.entry_passes
        )
    )


    passes_to_create = (
        order.quantity
        -
        existing_pass_count
    )


    if (
        passes_to_create
        < 0
    ):

        passes_to_create = 0


    for _ in range(
        passes_to_create
    ):

        entry_pass = EntryPass(

            order_id=
                order.id,

            entry_code=
                generate_entry_code(),

            status=
                "valid",
        )


        db.session.add(
            entry_pass
        )


    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Ticketing Payment] "
                "Failed to confirm ticket payment "
                "organizer_id=%s "
                "order_id=%s "
                "error=%s"
            ),
            organizer.id,
            order.id,
            error,
        )


        flash(
            (
                "Payment confirmation failed. "
                "Please try again."
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
            "Payment confirmed and "
            "entry pass generated."
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
