"""add organizer paystack payment connection

Revision ID: c7f4a21d908e
Revises: a3e72f6c91bd
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa

revision = "c7f4a21d908e"
down_revision = "a3e72f6c91bd"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table("organizers", schema=None) as batch_op:

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
                "payment_setup_status",
                sa.String(length=30),
                nullable=False,
                server_default="not_connected",
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
                "paystack_subaccount_id",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_bank_name",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_bank_code",
                sa.String(length=50),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_account_name",
                sa.String(length=200),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_account_last4",
                sa.String(length=4),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_connected_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_organizers_payment_provider",
            ["payment_provider"],
            unique=False,
        )

        batch_op.create_index(
            "ix_organizers_payment_setup_status",
            ["payment_setup_status"],
            unique=False,
        )

        batch_op.create_index(
            "ix_organizers_paystack_subaccount_code",
            ["paystack_subaccount_code"],
            unique=True,
        )

        batch_op.create_index(
            "ix_organizers_payment_connected_at",
            ["payment_connected_at"],
            unique=False,
        )

    op.alter_column(
        "organizers",
        "payment_provider",
        server_default=None,
    )

    op.alter_column(
        "organizers",
        "payment_setup_status",
        server_default=None,
    )


def downgrade():

    with op.batch_alter_table("organizers", schema=None) as batch_op:

        batch_op.drop_index("ix_organizers_payment_connected_at")
        batch_op.drop_index("ix_organizers_paystack_subaccount_code")
        batch_op.drop_index("ix_organizers_payment_setup_status")
        batch_op.drop_index("ix_organizers_payment_provider")

        batch_op.drop_column("payment_connected_at")
        batch_op.drop_column("payment_account_last4")
        batch_op.drop_column("payment_account_name")
        batch_op.drop_column("payment_bank_code")
        batch_op.drop_column("payment_bank_name")
        batch_op.drop_column("paystack_subaccount_id")
        batch_op.drop_column("paystack_subaccount_code")
        batch_op.drop_column("payment_setup_status")
        batch_op.drop_column("payment_provider")