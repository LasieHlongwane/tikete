"""add organizer ownership to ticketing

Revision ID: 3e3efa0318b7
Revises: e03295bc7029
Create Date: 2026-09-12 15:44:57.619324

"""
from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "3e3efa0318b7"
down_revision = "e03295bc7029"
branch_labels = None
depends_on = None


# ============================================================
# HELPERS
# ============================================================

def get_columns(table_name):

    bind = op.get_bind()

    inspector = sa.inspect(bind)

    return {
        column["name"]
        for column in inspector.get_columns(
            table_name
        )
    }


def get_indexes(table_name):

    bind = op.get_bind()

    inspector = sa.inspect(bind)

    return {
        index["name"]
        for index in inspector.get_indexes(
            table_name
        )
        if index.get("name")
    }


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # CHECKINS
    # ========================================================
    #
    # This index already exists in your current database.
    #
    # Only create it if it is genuinely missing.
    # ========================================================

    checkin_indexes = get_indexes(
        "checkins"
    )

    if (
        "ix_checkins_checked_in_at"
        not in checkin_indexes
    ):

        with op.batch_alter_table(
            "checkins",
            schema=None,
        ) as batch_op:

            batch_op.create_index(
                "ix_checkins_checked_in_at",
                [
                    "checked_in_at",
                ],
                unique=False,
            )


    # ========================================================
    # ENTRY PASSES
    # ========================================================

    entry_pass_indexes = get_indexes(
        "entry_passes"
    )

    if (
        "ix_entry_passes_checked_in_at"
        not in entry_pass_indexes
    ):

        with op.batch_alter_table(
            "entry_passes",
            schema=None,
        ) as batch_op:

            batch_op.create_index(
                "ix_entry_passes_checked_in_at",
                [
                    "checked_in_at",
                ],
                unique=False,
            )


    # ========================================================
    # TICKET EVENTS
    # ========================================================

    ticket_event_columns = get_columns(
        "ticket_events"
    )


    # --------------------------------------------------------
    # ADD ORGANIZER OWNERSHIP
    # --------------------------------------------------------

    if (
        "kalxa_organizer_id"
        not in ticket_event_columns
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.add_column(
                sa.Column(
                    "kalxa_organizer_id",
                    sa.Integer(),
                    nullable=True,
                )
            )


    # --------------------------------------------------------
    # ADD UPDATED_AT
    # --------------------------------------------------------
    #
    # CURRENT_TIMESTAMP ensures existing SQLite rows can
    # receive a value when this NOT NULL column is introduced.
    # ========================================================

    ticket_event_columns = get_columns(
        "ticket_events"
    )

    if (
        "updated_at"
        not in ticket_event_columns
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text(
                        "CURRENT_TIMESTAMP"
                    ),
                )
            )


    # --------------------------------------------------------
    # TICKET EVENT INDEXES
    # --------------------------------------------------------

    ticket_event_indexes = get_indexes(
        "ticket_events"
    )


    if (
        "ix_ticket_events_created_at"
        not in ticket_event_indexes
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.create_index(
                "ix_ticket_events_created_at",
                [
                    "created_at",
                ],
                unique=False,
            )


    ticket_event_indexes = get_indexes(
        "ticket_events"
    )


    if (
        "ix_ticket_events_event_date"
        not in ticket_event_indexes
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.create_index(
                "ix_ticket_events_event_date",
                [
                    "event_date",
                ],
                unique=False,
            )


    ticket_event_indexes = get_indexes(
        "ticket_events"
    )


    if (
        "ix_ticket_events_kalxa_organizer_id"
        not in ticket_event_indexes
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.create_index(
                "ix_ticket_events_kalxa_organizer_id",
                [
                    "kalxa_organizer_id",
                ],
                unique=False,
            )


    # ========================================================
    # TICKET ORDERS
    # ========================================================

    ticket_order_columns = get_columns(
        "ticket_orders"
    )


    # --------------------------------------------------------
    # UPDATED_AT
    # --------------------------------------------------------

    if (
        "updated_at"
        not in ticket_order_columns
    ):

        with op.batch_alter_table(
            "ticket_orders",
            schema=None,
        ) as batch_op:

            batch_op.add_column(
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text(
                        "CURRENT_TIMESTAMP"
                    ),
                )
            )


    # --------------------------------------------------------
    # CREATED_AT INDEX
    # --------------------------------------------------------

    ticket_order_indexes = get_indexes(
        "ticket_orders"
    )


    if (
        "ix_ticket_orders_created_at"
        not in ticket_order_indexes
    ):

        with op.batch_alter_table(
            "ticket_orders",
            schema=None,
        ) as batch_op:

            batch_op.create_index(
                "ix_ticket_orders_created_at",
                [
                    "created_at",
                ],
                unique=False,
            )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # TICKET ORDERS
    # ========================================================

    ticket_order_indexes = get_indexes(
        "ticket_orders"
    )

    ticket_order_columns = get_columns(
        "ticket_orders"
    )


    if (
        "ix_ticket_orders_created_at"
        in ticket_order_indexes
    ):

        with op.batch_alter_table(
            "ticket_orders",
            schema=None,
        ) as batch_op:

            batch_op.drop_index(
                "ix_ticket_orders_created_at"
            )


    ticket_order_columns = get_columns(
        "ticket_orders"
    )


    if (
        "updated_at"
        in ticket_order_columns
    ):

        with op.batch_alter_table(
            "ticket_orders",
            schema=None,
        ) as batch_op:

            batch_op.drop_column(
                "updated_at"
            )


    # ========================================================
    # TICKET EVENTS
    # ========================================================

    ticket_event_indexes = get_indexes(
        "ticket_events"
    )


    if (
        "ix_ticket_events_kalxa_organizer_id"
        in ticket_event_indexes
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.drop_index(
                "ix_ticket_events_kalxa_organizer_id"
            )


    ticket_event_indexes = get_indexes(
        "ticket_events"
    )


    if (
        "ix_ticket_events_event_date"
        in ticket_event_indexes
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.drop_index(
                "ix_ticket_events_event_date"
            )


    ticket_event_indexes = get_indexes(
        "ticket_events"
    )


    if (
        "ix_ticket_events_created_at"
        in ticket_event_indexes
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.drop_index(
                "ix_ticket_events_created_at"
            )


    ticket_event_columns = get_columns(
        "ticket_events"
    )


    if (
        "updated_at"
        in ticket_event_columns
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.drop_column(
                "updated_at"
            )


    ticket_event_columns = get_columns(
        "ticket_events"
    )


    if (
        "kalxa_organizer_id"
        in ticket_event_columns
    ):

        with op.batch_alter_table(
            "ticket_events",
            schema=None,
        ) as batch_op:

            batch_op.drop_column(
                "kalxa_organizer_id"
            )


    # ========================================================
    # IMPORTANT
    #
    # We intentionally DO NOT remove these two indexes:
    #
    # ix_entry_passes_checked_in_at
    # ix_checkins_checked_in_at
    #
    # They existed before this migration in your current
    # database, so this migration should not assume ownership
    # of them.
    # ========================================================
    # ### end Alembic commands ###
