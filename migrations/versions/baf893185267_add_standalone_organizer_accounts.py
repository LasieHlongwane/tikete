"""add standalone organizer accounts

Revision ID: baf893185267
Revises: 601eb0cbe9e8
Create Date: 2026-09-14 13:25:44.057382

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "baf893185267"
down_revision = "601eb0cbe9e8"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # CREATE ORGANIZERS TABLE
    # ========================================================

    op.create_table(
        "organizers",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(
                length=150
            ),
            nullable=False,
        ),

        sa.Column(
            "business_name",
            sa.String(
                length=200
            ),
            nullable=True,
        ),

        sa.Column(
            "email",
            sa.String(
                length=255
            ),
            nullable=False,
        ),

        sa.Column(
            "phone",
            sa.String(
                length=50
            ),
            nullable=True,
        ),

        sa.Column(
            "password_hash",
            sa.String(
                length=255
            ),
            nullable=False,
        ),

        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "kalxa_discovery_organizer_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    # ========================================================
    # ORGANIZER INDEXES
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_active"
            ),
            [
                "active"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_created_at"
            ),
            [
                "created_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_email"
            ),
            [
                "email"
            ],
            unique=True,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_organizers_kalxa_discovery_organizer_id"
            ),
            [
                "kalxa_discovery_organizer_id"
            ],
            unique=True,
        )


    # ========================================================
    # ADD LOCAL ORGANIZER OWNERSHIP TO TICKET EVENTS
    # ========================================================
    #
    # organizer_id stays nullable for this first migration so
    # existing production TicketEvent rows continue to work.
    #
    # All NEW events created by the updated application will
    # receive a real local organizer_id.
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "organizer_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_ticket_events_organizer_id"
            ),
            [
                "organizer_id"
            ],
            unique=False,
        )

        batch_op.create_foreign_key(
            "fk_ticket_events_organizer_id_organizers",
            "organizers",
            [
                "organizer_id"
            ],
            [
                "id"
            ],
            ondelete="RESTRICT",
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # REMOVE ORGANIZER OWNERSHIP FROM TICKET EVENTS
    # ========================================================

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.drop_constraint(
            "fk_ticket_events_organizer_id_organizers",
            type_="foreignkey",
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_ticket_events_organizer_id"
            )
        )

        batch_op.drop_column(
            "organizer_id"
        )


    # ========================================================
    # REMOVE ORGANIZER INDEXES
    # ========================================================

    with op.batch_alter_table(
        "organizers",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_kalxa_discovery_organizer_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_email"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_created_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_organizers_active"
            )
        )


    # ========================================================
    # DROP ORGANIZERS TABLE
    # ========================================================

    op.drop_table(
        "organizers"
    )