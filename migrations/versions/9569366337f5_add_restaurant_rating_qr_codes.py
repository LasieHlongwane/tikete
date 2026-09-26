"""add restaurant rating qr codes

Revision ID: 9569366337f5
Revises: d67c63ab8c39
Create Date: 2026-09-26 10:03:42.581811

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# ALEMBIC REVISION IDENTIFIERS
# ============================================================

revision = "9569366337f5"
down_revision = "d67c63ab8c39"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # --------------------------------------------------------
    # RESTAURANT RATING QR CODES
    # --------------------------------------------------------
    #
    # Permanent QR access points belonging to restaurant
    # adverts.
    #
    # Customers will scan URLs such as:
    #
    # https://tickets.kalxa.co.za/r/KX-A7F92C
    #
    # The public_code is used instead of exposing the
    # restaurant database ID.
    # --------------------------------------------------------

    op.create_table(
        "restaurant_rating_qr_codes",

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
            "public_code",
            sa.String(length=40),
            nullable=False,
        ),

        sa.Column(
            "placement_type",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "placement_label",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "active",
            sa.Boolean(),
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

        sa.ForeignKeyConstraint(
            ["restaurant_advert_id"],
            ["restaurant_adverts.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),
    )

    # --------------------------------------------------------
    # INDEXES
    # --------------------------------------------------------

    op.create_index(
        "ix_restaurant_rating_qr_codes_active",
        "restaurant_rating_qr_codes",
        ["active"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_rating_qr_codes_created_at",
        "restaurant_rating_qr_codes",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_rating_qr_codes_placement_type",
        "restaurant_rating_qr_codes",
        ["placement_type"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_rating_qr_codes_public_code",
        "restaurant_rating_qr_codes",
        ["public_code"],
        unique=True,
    )

    op.create_index(
        "ix_restaurant_rating_qr_codes_restaurant_advert_id",
        "restaurant_rating_qr_codes",
        ["restaurant_advert_id"],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # --------------------------------------------------------
    # DROP INDEXES FIRST
    # --------------------------------------------------------

    op.drop_index(
        "ix_restaurant_rating_qr_codes_restaurant_advert_id",
        table_name="restaurant_rating_qr_codes",
    )

    op.drop_index(
        "ix_restaurant_rating_qr_codes_public_code",
        table_name="restaurant_rating_qr_codes",
    )

    op.drop_index(
        "ix_restaurant_rating_qr_codes_placement_type",
        table_name="restaurant_rating_qr_codes",
    )

    op.drop_index(
        "ix_restaurant_rating_qr_codes_created_at",
        table_name="restaurant_rating_qr_codes",
    )

    op.drop_index(
        "ix_restaurant_rating_qr_codes_active",
        table_name="restaurant_rating_qr_codes",
    )

    # --------------------------------------------------------
    # DROP QR TABLE
    # --------------------------------------------------------

    op.drop_table(
        "restaurant_rating_qr_codes"
    )