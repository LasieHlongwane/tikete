
"""add paystack marketplace splits and ticket reservations

Revision ID: 1215a77b8e4b
Revises: 364ea3b211da
Create Date: 2026-10-13 00:55:50.851251

Purpose:
    Add Paystack marketplace split configuration to organisers.

    Record the expected Paystack split and subaccount used
    when each ticket checkout is initialized.

    Add ticket inventory reservation timestamps.

    Prevent a Paystack transaction ID from being assigned
    to multiple ticket orders.

IMPORTANT:
    This migration does not activate organiser payouts,
    create Paystack subaccounts, or reserve inventory.

    Those operations must be implemented separately
    in the application's payment and checkout services.

    Existing organiser accounts remain unverified until
    their Paystack configurations are validated.
"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# ALEMBIC REVISION IDENTIFIERS
# ============================================================

revision = "1215a77b8e4b"

down_revision = "364ea3b211da"

branch_labels = None

depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # 1. ORGANISER PAYSTACK MARKETPLACE CONFIGURATION
    # ========================================================
    #
    # Existing fields retained:
    #
    # payment_provider
    # payment_setup_status
    # paystack_subaccount_code
    # paystack_subaccount_id
    # payment_bank_name
    # payment_bank_code
    # payment_account_name
    # payment_account_last4
    # payment_connected_at
    #
    # New fields:
    #
    # paystack_split_code
    # paystack_split_verified_at
    # paystack_split_status
    #
    # Existing organisers default to "not_configured".
    # No organiser is automatically marked verified.
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "paystack_split_code",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "paystack_split_verified_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "paystack_split_status",
                sa.String(length=30),
                nullable=False,
                server_default="not_configured",
            )
        )

        # Each configured Paystack split belongs to
        # one KALXA organiser.
        #
        # PostgreSQL allows multiple NULL values
        # in this unique index.

        batch_op.create_index(
            "ix_organizers_paystack_split_code",
            ["paystack_split_code"],
            unique=True,
        )

        batch_op.create_index(
            "ix_organizers_paystack_split_status",
            ["paystack_split_status"],
            unique=False,
        )

    # ========================================================
    # 2. TICKET ORDER MARKETPLACE PAYMENT SNAPSHOTS
    # ========================================================
    #
    # These fields preserve the expected split
    # configuration used at checkout initialization.
    #
    # They must not be overwritten simply because
    # an organiser later changes payout settings.
    #
    # They do not independently prove settlement.
    # ========================================================

    with op.batch_alter_table(
        "ticket_orders",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "paystack_split_code",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "paystack_subaccount_code",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "paystack_split_verified_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        # ====================================================
        # 3. TICKET INVENTORY RESERVATION FIELDS
        # ====================================================
        #
        # reservation_expires_at:
        #     Deadline for the temporary reservation.
        #
        # inventory_reserved_at:
        #     When inventory was reserved.
        #
        # inventory_released_at:
        #     When the reservation was explicitly released.
        #
        # NULL values preserve compatibility with
        # historical ticket orders.
        # ====================================================

        batch_op.add_column(
            sa.Column(
                "reservation_expires_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "inventory_reserved_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "inventory_released_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        # ====================================================
        # 4. CREATE LOOKUP INDEXES
        # ====================================================

        batch_op.create_index(
            "ix_ticket_orders_paystack_split_code",
            ["paystack_split_code"],
            unique=False,
        )

        batch_op.create_index(
            "ix_ticket_orders_reservation_expires_at",
            ["reservation_expires_at"],
            unique=False,
        )

        # ====================================================
        # 5. PREVENT PAYSTACK TRANSACTION REUSE
        # ====================================================
        #
        # The TicketOrder model already defines a
        # non-unique index on paystack_transaction_id.
        #
        # This creates an additional partial unique index
        # without removing the existing index.
        #
        # Multiple historical NULL values are permitted.
        #
        # IMPORTANT:
        # Existing duplicate non-NULL transaction IDs
        # must be reconciled before this index is created.
        # ====================================================

        batch_op.create_index(
            "uq_ticket_orders_paystack_transaction_id",
            ["paystack_transaction_id"],
            unique=True,
            postgresql_where=sa.text(
                "paystack_transaction_id IS NOT NULL"
            ),
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # 1. REMOVE TICKET ORDER INDEXES AND FIELDS
    # ========================================================

    with op.batch_alter_table(
        "ticket_orders",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "uq_ticket_orders_paystack_transaction_id"
        )

        batch_op.drop_index(
            "ix_ticket_orders_reservation_expires_at"
        )

        batch_op.drop_index(
            "ix_ticket_orders_paystack_split_code"
        )

        batch_op.drop_column(
            "inventory_released_at"
        )

        batch_op.drop_column(
            "inventory_reserved_at"
        )

        batch_op.drop_column(
            "reservation_expires_at"
        )

        batch_op.drop_column(
            "paystack_split_verified_at"
        )

        batch_op.drop_column(
            "paystack_subaccount_code"
        )

        batch_op.drop_column(
            "paystack_split_code"
        )

    # ========================================================
    # 2. REMOVE ORGANISER SPLIT CONFIGURATION
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_organizers_paystack_split_status"
        )

        batch_op.drop_index(
            "ix_organizers_paystack_split_code"
        )

        batch_op.drop_column(
            "paystack_split_status"
        )

        batch_op.drop_column(
            "paystack_split_verified_at"
        )

        batch_op.drop_column(
            "paystack_split_code"
        )
