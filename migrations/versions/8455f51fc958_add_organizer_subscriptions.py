"""add organizer subscriptions

Revision ID: 8455f51fc958
Revises: baf893185267
Create Date: 2026-09-14 16:12:09.789867

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8455f51fc958"
down_revision = "baf893185267"
branch_labels = None
depends_on = None


def upgrade():

    # ========================================================
    # ORGANIZER SUBSCRIPTION FIELDS
    # ========================================================
    #
    # IMPORTANT:
    #
    # Existing organizer rows already exist in production.
    #
    # subscription_status is NOT NULL, so we temporarily give
    # the new column a database-level default of "inactive".
    #
    # This safely backfills all existing organizers.
    #
    # After the column exists and existing rows are populated,
    # the server default is removed. New organizer defaults are
    # then controlled by the SQLAlchemy Organizer model.
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "subscription_status",
                sa.String(
                    length=30
                ),
                nullable=False,
                server_default=
                    sa.text("'inactive'"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "subscription_started_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "subscription_expires_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "suspended_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "suspension_reason",
                sa.Text(),
                nullable=True,
            )
        )


        # ====================================================
        # INDEXES
        # ====================================================

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_subscription_expires_at"
            ),
            [
                "subscription_expires_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_subscription_status"
            ),
            [
                "subscription_status"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_suspended_at"
            ),
            [
                "suspended_at"
            ],
            unique=False,
        )


    # ========================================================
    # REMOVE TEMPORARY DATABASE DEFAULT
    # ========================================================
    #
    # All existing rows now contain "inactive".
    #
    # The application model controls defaults for future
    # Organizer objects.
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.alter_column(
            "subscription_status",
            existing_type=
                sa.String(
                    length=30
                ),
            nullable=False,
            server_default=None,
        )


def downgrade():

    # ========================================================
    # REMOVE ORGANIZER SUBSCRIPTION FIELDS
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_suspended_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_subscription_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_subscription_expires_at"
            )
        )

        batch_op.drop_column(
            "suspension_reason"
        )

        batch_op.drop_column(
            "suspended_at"
        )

        batch_op.drop_column(
            "subscription_expires_at"
        )

        batch_op.drop_column(
            "subscription_started_at"
        )

        batch_op.drop_column(
            "subscription_status"
        )
