"""add restaurant gallery images

Revision ID: d67c63ab8c39
Revises: 27769fa2fd8d
Create Date: 2026-09-22 08:48:15.805120
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = "d67c63ab8c39"
down_revision = "27769fa2fd8d"
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================
    # RESTAURANT GALLERY IMAGES
    # ========================================================

    op.create_table(
        "restaurant_gallery_images",
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
            "cloudinary_public_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "image_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "image_order",
            sa.Integer(),
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
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_advert_id"],
            ["restaurant_adverts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cloudinary_public_id",
        ),
        sa.UniqueConstraint(
            "restaurant_advert_id",
            "image_order",
            name="uq_restaurant_gallery_image_order",
        ),
    )

    # ========================================================
    # INDEXES
    # ========================================================

    op.create_index(
        "ix_restaurant_gallery_images_created_at",
        "restaurant_gallery_images",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_restaurant_gallery_images_restaurant_advert_id",
        "restaurant_gallery_images",
        ["restaurant_advert_id"],
        unique=False,
    )


def downgrade():
    # ========================================================
    # DROP INDEXES
    # ========================================================

    op.drop_index(
        "ix_restaurant_gallery_images_restaurant_advert_id",
        table_name="restaurant_gallery_images",
    )

    op.drop_index(
        "ix_restaurant_gallery_images_created_at",
        table_name="restaurant_gallery_images",
    )

    # ========================================================
    # DROP TABLE
    # ========================================================

    op.drop_table("restaurant_gallery_images")
