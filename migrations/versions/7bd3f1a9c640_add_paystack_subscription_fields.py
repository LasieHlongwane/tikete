"""add paystack subscription payment audit fields

Revision ID: 7bd3f1a9c640
Revises: 4c8d91a6ef20
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "7bd3f1a9c640"
down_revision = "4c8d91a6ef20"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table(
        "subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "paystack_access_code",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "paystack_authorization_url",
                sa.String(length=500),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "paystack_transaction_id",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_channel",
                sa.String(length=50),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_verified_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_subscription_payments_paystack_transaction_id",
            ["paystack_transaction_id"],
            unique=False,
        )

        batch_op.create_index(
            "ix_subscription_payments_payment_verified_at",
            ["payment_verified_at"],
            unique=False,
        )


def downgrade():

    with op.batch_alter_table(
        "subscription_payments",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_subscription_payments_payment_verified_at"
        )

        batch_op.drop_index(
            "ix_subscription_payments_paystack_transaction_id"
        )

        batch_op.drop_column(
            "payment_verified_at"
        )

        batch_op.drop_column(
            "payment_channel"
        )

        batch_op.drop_column(
            "paystack_transaction_id"
        )

        batch_op.drop_column(
            "paystack_authorization_url"
        )

        batch_op.drop_column(
            "paystack_access_code"
        )
