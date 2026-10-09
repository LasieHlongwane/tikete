
"""Add Yoco subscription payment fields.

Revision ID: f3a31952dbcd
Revises: 0c8ff16f5d7f
Create Date: 2026-10-09 02:46:26.993761

Purpose:
    Add Yoco checkout and payment tracking fields to:

    1. subscription_payments
       - Kalxa account subscriptions

    2. restaurant_subscription_payments
       - Restaurant Standard/Premium subscriptions

    This migration does not modify existing Paystack fields,
    payment records, subscription status, or unrelated tables.
"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# ALEMBIC REVISION IDENTIFIERS
# ============================================================

revision = "f3a31952dbcd"
down_revision = "0c8ff16f5d7f"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # 1. KALXA ACCOUNT SUBSCRIPTION PAYMENTS
    # ========================================================

    with op.batch_alter_table(
        "subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "yoco_checkout_id",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "yoco_checkout_url",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "yoco_payment_id",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "yoco_payment_status",
                sa.String(length=30),
                nullable=True,
            )
        )

        # Unique checkout identifier
        batch_op.create_index(
            "ix_subscription_payments_yoco_checkout_id",
            ["yoco_checkout_id"],
            unique=True,
        )

        # Unique payment identifier
        batch_op.create_index(
            "ix_subscription_payments_yoco_payment_id",
            ["yoco_payment_id"],
            unique=True,
        )

        # Payment status lookup
        batch_op.create_index(
            "ix_subscription_payments_yoco_payment_status",
            ["yoco_payment_status"],
            unique=False,
        )

    # ========================================================
    # 2. RESTAURANT SUBSCRIPTION PAYMENTS
    # ========================================================

    with op.batch_alter_table(
        "restaurant_subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "yoco_checkout_id",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "yoco_checkout_url",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "yoco_payment_id",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "yoco_payment_status",
                sa.String(length=30),
                nullable=True,
            )
        )

        # Unique restaurant checkout identifier
        batch_op.create_index(
            "ix_restaurant_subscription_payments_yoco_checkout_id",
            ["yoco_checkout_id"],
            unique=True,
        )

        # Unique restaurant payment identifier
        batch_op.create_index(
            "ix_restaurant_subscription_payments_yoco_payment_id",
            ["yoco_payment_id"],
            unique=True,
        )

        # Restaurant payment status lookup
        batch_op.create_index(
            "ix_restaurant_subscription_payments_yoco_payment_status",
            ["yoco_payment_status"],
            unique=False,
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # 1. REMOVE RESTAURANT YOCO FIELDS
    # ========================================================

    with op.batch_alter_table(
        "restaurant_subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_restaurant_subscription_payments_yoco_payment_status"
        )

        batch_op.drop_index(
            "ix_restaurant_subscription_payments_yoco_payment_id"
        )

        batch_op.drop_index(
            "ix_restaurant_subscription_payments_yoco_checkout_id"
        )

        batch_op.drop_column(
            "yoco_payment_status"
        )

        batch_op.drop_column(
            "yoco_payment_id"
        )

        batch_op.drop_column(
            "yoco_checkout_url"
        )

        batch_op.drop_column(
            "yoco_checkout_id"
        )

    # ========================================================
    # 2. REMOVE ACCOUNT SUBSCRIPTION YOCO FIELDS
    # ========================================================

    with op.batch_alter_table(
        "subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_subscription_payments_yoco_payment_status"
        )

        batch_op.drop_index(
            "ix_subscription_payments_yoco_payment_id"
        )

        batch_op.drop_index(
            "ix_subscription_payments_yoco_checkout_id"
        )

        batch_op.drop_column(
            "yoco_payment_status"
        )

        batch_op.drop_column(
            "yoco_payment_id"
        )

        batch_op.drop_column(
            "yoco_checkout_url"
        )

        batch_op.drop_column(
            "yoco_checkout_id"
        )
