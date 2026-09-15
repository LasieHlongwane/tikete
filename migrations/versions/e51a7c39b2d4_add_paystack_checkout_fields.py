"""add paystack checkout audit fields to ticket orders

Revision ID: e51a7c39b2d4
Revises: c7f4a21d908e
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "e51a7c39b2d4"
down_revision = "c7f4a21d908e"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table(
        "ticket_orders",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "payment_provider",
                sa.String(length=30),
                nullable=False,
                server_default="paystack",
            )
        )

        batch_op.add_column(
            sa.Column(
                "processing_fee",
                sa.Numeric(10, 2),
                nullable=False,
                server_default="0",
            )
        )

        batch_op.add_column(
            sa.Column(
                "checkout_amount",
                sa.Numeric(10, 2),
                nullable=True,
            )
        )

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
            "ix_ticket_orders_payment_provider",
            ["payment_provider"],
            unique=False,
        )

        batch_op.create_index(
            "ix_ticket_orders_paystack_transaction_id",
            ["paystack_transaction_id"],
            unique=False,
        )

        batch_op.create_index(
            "ix_ticket_orders_payment_verified_at",
            ["payment_verified_at"],
            unique=False,
        )


    op.alter_column(
        "ticket_orders",
        "payment_provider",
        server_default=None,
    )

    op.alter_column(
        "ticket_orders",
        "processing_fee",
        server_default=None,
    )


def downgrade():

    with op.batch_alter_table(
        "ticket_orders",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_ticket_orders_payment_verified_at"
        )

        batch_op.drop_index(
            "ix_ticket_orders_paystack_transaction_id"
        )

        batch_op.drop_index(
            "ix_ticket_orders_payment_provider"
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

        batch_op.drop_column(
            "checkout_amount"
        )

        batch_op.drop_column(
            "processing_fee"
        )

        batch_op.drop_column(
            "payment_provider"
        )
