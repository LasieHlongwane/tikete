"""allow anonymous push subscriptions

Revision ID: 9a61d03c4e72
Revises: 8d4f1c2a7b90
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "9a61d03c4e72"
down_revision = "8d4f1c2a7b90"
branch_labels = None
depends_on = None


def upgrade():

    op.alter_column(
        "push_subscriptions",
        "contact_id",
        existing_type=
            sa.Integer(),
        nullable=True,
    )


def downgrade():

    # Downgrade is safe only when no anonymous rows remain.
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            DELETE FROM push_subscriptions
            WHERE contact_id IS NULL
            """
        )
    )

    op.alter_column(
        "push_subscriptions",
        "contact_id",
        existing_type=
            sa.Integer(),
        nullable=False,
    )
