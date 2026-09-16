"""remove legacy event bank transfer fields

Revision ID: f84b6d21c7aa
Revises: e51a7c39b2d4
Create Date: 2026-09-16

This migration removes the old attendee-facing manual bank
transfer configuration from ticket_events.

Organizer settlement is now configured once through Paystack
at the organizer account level.

WARNING:
    The upgrade permanently deletes any values previously
    stored in these five legacy ticket_events columns.
"""

from alembic import op
import sqlalchemy as sa


revision = "f84b6d21c7aa"
down_revision = "e51a7c39b2d4"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.drop_column(
            "payment_instructions"
        )

        batch_op.drop_column(
            "branch_code"
        )

        batch_op.drop_column(
            "account_number"
        )

        batch_op.drop_column(
            "account_holder"
        )

        batch_op.drop_column(
            "bank_name"
        )


def downgrade():

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "bank_name",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "account_holder",
                sa.String(length=150),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "account_number",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "branch_code",
                sa.String(length=50),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "payment_instructions",
                sa.Text(),
                nullable=True,
            )
        )
