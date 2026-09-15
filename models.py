# ============================================================
# KALXA TICKETING - MODELS
# ============================================================

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import deferred
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


db = SQLAlchemy()


# ============================================================
# ORGANIZER
# ============================================================

class Organizer(db.Model):

    __tablename__ = "organizers"


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # ACCOUNT DETAILS
    # ========================================================

    name = db.Column(
        db.String(150),
        nullable=False,
    )

    business_name = db.Column(
        db.String(200),
        nullable=True,
    )

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    phone = db.Column(
        db.String(50),
        nullable=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )


    # ========================================================
    # ACCOUNT STATUS
    # ========================================================

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    # ========================================================
    # SUBSCRIPTION / SaaS ACCESS
    # ========================================================
    #
    # Possible subscription_status values:
    #
    # inactive
    # active
    # expired
    # suspended
    #
    # An organizer may still log in and view existing records
    # when inactive/expired. New event creation is controlled
    # by is_subscription_active.
    # ========================================================

    subscription_status = db.Column(
        db.String(30),
        nullable=False,
        default="inactive",
        index=True,
    )

    subscription_started_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    subscription_expires_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    suspended_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    suspension_reason = db.Column(
        db.Text,
        nullable=True,
    )


    # ========================================================
    # OPTIONAL KALXA DISCOVERY LINK
    # ========================================================

    kalxa_discovery_organizer_id = db.Column(
        db.Integer,
        nullable=True,
        unique=True,
        index=True,
    )


    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    events = db.relationship(
        "TicketEvent",
        back_populates="organizer",
        lazy=True,
    )


    subscription_payments = db.relationship(
        "SubscriptionPayment",
        back_populates="organizer",
        lazy=True,
        cascade="all, delete-orphan",
    )


    # ========================================================
    # PASSWORD HELPERS
    # ========================================================

    def set_password(
        self,
        password,
    ):

        self.password_hash = (
            generate_password_hash(
                password
            )
        )


    def check_password(
        self,
        password,
    ):

        if not self.password_hash:
            return False

        return check_password_hash(
            self.password_hash,
            password,
        )


    # ========================================================
    # DISPLAY HELPERS
    # ========================================================

    @property
    def display_name(self):

        return (
            self.business_name
            or self.name
        )


    # ========================================================
    # SUBSCRIPTION HELPERS
    # ========================================================

    @property
    def is_suspended(self):

        return (
            not self.active
            or self.subscription_status
            == "suspended"
        )


    @property
    def is_subscription_active(self):

        if not self.active:
            return False

        if (
            self.subscription_status
            != "active"
        ):
            return False

        if (
            self.subscription_expires_at
            is None
        ):
            return False

        return (
            self.subscription_expires_at
            > datetime.utcnow()
        )


    @property
    def effective_subscription_status(self):

        if self.is_suspended:
            return "suspended"

        if (
            self.subscription_status
            == "active"
            and self.subscription_expires_at
            and self.subscription_expires_at
            <= datetime.utcnow()
        ):
            return "expired"

        return (
            self.subscription_status
            or "inactive"
        )


    @property
    def subscription_days_remaining(self):

        if not self.is_subscription_active:
            return 0

        delta = (
            self.subscription_expires_at
            - datetime.utcnow()
        )

        return max(
            0,
            delta.days,
        )


    def __repr__(self):

        return (
            "<Organizer "
            f"id={self.id} "
            f"email={self.email} "
            f"subscription={self.effective_subscription_status}>"
        )


# ============================================================
# SUBSCRIPTION PAYMENT
# ============================================================
#
# This table records money paid by ORGANIZERS to KALXA for
# software access.
#
# It is completely separate from TicketOrder, which records
# money paid by ATTENDEES to EVENT ORGANIZERS.
# ============================================================

