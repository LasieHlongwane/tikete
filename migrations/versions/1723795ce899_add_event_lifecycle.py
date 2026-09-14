"""add event lifecycle

Revision ID: 1723795ce899
Revises: 2198f795d74f
Create Date: 2026-09-14 21:53:57.477395

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1723795ce899"
down_revision = "2198f795d74f"
branch_labels = None
depends_on = None


def upgrade():

    # ========================================================
    # EVENT LIFECYCLE COLUMNS
    # ========================================================
    #
    # IMPORTANT:
    # Existing events already live in production and were
    # previously treated as public/active.
    #
    # We therefore:
    # 1. Add status + sales_open with temporary server defaults.
    # 2. Backfill existing events as published with sales open.
    # 3. Backfill published_at from created_at where possible.
    # 4. Remove the temporary server defaults.
    #
    # New events will be created as drafts by the application.
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'published'"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "sales_open",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            )
        )

        batch_op.add_column(
            sa.Column(
                "published_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "closed_at",
                sa.DateTime(),
                nullable=True,
            )
        )


    # ========================================================
    # BACKFILL EXISTING EVENTS
    # ========================================================

    op.execute(
        """
        UPDATE ticket_events
        SET
            status = 'published',
            sales_open = true,
            published_at = COALESCE(published_at, created_at)
        """
    )


    # ========================================================
    # REMOVE TEMPORARY DATABASE DEFAULTS
    # ========================================================
    #
    # Application-level defaults now control new events:
    #
    # status = draft
    # sales_open = false
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default=None,
        )

        batch_op.alter_column(
            "sales_open",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )


    # ========================================================
    # INDEXES
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_closed_at"
            ),
            [
                "closed_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_published_at"
            ),
            [
                "published_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_sales_open"
            ),
            [
                "sales_open"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_status"
            ),
            [
                "status"
            ],
            unique=False,
        )


def downgrade():

    # ========================================================
    # REMOVE INDEXES
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_sales_open"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_published_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_closed_at"
            )
        )


    # ========================================================
    # REMOVE EVENT LIFECYCLE COLUMNS
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.drop_column(
            "closed_at"
        )

        batch_op.drop_column(
            "published_at"
        )

        batch_op.drop_column(
            "sales_open"
        )

        batch_op.drop_column(
            "status"
        )
