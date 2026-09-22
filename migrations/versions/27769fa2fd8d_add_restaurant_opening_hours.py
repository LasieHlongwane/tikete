"""add restaurant opening hours

Revision ID: 27769fa2fd8d
Revises: dc1c5e87dd37
Create Date: 2026-09-22 04:33:49.475423

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.

revision = "27769fa2fd8d"
down_revision = "dc1c5e87dd37"
branch_labels = None
depends_on = None

def upgrade():


# ========================================================
# RESTAURANT OPENING HOURS
# ========================================================

 op.create_table(
    "restaurant_opening_hours",

    sa.Column(
        "id",
        sa.Integer(),
        nullable=False,
    ),

    sa.Column(
        "restaurant_advert_id",
        sa.Integer(),
        nullable=False,
    ),

    sa.Column(
        "day_of_week",
        sa.String(
            length=10
        ),
        nullable=False,
    ),

    sa.Column(
        "open_time",
        sa.Time(),
        nullable=True,
    ),

    sa.Column(
        "close_time",
        sa.Time(),
        nullable=True,
    ),

    sa.Column(
        "is_closed",
        sa.Boolean(),
        server_default=sa.text(
            "false"
        ),
        nullable=False,
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

    sa.CheckConstraint(
        """
        day_of_week IN (
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
            'sunday'
        )
        """,
        name=
            "ck_restaurant_opening_hour_day",
    ),

    sa.ForeignKeyConstraint(
        [
            "restaurant_advert_id"
        ],
        [
            "restaurant_adverts.id"
        ],
        ondelete="CASCADE",
    ),

    sa.PrimaryKeyConstraint(
        "id"
    ),

    sa.UniqueConstraint(
        "restaurant_advert_id",
        "day_of_week",
        name=
            "uq_restaurant_opening_hour_day",
    ),
 )


# ========================================================
# INDEX
# ========================================================

 op.create_index(
    "ix_restaurant_opening_hours_restaurant_advert_id",
    "restaurant_opening_hours",
    [
        "restaurant_advert_id"
    ],
    unique=False,
 )


def downgrade():


# ========================================================
# REMOVE INDEX
# ========================================================

 op.drop_index(
    "ix_restaurant_opening_hours_restaurant_advert_id",
    table_name=
        "restaurant_opening_hours",
 )


# ========================================================
# REMOVE TABLE
# ========================================================

 op.drop_table(
    "restaurant_opening_hours"
 )