class SubscriptionPayment(db.Model):

    __tablename__ = "subscription_payments"


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # ORGANIZER
    # ========================================================

    organizer_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "organizers.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # ========================================================
    # PLAN SNAPSHOT
    # ========================================================

    plan_name = db.Column(
        db.String(120),
        nullable=False,
        default="Kalxa Organizer Monthly",
    )

    amount = db.Column(
        db.Numeric(
            10,
            2,
        ),
        nullable=False,
    )

    period_days = db.Column(
        db.Integer,
        nullable=False,
        default=30,
    )


    # ========================================================
    # PAYMENT
    # ========================================================

    payment_reference = db.Column(
        db.String(60),
        nullable=False,
        unique=True,
        index=True,
    )

    payment_method = db.Column(
        db.String(30),
        nullable=False,
        default="manual_bank",
        index=True,
    )

    payment_status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True,
    )


    # ========================================================
    # CONFIRMATION / SUBSCRIPTION PERIOD
    # ========================================================

    paid_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    confirmed_at = db.Column(
        db.DateTime,
        nullable=True,
    )

    confirmed_by = db.Column(
        db.String(100),
        nullable=True,
    )

    subscription_start = db.Column(
        db.DateTime,
        nullable=True,
    )

    subscription_end = db.Column(
        db.DateTime,
        nullable=True,
    )


    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


    # ========================================================
    # RELATIONSHIP
    # ========================================================

    organizer = db.relationship(
        "Organizer",
        back_populates="subscription_payments",
    )


    # ========================================================
    # STATUS HELPERS
    # ========================================================

    @property
    def is_pending(self):

        return (
            self.payment_status
            == "pending"
        )


    @property
    def is_paid(self):

        return (
            self.payment_status
            == "paid"
        )


    @property
    def is_cancelled(self):

        return (
            self.payment_status
            == "cancelled"
        )


    def __repr__(self):

        return (
            "<SubscriptionPayment "
            f"id={self.id} "
            f"organizer_id={self.organizer_id} "
            f"reference={self.payment_reference} "
            f"status={self.payment_status}>"
        )


# ============================================================
# TICKET EVENT
# ============================================================

