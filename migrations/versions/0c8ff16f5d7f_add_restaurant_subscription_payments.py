"""add restaurant subscription payments

Revision ID: 0c8ff16f5d7f
Revises: 4d0b344a2898
Create Date: 2026-10-02 01:13:42.732672

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "0c8ff16f5d7f"
down_revision = "4d0b344a2898"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # RESTAURANT SUBSCRIPTION PAYMENTS
    # ========================================================
    #
    # This table records payments made by restaurant owners
    # to Kalxa for Restaurant Standard / Premium plans.
    #
    # IMPORTANT:
    #
    # This is separate from:
    #
    #     subscription_payments
    #
    # which belongs to the legacy Organizer/Event SaaS
    # subscription system.
    #
    # It is also separate from:
    #
    #     ticket_orders
    #
    # which records attendee ticket purchases.
    # ========================================================

    op.create_table(

        "restaurant_subscription_payments",


        # ====================================================
        # PRIMARY KEY
        # ====================================================

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),


        # ====================================================
        # RESTAURANT
        # ====================================================

        sa.Column(
            "restaurant_advert_id",
            sa.Integer(),
            nullable=False,
        ),


        # ====================================================
        # ORGANIZER / OWNER
        # ====================================================

        sa.Column(
            "organizer_id",
            sa.Integer(),
            nullable=False,
        ),


        # ====================================================
        # PLAN SNAPSHOT
        # ====================================================

        sa.Column(
            "plan_tier",
            sa.String(
                length=30,
            ),
            nullable=False,
        ),

        sa.Column(
            "plan_name",
            sa.String(
                length=120,
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
            "currency",
            sa.String(
                length=10,
            ),
            nullable=False,
        ),

        sa.Column(
            "period_days",
            sa.Integer(),
            nullable=False,
        ),


        # ====================================================
        # PAYMENT
        # ====================================================

        sa.Column(
            "payment_reference",
            sa.String(
                length=80,
            ),
            nullable=False,
        ),

        sa.Column(
            "payment_method",
            sa.String(
                length=30,
            ),
            nullable=False,
        ),

        sa.Column(
            "payment_status",
            sa.String(
                length=30,
            ),
            nullable=False,
        ),


        # ====================================================
        # PAYSTACK AUDIT
        # ====================================================

        sa.Column(
            "paystack_access_code",
            sa.String(
                length=150,
            ),
            nullable=True,
        ),

        sa.Column(
            "paystack_authorization_url",
            sa.String(
                length=500,
            ),
            nullable=True,
        ),

        sa.Column(
            "paystack_transaction_id",
            sa.String(
                length=100,
            ),
            nullable=True,
        ),

        sa.Column(
            "payment_channel",
            sa.String(
                length=50,
            ),
            nullable=True,
        ),

        sa.Column(
            "payment_verified_at",
            sa.DateTime(),
            nullable=True,
        ),


        # ====================================================
        # PAYMENT CONFIRMATION
        # ====================================================

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
                length=100,
            ),
            nullable=True,
        ),


        # ====================================================
        # SUBSCRIPTION PERIOD SNAPSHOT
        # ====================================================

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


        # ====================================================
        # TIMESTAMPS
        # ====================================================

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


        # ====================================================
        # FOREIGN KEYS
        # ====================================================

        sa.ForeignKeyConstraint(
            [
                "organizer_id",
            ],
            [
                "organizers.id",
            ],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            [
                "restaurant_advert_id",
            ],
            [
                "restaurant_adverts.id",
            ],
            ondelete="CASCADE",
        ),


        # ====================================================
        # PRIMARY KEY
        # ====================================================

        sa.PrimaryKeyConstraint(
            "id",
        ),

    )


    # ========================================================
    # INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_subscription_payments",
        schema=None,
    ) as batch_op:

        # ----------------------------------------------------
        # CREATED AT
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_created_at"
            ),
            [
                "created_at",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # ORGANIZER
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_organizer_id"
            ),
            [
                "organizer_id",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # PAID AT
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_paid_at"
            ),
            [
                "paid_at",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # PAYMENT METHOD
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_method"
            ),
            [
                "payment_method",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # PAYMENT REFERENCE
        # ----------------------------------------------------
        #
        # Every Paystack transaction reference must identify
        # exactly one restaurant subscription payment.
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_reference"
            ),
            [
                "payment_reference",
            ],
            unique=True,
        )


        # ----------------------------------------------------
        # PAYMENT STATUS
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_status"
            ),
            [
                "payment_status",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # PAYMENT VERIFIED AT
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_verified_at"
            ),
            [
                "payment_verified_at",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # PAYSTACK TRANSACTION ID
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_paystack_transaction_id"
            ),
            [
                "paystack_transaction_id",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # PLAN TIER
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_plan_tier"
            ),
            [
                "plan_tier",
            ],
            unique=False,
        )


        # ----------------------------------------------------
        # RESTAURANT
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_restaurant_advert_id"
            ),
            [
                "restaurant_advert_id",
            ],
            unique=False,
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # REMOVE INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_restaurant_advert_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_plan_tier"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_paystack_transaction_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_verified_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_reference"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_payment_method"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_paid_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_organizer_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_subscription_payments_created_at"
            )
        )


    # ========================================================
    # REMOVE TABLE
    # ========================================================

    op.drop_table(
        "restaurant_subscription_payments"
    )