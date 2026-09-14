"""add subscription payments

Revision ID: 2198f795d74f
Revises: 8455f51fc958
Create Date: 2026-09-14 18:23:00.218117

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2198f795d74f"
down_revision = "8455f51fc958"
branch_labels = None
depends_on = None


def upgrade():

    # ========================================================
    # SUBSCRIPTION PAYMENTS
    # ========================================================
    #
    # This table records money paid by ORGANIZERS to KALXA
    # for SaaS access.
    #
    # It is deliberately separate from ticket_orders, which
    # records attendee payments for event tickets.
    # ========================================================

    op.create_table(

        "subscription_payments",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "organizer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "plan_name",
            sa.String(
                length=120
            ),
            nullable=False,
        ),

        sa.Column(
            "amount",
            sa.Numeric(
                precision=10,
                scale=2,
            ),
            nullable=False,
        ),

        sa.Column(
            "period_days",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "payment_reference",
            sa.String(
                length=60
            ),
            nullable=False,
        ),

        sa.Column(
            "payment_method",
            sa.String(
                length=30
            ),
            nullable=False,
        ),

        sa.Column(
            "payment_status",
            sa.String(
                length=30
            ),
            nullable=False,
        ),

        sa.Column(
            "paid_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "confirmed_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "confirmed_by",
            sa.String(
                length=100
            ),
            nullable=True,
        ),

        sa.Column(
            "subscription_start",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "subscription_end",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            [
                "organizer_id"
            ],
            [
                "organizers.id"
            ],
            name=(
                "fk_subscription_payments_"
                "organizer_id_organizers"
            ),
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    # ========================================================
    # INDEXES
    # ========================================================

    with op.batch_alter_table(
        "subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_subscription_payments_created_at"
            ),
            [
                "created_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_subscription_payments_organizer_id"
            ),
            [
                "organizer_id"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_subscription_payments_paid_at"
            ),
            [
                "paid_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_subscription_payments_payment_method"
            ),
            [
                "payment_method"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_subscription_payments_payment_reference"
            ),
            [
                "payment_reference"
            ],
            unique=True,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_subscription_payments_payment_status"
            ),
            [
                "payment_status"
            ],
            unique=False,
        )


def downgrade():

    # ========================================================
    # REMOVE INDEXES
    # ========================================================

    with op.batch_alter_table(
        "subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_subscription_payments_payment_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_subscription_payments_payment_reference"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_subscription_payments_payment_method"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_subscription_payments_paid_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_subscription_payments_organizer_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_subscription_payments_created_at"
            )
        )


    # ========================================================
    # REMOVE TABLE
    # ========================================================

    op.drop_table(
        "subscription_payments"
    )
