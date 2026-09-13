import io
import os
import secrets
import string
import uuid
from datetime import datetime

import qrcode

from dotenv import load_dotenv

from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired,
)

from flask import (
    Flask,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)

from flask_migrate import Migrate

from models import (
    db,
    TicketEvent,
    TicketOrder,
    EntryPass,
    CheckIn,
    KalxaBridgeTokenUse,
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

app.config["SECRET_KEY"] = (
    os.environ.get(
        "SECRET_KEY"
    )
)


if not app.config["SECRET_KEY"]:

    raise RuntimeError(
        "SECRET_KEY is not configured."
    )


# ============================================================
# DATABASE
# ============================================================

database_url = (
    os.environ.get(
        "DATABASE_URL"
    )
)


if not database_url:

    raise RuntimeError(
        (
            "DATABASE_URL is not configured. "
            "Kalxa Ticketing now requires PostgreSQL."
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

    "pool_pre_ping":
        True,

    "pool_recycle":
        300,
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
# ADMIN AUTH
# ============================================================

def require_admin():

    if not session.get(
        "kalxa_ticketing_admin"
    ):

        return redirect(
            url_for(
                "admin_login"
            )
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
                payment_reference=reference
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
# HOME
# ============================================================

@app.route("/")
def home():

    events = (
        TicketEvent.query
        .filter_by(
            active=True
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
        )
        .first_or_404()
    )


    if request.method == "POST":

        # ====================================================
        # CUSTOMER
        # ====================================================

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


        # ====================================================
        # VALIDATION
        # ====================================================

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


        # ====================================================
        # CAPACITY
        # ====================================================

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


        # ====================================================
        # ORDER TOTAL
        # ====================================================

        ticket_price = (
            event.ticket_price
        )


        total_amount = (
            ticket_price
            *
            quantity
        )


        # ====================================================
        # PAYMENT REFERENCE
        # ====================================================

        reference = (
            generate_payment_reference()
        )


        # ====================================================
        # CREATE ORDER
        # ====================================================

        order = TicketOrder(

            event_id=(
                event.id
            ),

            customer_name=(
                customer_name
            ),

            customer_phone=(
                customer_phone
            ),

            customer_email=(
                customer_email
            ),

            quantity=(
                quantity
            ),

            ticket_price=(
                ticket_price
            ),

            total_amount=(
                total_amount
            ),

            payment_reference=(
                reference
            ),

            payment_status=(
                "pending"
            ),
        )


        db.session.add(
            order
        )


        db.session.commit()


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
# KALXA DISCOVERY → TICKETING BRIDGE
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
        secret_key=bridge_secret,
        salt="kalxa-ticketing-bridge-v1",
    )
    
    
# ============================================================
# KALXA ORGANIZER AUTH BRIDGE
# ============================================================
@app.route(
    "/auth/kalxa",
    methods=["POST"],
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


    # =====================================================
    # VERIFY SIGNATURE + EXPIRY
    # =====================================================
    #
    # Token lifetime:
    #
    # 90 seconds
    #
    # Discovery only needs enough time to redirect the
    # organizer into Ticketing.
    # =====================================================

    try:

        payload = serializer.loads(
            token,
            max_age=90,
        )


    except SignatureExpired:

        flash(
            (
                "Your secure Kalxa Ticketing link "
                "expired. Open Ticketing again "
                "from your Kalxa dashboard."
            ),
            "error",
        )

        return redirect(
            url_for(
                "ticketing_access_error"
            )
        )


    except BadSignature:

        current_app.logger.warning(
            (
                "[Kalxa Bridge] Invalid signed "
                "ticketing token."
            )
        )

        abort(403)


    # =====================================================
    # VALIDATE PAYLOAD
    # =====================================================

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


    organizer_id = (
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
        or organizer_id is None
        or content_item_id is None
    ):

        abort(403)


    try:

        organizer_id = int(
            organizer_id
        )

        content_item_id = int(
            content_item_id
        )

    except (
        TypeError,
        ValueError,
    ):

        abort(403)


    if (
        organizer_id <= 0
        or content_item_id <= 0
    ):

        abort(403)


    # =====================================================
    # ONE-TIME TOKEN PROTECTION
    # =====================================================

    already_used = (
        KalxaBridgeTokenUse.query
        .filter_by(
            bridge_id=bridge_id
        )
        .first()
    )


    if already_used:

        current_app.logger.warning(
            (
                "[Kalxa Bridge] Replayed bridge "
                "token bridge_id=%s"
            ),
            bridge_id,
        )

        abort(403)


    token_use = (
        KalxaBridgeTokenUse(

            bridge_id=(
                bridge_id
            ),

            kalxa_organizer_id=(
                organizer_id
            ),

            kalxa_content_item_id=(
                content_item_id
            ),
        )
    )


    try:

        db.session.add(
            token_use
        )

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Kalxa Bridge] Unable to consume "
                "bridge token error=%s"
            ),
            error,
        )

        abort(403)


    # =====================================================
    # CREATE TICKETING SESSION
    # =====================================================

    session.clear()


    session[
        "kalxa_organizer_id"
    ] = organizer_id


    session[
        "kalxa_content_item_id"
    ] = content_item_id


    current_app.logger.info(
        (
            "[Kalxa Bridge] Organizer authenticated "
            "organizer_id=%s "
            "content_item_id=%s"
        ),
        organizer_id,
        content_item_id,
    )


    # =====================================================
    # CONTINUE TO TICKETING ADMIN DASHBOARD
    # =====================================================
    #
    # The admin dashboard reads:
    #
    # session["kalxa_organizer_id"]
    # session["kalxa_content_item_id"]
    #
    # and uses that secure context to display/create the
    # TicketEvent for the approved Kalxa Discovery event.
    # =====================================================

    return redirect(
        url_for(
            "admin_dashboard"
        )
    )

    
# ============================================================
# CURRENT TICKETING ORGANIZER
# ============================================================

def get_ticketing_organizer_id():

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
# CURRENT KALXA CONTENT ITEM
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

   
        
def require_ticketing_organizer():

    organizer_id = (
        get_ticketing_organizer_id()
    )


    if organizer_id:

        return None


    flash(
        (
            "Open Kalxa Ticketing from your "
            "Kalxa organizer dashboard."
        ),
        "error",
    )


    return redirect(
        url_for(
            "ticketing_access_error"
        )
    )
    
    
# ============================================================
# ORGANIZER TICKETING DASHBOARD
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


    organizer_id = (
        get_ticketing_organizer_id()
    )


    # =====================================================
    # ONLY THIS ORGANIZER'S EVENTS
    # =====================================================

    events = (
        TicketEvent.query
        .filter_by(
            kalxa_organizer_id=(
                organizer_id
            )
        )
        .order_by(
            TicketEvent
            .created_at
            .desc()
        )
        .all()
    )


    # =====================================================
    # ORDERS BELONGING TO THEIR EVENTS
    # =====================================================

    orders = (
        TicketOrder.query
        .join(
            TicketEvent
        )
        .filter(
            TicketEvent.kalxa_organizer_id
            == organizer_id
        )
        .all()
    )


    total_orders = len(
        orders
    )


    paid_orders = sum(
        1
        for order
        in orders
        if (
            order.payment_status
            == "paid"
        )
    )


    checked_in = (
        CheckIn.query
        .join(
            EntryPass
        )
        .join(
            TicketOrder
        )
        .join(
            TicketEvent
        )
        .filter(
            TicketEvent.kalxa_organizer_id
            == organizer_id
        )
        .count()
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
    )
    
    
@app.route(
    "/ticketing/access"
)
def ticketing_access_error():

    return """
    <h2>Kalxa Ticketing</h2>
    <p>
        Please open Ticketing from your
        Kalxa Organizer Dashboard.
    </p>
    """, 401

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
            payment_reference=reference
        )
        .first_or_404()
    )


    return render_template(
        "booking_status.html",
        order=order,
    )


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
            entry_code=entry_code
        )
        .first_or_404()
    )


    return render_template(
        "ticket.html",
        entry_pass=entry_pass,
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
            entry_code=entry_code
        )
        .first_or_404()
    )


    ticket_url = (
        f"{PUBLIC_BASE_URL}"
        f"/ticket/"
        f"{entry_pass.entry_code}"
    )


    image = qrcode.make(
        ticket_url
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
# ADMIN LOGIN
# ============================================================

@app.route(
    "/admin/login",
    methods=[
        "GET",
        "POST",
    ],
)
def admin_login():

    # ========================================================
    # ALREADY LOGGED IN
    # ========================================================

    if session.get(
        "kalxa_ticketing_admin"
    ):

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # LOGIN
    # ========================================================

    if request.method == "POST":

        supplied_password = (
            request.form.get(
                "password",
                "",
            )
            .strip()
        )


        expected_password = (
            os.environ.get(
                "ADMIN_PASSWORD",
                "",
            )
            .strip()
        )


        current_app.logger.info(
            (
                "Admin login attempt. "
                "supplied_length=%s "
                "expected_length=%s"
            ),
            len(supplied_password),
            len(expected_password),
        )


        if (
            expected_password
            and
            secrets.compare_digest(
                supplied_password,
                expected_password,
            )
        ):

            session.clear()


            session[
                "kalxa_ticketing_admin"
            ] = True


            flash(
                "Welcome to Kalxa Ticketing.",
                "success",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        flash(
            "Invalid admin password.",
            "error",
        )


    # ========================================================
    # LOGIN PAGE
    # ========================================================

    return """
    <!DOCTYPE html>
    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <title>
            Kalxa Ticketing Admin
        </title>

        <link
            rel="stylesheet"
            href="/static/css/style.css"
        >

    </head>

    <body class="admin-body">

        <div class="admin-login-card">

            <h1>
                Kalxa Ticketing
            </h1>

            <p>
                Organizer Control Centre
            </p>

            <form method="POST">

                <label>

                    Admin Password

                    <input
                        type="password"
                        name="password"
                        required
                        autocomplete="current-password"
                    >

                </label>

                <button
                    type="submit"
                    class="button"
                >
                    Enter Dashboard
                </button>

            </form>

        </div>

    </body>

    </html>
    """


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.clear()


    return redirect(
        url_for(
            "admin_login"
        )
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route(
    "/admin"
)
def admin_dashboard():

    # ========================================================
    # REQUIRE ORGANIZER SESSION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )


    if auth:
        return auth


    organizer_id = (
        get_ticketing_organizer_id()
    )


    active_content_item_id = (
        get_ticketing_content_item_id()
    )


    # ========================================================
    # CURRENT DISCOVERY EVENT
    # ========================================================
    #
    # This is the ContentItem used when the organizer clicked
    # "Manage Tickets" inside Kalxa Discovery.
    # ========================================================

    current_ticket_event = None


    if active_content_item_id:

        current_ticket_event = (
            TicketEvent.query
            .filter_by(
                kalxa_content_item_id=(
                    active_content_item_id
                ),
                kalxa_organizer_id=(
                    organizer_id
                ),
            )
            .first()
        )


    # ========================================================
    # ORGANIZER EVENTS ONLY
    # ========================================================

    events = (
        TicketEvent.query
        .filter_by(
            kalxa_organizer_id=(
                organizer_id
            )
        )
        .order_by(
            TicketEvent.created_at.desc()
        )
        .all()
    )


    # ========================================================
    # ORGANIZER ORDERS ONLY
    # ========================================================

    organizer_orders = (
        TicketOrder.query
        .join(
            TicketEvent,
            TicketOrder.event_id
            == TicketEvent.id,
        )
        .filter(
            TicketEvent.kalxa_organizer_id
            == organizer_id
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


    # ========================================================
    # ORGANIZER CHECK-INS ONLY
    # ========================================================

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
            TicketEvent.kalxa_organizer_id
            == organizer_id
        )
        .filter(
            EntryPass.status
            == "used"
        )
        .count()
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "admin/dashboard.html",

        events=(
            events
        ),

        total_orders=(
            total_orders
        ),

        paid_orders=(
            paid_orders
        ),

        checked_in=(
            checked_in
        ),

        organizer_id=(
            organizer_id
        ),

        active_content_item_id=(
            active_content_item_id
        ),

        current_ticket_event=(
            current_ticket_event
        ),
    )
# ============================================================
# ADMIN CREATE EVENT
# ============================================================
@app.route(
    "/admin/events/new",
    methods=[
        "POST",
    ],
)
def admin_create_event():

    # ========================================================
    # REQUIRE VERIFIED KALXA ORGANIZER SESSION
    # ========================================================
    #
    # IMPORTANT:
    #
    # This route NO LONGER uses require_admin().
    #
    # Ticket event ownership comes from the secure
    # Discovery -> Ticketing authentication bridge.
    # ========================================================

    auth = require_ticketing_organizer()

    if auth:
        return auth


    kalxa_organizer_id = (
        get_ticketing_organizer_id()
    )


    kalxa_content_item_id = (
        get_ticketing_content_item_id()
    )


    # ========================================================
    # REQUIRE DISCOVERY EVENT CONTEXT
    # ========================================================

    if not kalxa_content_item_id:

        current_app.logger.warning(
            (
                "[Ticketing] Organizer attempted to create "
                "an event without a Kalxa content context. "
                "organizer_id=%s"
            ),
            kalxa_organizer_id,
        )


        flash(
            (
                "Open Ticketing from an approved event "
                "inside your Kalxa Organizer Dashboard."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # DUPLICATE / OWNERSHIP PROTECTION
    # ========================================================
    #
    # One Kalxa Discovery listing should normally create
    # only one TicketEvent.
    #
    # If the content item is already linked to another
    # organizer, something is wrong and access is denied.
    # ========================================================

    existing_event = (
        TicketEvent.query
        .filter_by(
            kalxa_content_item_id=(
                kalxa_content_item_id
            )
        )
        .first()
    )


    if existing_event:

        if (
            existing_event.kalxa_organizer_id
            != kalxa_organizer_id
        ):

            current_app.logger.error(
                (
                    "[Ticketing Security] Content ownership "
                    "collision. "
                    "session_organizer_id=%s "
                    "content_item_id=%s "
                    "existing_event_id=%s "
                    "existing_owner_id=%s"
                ),
                kalxa_organizer_id,
                kalxa_content_item_id,
                existing_event.id,
                existing_event.kalxa_organizer_id,
            )


            abort(403)


        flash(
            (
                "Ticketing has already been created "
                "for this Kalxa event."
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
            "Please enter a valid ticket price.",
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


        if not original_filename:

            flash(
                "Invalid poster filename.",
                "error",
            )


            return redirect(
                url_for(
                    "admin_dashboard"
                )
            )


        # ====================================================
        # VALIDATE FILE EXTENSION
        # ====================================================

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


        # ====================================================
        # UNIQUE FILE NAME
        # ====================================================

        filename = (
            f"{uuid.uuid4().hex}.{extension}"
        )


        # ====================================================
        # UPLOAD DIRECTORY
        # ====================================================

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


        # ====================================================
        # SAVE POSTER
        # ====================================================

        try:

            poster_image.save(
                poster_path
            )


        except Exception as error:

            current_app.logger.exception(
                (
                    "[Ticketing] Failed to save "
                    "event poster. "
                    "organizer_id=%s "
                    "content_item_id=%s "
                    "title=%s "
                    "error=%s"
                ),
                kalxa_organizer_id,
                kalxa_content_item_id,
                title,
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


        # ====================================================
        # PUBLIC STATIC URL
        # ====================================================

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
    # CREATE TICKET EVENT
    # ========================================================
    #
    # SECURITY:
    #
    # Neither kalxa_organizer_id nor kalxa_content_item_id
    # comes from request.form.
    #
    # Both come from the verified session created by the
    # signed Discovery authentication bridge.
    # ========================================================

    event = TicketEvent(

        kalxa_organizer_id=(
            kalxa_organizer_id
        ),

        kalxa_content_item_id=(
            kalxa_content_item_id
        ),


        title=(
            title
        ),


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


        event_date=(
            event_date
        ),


        event_time=(
            event_time
        ),


        # ====================================================
        # ORGANIZER DISPLAY SNAPSHOT
        # ====================================================
        #
        # Ownership is NOT determined from these fields.
        #
        # We leave them empty for now because the secure
        # bridge currently transfers organizer IDs only.
        #
        # Later we can safely transfer organizer display
        # name/phone as signed token claims.
        # ====================================================

        organizer_name=None,

        organizer_phone=None,


        # ====================================================
        # POSTER
        # ====================================================

        image_url=(
            image_url
        ),


        # ====================================================
        # TICKETS
        # ====================================================

        ticket_price=(
            ticket_price
        ),

        ticket_capacity=(
            ticket_capacity
        ),


        # ====================================================
        # PAYMENT DETAILS
        # ====================================================

        bank_name=(
            bank_name
        ),

        account_holder=(
            account_holder
        ),

        account_number=(
            account_number
        ),

        branch_code=(
            branch_code
        ),

        payment_instructions=(
            payment_instructions
        ),


        active=True,
    )


    # ========================================================
    # SAVE EVENT
    # ========================================================

    try:

        db.session.add(
            event
        )


        db.session.commit()


    except Exception as error:

        db.session.rollback()


        # ====================================================
        # DELETE POSTER IF DB SAVE FAILED
        # ====================================================

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
                        "poster after event creation "
                        "failed."
                    )
                )


        current_app.logger.exception(
            (
                "[Ticketing] Failed to create event. "
                "organizer_id=%s "
                "content_item_id=%s "
                "title=%s "
                "error=%s"
            ),
            kalxa_organizer_id,
            kalxa_content_item_id,
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


    # ========================================================
    # SUCCESS LOG
    # ========================================================

    current_app.logger.info(
        (
            "[Ticketing] Ticket event created "
            "event_id=%s "
            "organizer_id=%s "
            "content_item_id=%s"
        ),
        event.id,
        event.kalxa_organizer_id,
        event.kalxa_content_item_id,
    )


    flash(
        "Ticket event created successfully.",
        "success",
    )


    return redirect(
        url_for(
            "admin_dashboard"
        )
    )

# ============================================================
# ADMIN ORDERS
# ============================================================
@app.route(
    "/admin/events/<int:event_id>/orders"
)
def admin_orders(
    event_id,
):

    # ========================================================
    # REQUIRE VERIFIED ORGANIZER SESSION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    organizer_id = (
        get_ticketing_organizer_id()
    )


    # ========================================================
    # FIND EVENT OWNED BY THIS ORGANIZER
    # ========================================================
    #
    # IMPORTANT:
    #
    # Do not:
    #
    # TicketEvent.query.get_or_404(event_id)
    #
    # because that would allow Organizer #7 to manually
    # request Organizer #12's event URL.
    # ========================================================

    event = (
        TicketEvent.query
        .filter_by(
            id=(
                event_id
            ),
            kalxa_organizer_id=(
                organizer_id
            ),
        )
        .first_or_404()
    )


    # ========================================================
    # ORDERS FOR THIS OWNED EVENT ONLY
    # ========================================================

    orders = (
        TicketOrder.query
        .filter_by(
            event_id=(
                event.id
            )
        )
        .order_by(
            TicketOrder.created_at.desc()
        )
        .all()
    )


    current_app.logger.info(
        (
            "[Ticketing Orders] Organizer opened orders "
            "organizer_id=%s "
            "event_id=%s "
            "order_count=%s"
        ),
        organizer_id,
        event.id,
        len(
            orders
        ),
    )


    return render_template(
        "admin/orders.html",

        event=(
            event
        ),

        orders=(
            orders
        ),
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

    # ========================================================
    # REQUIRE VERIFIED ORGANIZER SESSION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    organizer_id = (
        get_ticketing_organizer_id()
    )


    # ========================================================
    # FIND ORDER OWNED BY THIS ORGANIZER
    # ========================================================
    #
    # Ownership chain:
    #
    # TicketOrder
    #     ↓
    # TicketEvent
    #     ↓
    # kalxa_organizer_id
    #
    # This prevents Organizer #7 from manually submitting:
    #
    # /admin/orders/999/mark-paid
    #
    # when order #999 belongs to Organizer #12.
    # ========================================================

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
            TicketEvent.kalxa_organizer_id
            == organizer_id
        )

        .first_or_404()
    )


    # ========================================================
    # DEFENSIVE EVENT CHECK
    # ========================================================

    event = (
        order.event
    )


    if not event:

        current_app.logger.error(
            (
                "[Ticketing Payment] Order has no "
                "event relationship "
                "organizer_id=%s "
                "order_id=%s"
            ),
            organizer_id,
            order.id,
        )


        flash(
            (
                "This order is not linked to a valid "
                "ticket event."
            ),
            "error",
        )


        return redirect(
            url_for(
                "admin_dashboard"
            )
        )


    # ========================================================
    # OWNERSHIP DOUBLE-CHECK
    # ========================================================

    if (
        event.kalxa_organizer_id
        != organizer_id
    ):

        current_app.logger.warning(
            (
                "[Ticketing Security] Cross-organizer "
                "payment confirmation blocked "
                "session_organizer_id=%s "
                "order_id=%s "
                "event_id=%s "
                "event_owner_id=%s"
            ),
            organizer_id,
            order.id,
            event.id,
            event.kalxa_organizer_id,
        )


        abort(403)


    # ========================================================
    # ALREADY PAID
    # ========================================================

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
                event_id=(
                    event.id
                ),
            )
        )


    # ========================================================
    # FINAL CAPACITY CHECK
    # ========================================================

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

            current_app.logger.warning(
                (
                    "[Ticketing Payment] Capacity "
                    "confirmation blocked "
                    "organizer_id=%s "
                    "event_id=%s "
                    "order_id=%s "
                    "quantity=%s "
                    "remaining=%s"
                ),
                organizer_id,
                event.id,
                order.id,
                order.quantity,
                remaining,
            )


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
                    event_id=(
                        event.id
                    ),
                )
            )


    # ========================================================
    # MARK PAID
    # ========================================================

    now = (
        datetime.utcnow()
    )


    order.payment_status = (
        "paid"
    )


    order.paid_at = (
        now
    )


    # ========================================================
    # GENERATE ONE ENTRY PASS PER TICKET
    # ========================================================

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


    # ========================================================
    # DEFENSIVE PASS COUNT CHECK
    # ========================================================
    #
    # If somehow more passes exist than ordered quantity,
    # do not create more.
    # ========================================================

    if (
        passes_to_create
        < 0
    ):

        current_app.logger.warning(
            (
                "[Ticketing Payment] Order has more "
                "entry passes than quantity "
                "organizer_id=%s "
                "order_id=%s "
                "quantity=%s "
                "existing_passes=%s"
            ),
            organizer_id,
            order.id,
            order.quantity,
            existing_pass_count,
        )


        passes_to_create = 0


    # ========================================================
    # CREATE PASSES
    # ========================================================

    for _ in range(
        passes_to_create
    ):

        entry_pass = EntryPass(

            order_id=(
                order.id
            ),

            entry_code=(
                generate_entry_code()
            ),

            status=(
                "valid"
            ),
        )


        db.session.add(
            entry_pass
        )


    # ========================================================
    # SAVE
    # ========================================================

    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Ticketing Payment] Failed to confirm "
                "ticket payment "
                "organizer_id=%s "
                "event_id=%s "
                "order_id=%s "
                "error=%s"
            ),
            organizer_id,
            event.id,
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
                event_id=(
                    event.id
                ),
            )
        )


    # ========================================================
    # SUCCESS LOG
    # ========================================================

    current_app.logger.info(
        (
            "[Ticketing Payment] Payment confirmed "
            "organizer_id=%s "
            "event_id=%s "
            "order_id=%s "
            "quantity=%s "
            "passes_created=%s"
        ),
        organizer_id,
        event.id,
        order.id,
        order.quantity,
        passes_to_create,
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
            event_id=(
                event.id
            ),
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

    # ========================================================
    # REQUIRE VERIFIED ORGANIZER SESSION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    organizer_id = (
        get_ticketing_organizer_id()
    )


    entry_pass = None
    message = None


    # ========================================================
    # ACCEPT:
    #
    # 1. MANUAL ENTRY CODE
    # 2. FULL QR TICKET URL
    # ========================================================

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

                message=(
                    message
                ),
            )


        # ====================================================
        # NORMALIZE
        # ====================================================

        entry_code = (
            raw_value
            .strip()
            .upper()
        )


        # ====================================================
        # EXTRACT CODE FROM FULL TICKET URL
        # ====================================================

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


        # ====================================================
        # LOOK UP PASS + OWNERSHIP CHAIN
        # ====================================================
        #
        # EntryPass
        #    ↓
        # TicketOrder
        #    ↓
        # TicketEvent
        #    ↓
        # kalxa_organizer_id
        #
        # This ensures Organizer #7 can only scan tickets
        # belonging to Organizer #7's own events.
        # ====================================================

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
                TicketEvent.kalxa_organizer_id
                == organizer_id
            )

            .first()
        )


        # ====================================================
        # NOT FOUND / NOT OWNED
        # ====================================================

        if not entry_pass:

            message = (
                "Ticket not found for your events."
            )


            current_app.logger.warning(
                (
                    "[Ticketing Check-In] Ticket lookup "
                    "failed or ownership mismatch "
                    "organizer_id=%s "
                    "entry_code=%s"
                ),
                organizer_id,
                entry_code,
            )


        # ====================================================
        # DEFENSIVE RELATIONSHIP CHECK
        # ====================================================

        elif (
            not entry_pass.order
            or not entry_pass.order.event
        ):

            message = (
                "This ticket record is incomplete."
            )


            current_app.logger.error(
                (
                    "[Ticketing Check-In] Broken ticket "
                    "relationship "
                    "organizer_id=%s "
                    "entry_pass_id=%s"
                ),
                organizer_id,
                entry_pass.id,
            )


        # ====================================================
        # OWNERSHIP DOUBLE-CHECK
        # ====================================================

        elif (
            entry_pass.order.event.kalxa_organizer_id
            != organizer_id
        ):

            entry_pass = None


            message = (
                "Ticket not found for your events."
            )


            current_app.logger.warning(
                (
                    "[Ticketing Security] Cross-organizer "
                    "check-in attempt blocked "
                    "organizer_id=%s "
                    "entry_code=%s"
                ),
                organizer_id,
                entry_code,
            )


        # ====================================================
        # PAYMENT STATUS
        # ====================================================

        elif (
            entry_pass.order.payment_status
            != "paid"
        ):

            message = (
                "Payment has not been confirmed "
                "for this ticket."
            )


        # ====================================================
        # ALREADY USED
        # ====================================================

        elif (
            entry_pass.status
            == "used"
        ):

            message = (
                "This ticket has already been used."
            )


        # ====================================================
        # INVALID STATUS
        # ====================================================

        elif (
            entry_pass.status
            != "valid"
        ):

            message = (
                "This ticket is not valid."
            )


        # ====================================================
        # VALID TICKET
        # ====================================================

        else:

            current_app.logger.info(
                (
                    "[Ticketing Check-In] Valid ticket found "
                    "organizer_id=%s "
                    "event_id=%s "
                    "entry_pass_id=%s "
                    "entry_code=%s"
                ),
                organizer_id,
                entry_pass.order.event.id,
                entry_pass.id,
                entry_pass.entry_code,
            )


    return render_template(
        "admin/checkin.html",

        entry_pass=(
            entry_pass
        ),

        message=(
            message
        ),
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

    # ========================================================
    # REQUIRE VERIFIED ORGANIZER SESSION
    # ========================================================

    auth = (
        require_ticketing_organizer()
    )

    if auth:
        return auth


    organizer_id = (
        get_ticketing_organizer_id()
    )


    # ========================================================
    # FIND PASS OWNED BY THIS ORGANIZER
    # ========================================================
    #
    # SECURITY:
    #
    # Do not use:
    #
    # EntryPass.query.get_or_404(pass_id)
    #
    # because a malicious organizer could manually submit
    # another organizer's pass ID.
    #
    # Ownership chain:
    #
    # EntryPass
    #     ↓
    # TicketOrder
    #     ↓
    # TicketEvent
    #     ↓
    # kalxa_organizer_id
    # ========================================================

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
            TicketEvent.kalxa_organizer_id
            == organizer_id
        )

        .first_or_404()
    )


    # ========================================================
    # DEFENSIVE RELATIONSHIP CHECK
    # ========================================================

    if (
        not entry_pass.order
        or not entry_pass.order.event
    ):

        current_app.logger.error(
            (
                "[Ticketing Check-In] Broken pass "
                "relationship "
                "organizer_id=%s "
                "entry_pass_id=%s"
            ),
            organizer_id,
            entry_pass.id,
        )


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


    # ========================================================
    # OWNERSHIP DOUBLE-CHECK
    # ========================================================

    event = (
        entry_pass.order.event
    )


    if (
        event.kalxa_organizer_id
        != organizer_id
    ):

        current_app.logger.warning(
            (
                "[Ticketing Security] Cross-organizer "
                "check-in blocked "
                "session_organizer_id=%s "
                "entry_pass_id=%s "
                "event_id=%s "
                "event_owner_id=%s"
            ),
            organizer_id,
            entry_pass.id,
            event.id,
            event.kalxa_organizer_id,
        )


        abort(403)


    # ========================================================
    # PAYMENT MUST BE PAID
    # ========================================================

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


    # ========================================================
    # PASS MUST STILL BE VALID
    # ========================================================

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


    # ========================================================
    # CHECK FOR EXISTING CHECK-IN
    # ========================================================
    #
    # This provides another layer of duplicate protection.
    # ========================================================

    existing_checkin = (
        CheckIn.query
        .filter_by(
            entry_pass_id=(
                entry_pass.id
            )
        )
        .first()
    )


    if existing_checkin:

        current_app.logger.warning(
            (
                "[Ticketing Check-In] Duplicate check-in "
                "blocked "
                "organizer_id=%s "
                "entry_pass_id=%s "
                "checkin_id=%s"
            ),
            organizer_id,
            entry_pass.id,
            existing_checkin.id,
        )


        flash(
            "This ticket has already been checked in.",
            "error",
        )


        return redirect(
            url_for(
                "admin_checkin"
            )
        )


    # ========================================================
    # MARK PASS USED
    # ========================================================

    now = (
        datetime.utcnow()
    )


    entry_pass.status = (
        "used"
    )


    entry_pass.checked_in_at = (
        now
    )


    # ========================================================
    # CREATE CHECK-IN AUDIT RECORD
    # ========================================================

    checkin = CheckIn(

        entry_pass_id=(
            entry_pass.id
        ),

        checked_in_at=(
            now
        ),

        checked_in_by=(
            f"organizer:{organizer_id}"
        ),
    )


    db.session.add(
        checkin
    )


    # ========================================================
    # SAVE
    # ========================================================

    try:

        db.session.commit()


    except Exception as error:

        db.session.rollback()


        current_app.logger.exception(
            (
                "[Ticketing Check-In] Ticket check-in "
                "failed "
                "organizer_id=%s "
                "event_id=%s "
                "entry_pass_id=%s "
                "error=%s"
            ),
            organizer_id,
            event.id,
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


    # ========================================================
    # SUCCESS LOG
    # ========================================================

    current_app.logger.info(
        (
            "[Ticketing Check-In] Ticket checked in "
            "organizer_id=%s "
            "event_id=%s "
            "order_id=%s "
            "entry_pass_id=%s"
        ),
        organizer_id,
        event.id,
        entry_pass.order.id,
        entry_pass.id,
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
