"""store event posters in postgres

Revision ID: 8d4f1c2a7b90
Revises: 1b7c9e4f2a61
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "8d4f1c2a7b90"
down_revision = "1b7c9e4f2a61"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "poster_image_data",
                sa.LargeBinary(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "poster_image_mimetype",
                sa.String(
                    length=100
                ),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "poster_image_filename",
                sa.String(
                    length=255
                ),
                nullable=True,
            )
        )


def downgrade():

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.drop_column(
            "poster_image_filename"
        )

        batch_op.drop_column(
            "poster_image_mimetype"
        )

        batch_op.drop_column(
            "poster_image_data"
        )
