# ============================================================
# KALXA TICKETING - MODELS
# ============================================================

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
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
        default=True,
        index=True,
    )


    # ========================================================
    # OPTIONAL KALXA DISCOVERY LINK
    # ========================================================
    #
    # Kalxa Ticketing is now a standalone product.
    #
    # This field is only an optional external reference back
    # to an organizer from Kalxa Discovery.
    #
    # It does NOT determine ownership inside Ticketing.
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


    def __repr__(self):

        return (
            "<Organizer "
            f"id={self.id} "
            f"email={self.email}>"
        )


# ============================================================
# TICKET EVENT
# ============================================================

class TicketEvent(db.Model):

    __tablename__ = "ticket_events"


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # LOCAL TICKETING OWNERSHIP
    # ========================================================
    #
    # IMPORTANT:
    #
    # This is now the REAL ownership relationship inside
    # Kalxa Ticketing.
    #
    # Every new event created through Ticketing belongs to
    # one local Organizer account.
    #
    # nullable=True is intentional during migration so that
    # old production events can continue to exist while they
    # are assigned to organizer accounts.
    # ========================================================

    organizer_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "organizers.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )


    # ========================================================
    # OPTIONAL KALXA DISCOVERY REFERENCES
    # ========================================================
    #
    # These fields are no longer Ticketing ownership fields.
    #
    # They remain only so Ticketing can optionally know which
    # Discovery organizer / content item sent traffic into
    # Ticketing.
    # ========================================================

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


    # ========================================================
    # EVENT INFORMATION
    # ========================================================

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


    # ========================================================
    # ORGANIZER SNAPSHOT
    # ========================================================
    #
    # These are display/contact snapshots.
    #
    # Ownership is determined only by organizer_id.
    # ========================================================

    organizer_name = db.Column(
        db.String(150),
        nullable=True,
    )

    organizer_phone = db.Column(
        db.String(50),
        nullable=True,
    )


    # ========================================================
    # EVENT POSTER
    # ========================================================

    image_url = db.Column(
        db.String(500),
        nullable=True,
    )


    # ========================================================
    # TICKETING
    # ========================================================

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
        default=True,
        index=True,
    )


    # ========================================================
    # CURRENT / MANUAL PAYMENT DETAILS
    # ========================================================
    #
    # These are retained for compatibility with your current
    # manual payment confirmation flow.
    #
    # Later, direct organizer payment-provider configuration
    # should move to Organizer-level settings.
    # ========================================================

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


    # ========================================================
    # OWNERSHIP HELPERS
    # ========================================================

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
    # TICKET HELPERS
    # ========================================================

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
            -
            self.paid_ticket_count,
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


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # EVENT
    # ========================================================

    event_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "ticket_events.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # ========================================================
    # CUSTOMER
    # ========================================================

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


    # ========================================================
    # ORDER
    # ========================================================

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


    # ========================================================
    # PAYMENT
    # ========================================================

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


    # ========================================================
    # OWNERSHIP HELPERS
    # ========================================================

    @property
    def organizer_id(self):

        if not self.event:
            return None

        return (
            self.event.organizer_id
        )


    def belongs_to_organizer(
        self,
        organizer_id,
    ):

        if not self.event:
            return False

        return (
            self.event.belongs_to_organizer(
                organizer_id
            )
        )


    # ========================================================
    # STATUS HELPERS
    # ========================================================

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


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # ORDER
    # ========================================================

    order_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "ticket_orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # ========================================================
    # ENTRY CODE
    # ========================================================

    entry_code = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        index=True,
    )


    # ========================================================
    # STATUS
    # ========================================================

    status = db.Column(
        db.String(30),
        nullable=False,
        default="valid",
        index=True,
    )


    # ========================================================
    # TIMESTAMPS
    # ========================================================

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


    # ========================================================
    # RELATIONSHIPS
    # ========================================================

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


    # ========================================================
    # OWNERSHIP HELPERS
    # ========================================================

    @property
    def event(self):

        if not self.order:
            return None

        return self.order.event


    @property
    def organizer_id(self):

        if not self.event:
            return None

        return (
            self.event.organizer_id
        )


    def belongs_to_organizer(
        self,
        organizer_id,
    ):

        if not self.order:
            return False

        return (
            self.order.belongs_to_organizer(
                organizer_id
            )
        )


    # ========================================================
    # CHECK-IN HELPERS
    # ========================================================

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


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # ENTRY PASS
    # ========================================================

    entry_pass_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "entry_passes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )


    # ========================================================
    # CHECK-IN DETAILS
    # ========================================================

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


    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    entry_pass = db.relationship(
        "EntryPass",
        back_populates="checkins",
    )


    # ========================================================
    # OWNERSHIP HELPERS
    # ========================================================

    @property
    def event(self):

        if not self.entry_pass:
            return None

        return (
            self.entry_pass.event
        )


    @property
    def organizer_id(self):

        if not self.event:
            return None

        return (
            self.event.organizer_id
        )


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
# KALXA AUTH BRIDGE TOKEN
# ============================================================

class KalxaBridgeTokenUse(db.Model):

    __tablename__ = "kalxa_bridge_token_uses"


    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.Integer,
        primary_key=True,
    )


    # ========================================================
    # ONE-TIME TOKEN ID
    # ========================================================

    bridge_id = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
    )


    # ========================================================
    # EXTERNAL DISCOVERY REFERENCES
    # ========================================================

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


    # ========================================================
    # CONSUMED
    # ========================================================

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
