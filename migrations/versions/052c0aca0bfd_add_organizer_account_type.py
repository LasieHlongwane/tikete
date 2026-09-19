"""add organizer account type

Revision ID: 052c0aca0bfd
Revises: 13e8c543a766
Create Date: 2026-09-19 08:00:20.062324

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '052c0aca0bfd'
down_revision = '13e8c543a766'
branch_labels = None
depends_on = None

def upgrade():

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "account_type",
                sa.String(length=30),
                nullable=False,
                server_default="event",
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_account_type"
            ),
            ["account_type"],
            unique=False,
        )


    # Existing organizers have now received "event".
    #
    # Remove the database-level default because the
    # SQLAlchemy model handles defaults for new rows.
    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.alter_column(
            "account_type",
            server_default=None,
        )


def downgrade():

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_account_type"
            )
        )

        batch_op.drop_column(
            "account_type"
        )
    # ### end Alembic commands ###
