"""add restaurant advertising

Revision ID: 13e8c543a766
Revises: e71ac408740d
Create Date: 2026-09-19 06:24:10.301065
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "13e8c543a766"
down_revision = "e71ac408740d"
branch_labels = None
depends_on = None


def upgrade():

    # =========================================================
    # RESTAURANT ADVERTS
    # =========================================================

    op.create_table(
        "restaurant_adverts",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "organizer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "business_name",
            sa.String(length=180),
            nullable=False,
        ),

        sa.Column(
            "headline",
            sa.String(length=220),
            nullable=True,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "price_text",
            sa.String(length=80),
            nullable=True,
        ),

        sa.Column(
            "address",
            sa.String(length=300),
            nullable=True,
        ),

        sa.Column(
            "area",
            sa.String(length=150),
            nullable=True,
        ),

        sa.Column(
            "directions_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "whatsapp_number",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "phone_number",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "poster_image_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "poster_cloudinary_public_id",
            sa.String(length=255),
            nullable=True,
        ),

        sa.Column(
            "starts_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "ends_at",
            sa.DateTime(),
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
            ["organizer_id"],
            ["organizers.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    # =========================================================
    # RESTAURANT ADVERT INDEXES
    # =========================================================

    op.create_index(
        "ix_restaurant_adverts_active",
        "restaurant_adverts",
        ["active"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_adverts_area",
        "restaurant_adverts",
        ["area"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_adverts_business_name",
        "restaurant_adverts",
        ["business_name"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_adverts_created_at",
        "restaurant_adverts",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_adverts_ends_at",
        "restaurant_adverts",
        ["ends_at"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_adverts_organizer_id",
        "restaurant_adverts",
        ["organizer_id"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_adverts_starts_at",
        "restaurant_adverts",
        ["starts_at"],
        unique=False,
    )


    # =========================================================
    # RESTAURANT REELS
    # =========================================================

    op.create_table(
        "restaurant_reels",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "advert_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "organizer_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "cloudinary_public_id",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "video_url",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "thumbnail_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "duration_seconds",
            sa.Float(),
            nullable=False,
        ),

        sa.Column(
            "width",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "height",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "file_bytes",
            sa.Integer(),
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
            ["advert_id"],
            ["restaurant_adverts.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["organizer_id"],
            ["organizers.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    # =========================================================
    # RESTAURANT REEL INDEXES
    # =========================================================

    op.create_index(
        "ix_restaurant_reels_active",
        "restaurant_reels",
        ["active"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_reels_advert_id",
        "restaurant_reels",
        ["advert_id"],
        unique=True,
    )

    op.create_index(
        "ix_restaurant_reels_created_at",
        "restaurant_reels",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_reels_organizer_id",
        "restaurant_reels",
        ["organizer_id"],
        unique=False,
    )


def downgrade():

    # =========================================================
    # DROP RESTAURANT REELS
    # =========================================================

    op.drop_index(
        "ix_restaurant_reels_organizer_id",
        table_name="restaurant_reels",
    )

    op.drop_index(
        "ix_restaurant_reels_created_at",
        table_name="restaurant_reels",
    )

    op.drop_index(
        "ix_restaurant_reels_advert_id",
        table_name="restaurant_reels",
    )

    op.drop_index(
        "ix_restaurant_reels_active",
        table_name="restaurant_reels",
    )

    op.drop_table(
        "restaurant_reels"
    )


    # =========================================================
    # DROP RESTAURANT ADVERTS
    # =========================================================

    op.drop_index(
        "ix_restaurant_adverts_starts_at",
        table_name="restaurant_adverts",
    )

    op.drop_index(
        "ix_restaurant_adverts_organizer_id",
        table_name="restaurant_adverts",
    )

    op.drop_index(
        "ix_restaurant_adverts_ends_at",
        table_name="restaurant_adverts",
    )

    op.drop_index(
        "ix_restaurant_adverts_created_at",
        table_name="restaurant_adverts",
    )

    op.drop_index(
        "ix_restaurant_adverts_business_name",
        table_name="restaurant_adverts",
    )

    op.drop_index(
        "ix_restaurant_adverts_area",
        table_name="restaurant_adverts",
    )

    op.drop_index(
        "ix_restaurant_adverts_active",
        table_name="restaurant_adverts",
    )

    op.drop_table(
        "restaurant_adverts"
    )