"""add individual attendee names to tickets

Revision ID: b31d8f4c6a20
Revises: a91f0c7e3d24
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa

revision = "b31d8f4c6a20"
down_revision = "a91f0c7e3d24"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table(
        "ticket_order_items"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "attendee_names",
                sa.JSON(),
                nullable=True,
            )
        )

    with op.batch_alter_table(
        "entry_passes"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "attendee_name",
                sa.String(length=150),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_entry_passes_attendee_name",
            ["attendee_name"],
            unique=False,
        )

    # Existing tickets inherit the original purchaser name.
    op.execute(
        """
        UPDATE entry_passes AS ep
        SET attendee_name = o.customer_name
        FROM ticket_orders AS o
        WHERE ep.order_id = o.id
          AND ep.attendee_name IS NULL
        """
    )


def downgrade():

    with op.batch_alter_table(
        "entry_passes"
    ) as batch_op:
        batch_op.drop_index(
            "ix_entry_passes_attendee_name"
        )
        batch_op.drop_column(
            "attendee_name"
        )

    with op.batch_alter_table(
        "ticket_order_items"
    ) as batch_op:
        batch_op.drop_column(
            "attendee_names"
        )
