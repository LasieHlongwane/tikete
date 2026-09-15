"""add organizer safe delete to ticket events

Revision ID: a3e72f6c91bd
Revises: 9a61d03c4e72
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "a3e72f6c91bd"
down_revision = "9a61d03c4e72"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "organizer_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=
                    sa.false(),
            )
        )

        batch_op.add_column(
            sa.Column(
                "deleted_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_organizer_deleted"
            ),
            [
                "organizer_deleted",
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_deleted_at"
            ),
            [
                "deleted_at",
            ],
            unique=False,
        )


    # The Python model supplies the ongoing default.
    # Remove the temporary migration-side server default.
    op.alter_column(
        "ticket_events",
        "organizer_deleted",
        server_default=None,
    )


def downgrade():

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_deleted_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_organizer_deleted"
            )
        )

        batch_op.drop_column(
            "deleted_at"
        )

        batch_op.drop_column(
            "organizer_deleted"
        )