class TicketEvent(db.Model):

    __tablename__ = "ticket_events"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    organizer_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "organizers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )


    kalxa_organizer_id = db.Column(
        db.Integer,
        nullable=True,
        index=True,
    )

    kalxa_content_item_id = db.Column(
        db.Integer,
        nullable=True,
        index=True,
    )


    title = db.Column(
        db.String(200),
        nullable=False,
    )

    description = db.Column(
        db.Text,
        nullable=True,
    )

    venue = db.Column(
        db.String(200),
        nullable=True,
    )

    event_date = db.Column(
        db.Date,
        nullable=True,
        index=True,
    )

    event_time = db.Column(
        db.Time,
        nullable=True,
    )


    organizer_name = db.Column(
        db.String(150),
        nullable=True,
    )

    organizer_phone = db.Column(
        db.String(50),
        nullable=True,
    )


    image_url = db.Column(
        db.String(500),
        nullable=True,
    )


    # Durable event poster stored in PostgreSQL.
    # Deferred so listing queries do not automatically load
    # the potentially large image bytes.
    poster_image_data = deferred(
        db.Column(
            db.LargeBinary,
            nullable=True,
        )
    )

    poster_image_mimetype = db.Column(
        db.String(100),
        nullable=True,
    )

    poster_image_filename = db.Column(
        db.String(255),
        nullable=True,
    )


    ticket_price = db.Column(
        db.Numeric(
            10,
            2,
        ),
        nullable=False,
        default=0,
    )

    ticket_capacity = db.Column(
        db.Integer,
        nullable=True,
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )


    # ========================================================
    # EVENT LIFECYCLE
    # ========================================================
    #
    # Possible status values:
    #
    # draft
    # published
    # closed
    #
    # status controls the event lifecycle.
    #
    # sales_open is separate so a published event can remain
    # publicly visible while ticket sales are temporarily paused.
    # ========================================================

    status = db.Column(
        db.String(30),
        nullable=False,
        default="draft",
        index=True,
    )

    sales_open = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    published_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    closed_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )


    bank_name = db.Column(
        db.String(100),
        nullable=True,
    )

    account_holder = db.Column(
        db.String(150),
        nullable=True,
    )

    account_number = db.Column(
        db.String(100),
        nullable=True,
    )

    branch_code = db.Column(
        db.String(50),
        nullable=True,
    )

    payment_instructions = db.Column(
        db.Text,
        nullable=True,
    )


    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


    organizer = db.relationship(
        "Organizer",
        back_populates="events",
    )

    orders = db.relationship(
        "TicketOrder",
        back_populates="event",
        lazy=True,
        cascade="all, delete-orphan",
    )


    @property
    def has_owner(self):

        return (
            self.organizer_id
            is not None
        )


    def belongs_to_organizer(
        self,
        organizer_id,
    ):

        if organizer_id is None:
            return False

        return (
            self.organizer_id
            == organizer_id
        )


    @property
    def is_linked_to_kalxa(self):

        return (
            self.kalxa_content_item_id
            is not None
        )


    # ========================================================
    # EVENT LIFECYCLE HELPERS
    # ========================================================

    @property
    def is_draft(self):

        return (
            self.status
            == "draft"
        )


    @property
    def is_published(self):

        return (
            self.status
            == "published"
        )


    @property
    def is_closed(self):

        return (
            self.status
            == "closed"
        )


    @property
    def is_public(self):

        return (
            self.status
            == "published"
            and self.active
        )


    @property
    def can_accept_orders(self):

        return (
            self.is_public
            and self.sales_open
            and not self.is_sold_out
        )


    @property
    def lifecycle_label(self):

        if self.status == "published":

            if self.sales_open:
                return "Published · Sales Open"

            return "Published · Sales Paused"

        if self.status == "closed":
            return "Closed"

        return "Draft"


    @property
    def paid_ticket_count(self):

        total = 0

        for order in self.orders:

            if (
                order.payment_status
                == "paid"
            ):

                total += (
                    order.quantity
                    or 0
                )

        return total


    @property
    def pending_ticket_count(self):

        total = 0

        for order in self.orders:

            if (
                order.payment_status
                == "pending"
            ):

                total += (
                    order.quantity
                    or 0
                )

        return total


    @property
    def remaining_tickets(self):

        if self.ticket_capacity is None:
            return None

        return max(
            0,
            self.ticket_capacity
            - self.paid_ticket_count,
        )


    @property
    def is_sold_out(self):

        if self.ticket_capacity is None:
            return False

        return (
            self.remaining_tickets
            <= 0
        )


    @property
    def paid_revenue(self):

        total = 0

        for order in self.orders:

            if (
                order.payment_status
                == "paid"
            ):

                total += (
                    order.total_amount
                    or 0
                )

        return total


    @property
    def checked_in_ticket_count(self):

        total = 0

        for order in self.orders:

            for entry_pass in (
                order.entry_passes
            ):

                if (
                    entry_pass.status
                    == "used"
                    or entry_pass.checked_in_at
                    is not None
                ):

                    total += 1

        return total


    def __repr__(self):

        return (
            "<TicketEvent "
            f"id={self.id} "
            f"organizer_id={self.organizer_id} "
            f"title={self.title}>"
        )


# ============================================================
# TICKET ORDER
# ============================================================

class TicketOrder(db.Model):

    __tablename__ = "ticket_orders"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    event_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "ticket_events.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    customer_name = db.Column(
        db.String(150),
        nullable=False,
    )

    customer_phone = db.Column(
        db.String(50),
        nullable=False,
    )

    customer_email = db.Column(
        db.String(150),
        nullable=True,
    )


    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1,
    )

    ticket_price = db.Column(
        db.Numeric(
            10,
            2,
        ),
        nullable=False,
    )

    total_amount = db.Column(
        db.Numeric(
            10,
            2,
        ),
        nullable=False,
    )


    payment_reference = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    payment_status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True,
    )

    paid_at = db.Column(
        db.DateTime,
        nullable=True,
    )


    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


    event = db.relationship(
        "TicketEvent",
        back_populates="orders",
    )

    entry_passes = db.relationship(
        "EntryPass",
        back_populates="order",
        lazy=True,
        cascade="all, delete-orphan",
    )


    @property
    def organizer_id(self):

        if not self.event:
            return None

        return self.event.organizer_id


    def belongs_to_organizer(
        self,
        organizer_id,
    ):

        if not self.event:
            return False

        return self.event.belongs_to_organizer(
            organizer_id
        )


    @property
    def is_paid(self):

        return (
            self.payment_status
            == "paid"
        )


    @property
    def is_pending(self):

        return (
            self.payment_status
            == "pending"
        )


    @property
    def is_cancelled(self):

        return (
            self.payment_status
            == "cancelled"
        )


    def __repr__(self):

        return (
            "<TicketOrder "
            f"id={self.id} "
            f"event_id={self.event_id} "
            f"payment_status={self.payment_status}>"
        )


# ============================================================
# ENTRY PASS
# ============================================================

class EntryPass(db.Model):

    __tablename__ = "entry_passes"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    order_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "ticket_orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    entry_code = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        index=True,
    )


    status = db.Column(
        db.String(30),
        nullable=False,
        default="valid",
        index=True,
    )


    issued_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    checked_in_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )


    order = db.relationship(
        "TicketOrder",
        back_populates="entry_passes",
    )

    checkins = db.relationship(
        "CheckIn",
        back_populates="entry_pass",
        lazy=True,
        cascade="all, delete-orphan",
    )


    @property
    def event(self):

        if not self.order:
            return None

        return self.order.event


    @property
    def organizer_id(self):

        if not self.event:
            return None

        return self.event.organizer_id


    def belongs_to_organizer(
        self,
        organizer_id,
    ):

        if not self.order:
            return False

        return self.order.belongs_to_organizer(
            organizer_id
        )


    @property
    def is_valid(self):

        return (
            self.status
            == "valid"
            and self.checked_in_at
            is None
        )


    @property
    def is_used(self):

        return (
            self.status
            == "used"
            or self.checked_in_at
            is not None
        )


    def __repr__(self):

        return (
            "<EntryPass "
            f"id={self.id} "
            f"entry_code={self.entry_code} "
            f"status={self.status}>"
        )


# ============================================================
# CHECK-IN AUDIT
# ============================================================

class CheckIn(db.Model):

    __tablename__ = "checkins"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    entry_pass_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "entry_passes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    checked_in_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    checked_in_by = db.Column(
        db.String(100),
        nullable=True,
    )


    entry_pass = db.relationship(
        "EntryPass",
        back_populates="checkins",
    )


    @property
    def event(self):

        if not self.entry_pass:
            return None

        return self.entry_pass.event


    @property
    def organizer_id(self):

        if not self.event:
            return None

        return self.event.organizer_id


    def belongs_to_organizer(
        self,
        organizer_id,
    ):

        if not self.entry_pass:
            return False

        return (
            self.entry_pass
            .belongs_to_organizer(
                organizer_id
            )
        )


    def __repr__(self):

        return (
            "<CheckIn "
            f"id={self.id} "
            f"entry_pass_id={self.entry_pass_id}>"
        )


# ============================================================
# ATTENDEE CONTACT
# ============================================================
#
# A contact is created only when the attendee explicitly opts
# in to future-event notifications.
#
# TicketOrder.customer_phone remains the booking record.
# This table is the reusable consented audience identity.
# ============================================================

class AttendeeContact(db.Model):

    __tablename__ = "attendee_contacts"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    name = db.Column(
        db.String(150),
        nullable=True,
    )

    phone = db.Column(
        db.String(50),
        nullable=True,
    )

    phone_normalized = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        index=True,
    )

    email = db.Column(
        db.String(150),
        nullable=True,
        index=True,
    )


    # ========================================================
    # MARKETING / PUSH CONSENT
    # ========================================================

    notification_consent = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    consented_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )

    opted_out_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )


    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    push_subscriptions = db.relationship(
        "PushSubscription",
        back_populates="contact",
        lazy=True,
        cascade="all, delete-orphan",
    )


    @property
    def is_opted_in(self):

        return (
            self.notification_consent
            and self.opted_out_at
            is None
        )


    def __repr__(self):

        return (
            "<AttendeeContact "
            f"id={self.id} "
            f"phone={self.phone_normalized} "
            f"consent={self.notification_consent}>"
        )


# ============================================================
# PUSH SUBSCRIPTION
# ============================================================
#
# Stores the Firebase Installation ID (FID) for a browser /
# device that has explicitly opted in.
#
# One attendee contact may have multiple devices.
# One FID belongs to only one contact at a time.
# ============================================================

class PushSubscription(db.Model):

    __tablename__ = "push_subscriptions"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    contact_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "attendee_contacts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    firebase_installation_id = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
    )


    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True,
    )


    registered_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    last_seen_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    disabled_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )


    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


    contact = db.relationship(
        "AttendeeContact",
        back_populates="push_subscriptions",
    )


    @property
    def is_active(self):

        return (
            self.active
            and self.disabled_at
            is None
            and self.contact
            and self.contact.is_opted_in
        )


    def __repr__(self):

        return (
            "<PushSubscription "
            f"id={self.id} "
            f"contact_id={self.contact_id} "
            f"active={self.active}>"
        )




# ============================================================
# PUSH NOTIFICATION CAMPAIGN
# ============================================================
#
# One row represents one Super Admin push campaign.
#
# status:
# draft / processing / completed / partial / failed
# ============================================================

class PushCampaign(db.Model):

    __tablename__ = "push_campaigns"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    event_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "ticket_events.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    title = db.Column(
        db.String(120),
        nullable=False,
    )

    body = db.Column(
        db.String(500),
        nullable=False,
    )

    target_url = db.Column(
        db.String(1000),
        nullable=True,
    )


    status = db.Column(
        db.String(30),
        nullable=False,
        default="draft",
        index=True,
    )


    recipient_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    success_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    failure_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )


    created_by = db.Column(
        db.String(100),
        nullable=False,
        default="superadmin",
    )


    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    sent_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )


    event = db.relationship(
        "TicketEvent",
        lazy=True,
    )

    deliveries = db.relationship(
        "PushDelivery",
        back_populates="campaign",
        lazy=True,
        cascade="all, delete-orphan",
    )


    def __repr__(self):

        return (
            "<PushCampaign "
            f"id={self.id} "
            f"status={self.status} "
            f"recipients={self.recipient_count}>"
        )


# ============================================================
# PUSH NOTIFICATION DELIVERY
# ============================================================
#
# Stores one delivery result for one browser/app instance.
# ============================================================

class PushDelivery(db.Model):

    __tablename__ = "push_deliveries"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    campaign_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "push_campaigns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    push_subscription_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "push_subscriptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )


    firebase_installation_id = db.Column(
        db.String(255),
        nullable=False,
        index=True,
    )


    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True,
    )


    firebase_message_id = db.Column(
        db.String(500),
        nullable=True,
    )

    error_message = db.Column(
        db.Text,
        nullable=True,
    )


    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    sent_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
    )


    campaign = db.relationship(
        "PushCampaign",
        back_populates="deliveries",
    )

    push_subscription = db.relationship(
        "PushSubscription",
        lazy=True,
    )


    def __repr__(self):

        return (
            "<PushDelivery "
            f"id={self.id} "
            f"campaign_id={self.campaign_id} "
            f"status={self.status}>"
        )


# ============================================================
# KALXA AUTH BRIDGE TOKEN
# ============================================================

class KalxaBridgeTokenUse(db.Model):

    __tablename__ = "kalxa_bridge_token_uses"


    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    bridge_id = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
    )


    kalxa_organizer_id = db.Column(
        db.Integer,
        nullable=False,
        index=True,
    )

    kalxa_content_item_id = db.Column(
        db.Integer,
        nullable=False,
        index=True,
    )


    consumed_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )


    def __repr__(self):

        return (
            "<KalxaBridgeTokenUse "
            f"bridge_id={self.bridge_id} "
            f"organizer={self.kalxa_organizer_id}>"
        )
