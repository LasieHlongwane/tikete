"""support multiple restaurant experience media

Revision ID: ff2b3fee9b72
Revises: e434e38fd761
Create Date: 2026-09-20 23:48:15.027472
"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# ALEMBIC REVISION IDENTIFIERS
# ============================================================

revision = "ff2b3fee9b72"
down_revision = "e434e38fd761"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # 1. CREATE MULTI-MEDIA TABLE
    # ========================================================

    op.create_table(
        "restaurant_experience_media",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "post_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "media_type",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "media_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "cloudinary_public_id",
            sa.String(length=500),
            nullable=False,
        ),

        sa.Column(
            "media_url",
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
            nullable=True,
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
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.ForeignKeyConstraint(
            ["post_id"],
            ["restaurant_experience_posts.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "post_id",
            "media_order",
            name="uq_restaurant_experience_media_order",
        ),
    )


    # ========================================================
    # 2. CREATE INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_media",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_media_cloudinary_public_id"
            ),
            ["cloudinary_public_id"],
            unique=True,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_media_created_at"
            ),
            ["created_at"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_media_media_order"
            ),
            ["media_order"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_media_media_type"
            ),
            ["media_type"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_media_post_id"
            ),
            ["post_id"],
            unique=False,
        )


    # ========================================================
    # 3. MIGRATE EXISTING MEDIA
    #
    # Existing restaurant posts currently contain one media
    # item directly on restaurant_experience_posts.
    #
    # Move that existing media into the new child table before
    # removing the old columns.
    # ========================================================

    op.execute(
        """
        INSERT INTO restaurant_experience_media (
            post_id,
            media_type,
            media_order,
            cloudinary_public_id,
            media_url,
            thumbnail_url,
            duration_seconds,
            width,
            height,
            file_bytes,
            created_at
        )
        SELECT
            id,
            media_type,
            0,
            cloudinary_public_id,
            media_url,
            thumbnail_url,
            duration_seconds,
            width,
            height,
            file_bytes,
            CURRENT_TIMESTAMP
        FROM restaurant_experience_posts
        WHERE
            cloudinary_public_id IS NOT NULL
            AND media_url IS NOT NULL;
        """
    )


    # ========================================================
    # 4. REMOVE OLD SINGLE-MEDIA COLUMNS
    #
    # Media now belongs in restaurant_experience_media.
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_cloudinary_public_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_media_type"
            )
        )

        batch_op.drop_column(
            "cloudinary_public_id"
        )

        batch_op.drop_column(
            "height"
        )

        batch_op.drop_column(
            "thumbnail_url"
        )

        batch_op.drop_column(
            "media_url"
        )

        batch_op.drop_column(
            "duration_seconds"
        )

        batch_op.drop_column(
            "media_type"
        )

        batch_op.drop_column(
            "file_bytes"
        )

        batch_op.drop_column(
            "width"
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # 1. RESTORE OLD SINGLE-MEDIA COLUMNS
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "width",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "file_bytes",
                sa.BigInteger(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "media_type",
                sa.String(length=20),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "duration_seconds",
                sa.Float(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "media_url",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "thumbnail_url",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "height",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "cloudinary_public_id",
                sa.String(length=500),
                nullable=True,
            )
        )


    # ========================================================
    # 2. RESTORE FIRST MEDIA ITEM TO POST
    #
    # Since the old schema only supports one media item,
    # restore media_order = 0.
    # ========================================================

    op.execute(
        """
        UPDATE restaurant_experience_posts
        SET
            media_type = media.media_type,
            cloudinary_public_id = media.cloudinary_public_id,
            media_url = media.media_url,
            thumbnail_url = media.thumbnail_url,
            duration_seconds = media.duration_seconds,
            width = media.width,
            height = media.height,
            file_bytes = media.file_bytes
        FROM restaurant_experience_media AS media
        WHERE
            restaurant_experience_posts.id = media.post_id
            AND media.media_order = 0;
        """
    )


    # ========================================================
    # 3. RESTORE INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_media_type"
            ),
            ["media_type"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_cloudinary_public_id"
            ),
            ["cloudinary_public_id"],
            unique=True,
        )


    # ========================================================
    # 4. DROP MULTI-MEDIA INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_media",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_media_post_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_media_media_type"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_media_media_order"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_media_created_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_media_cloudinary_public_id"
            )
        )


    # ========================================================
    # 5. DROP MULTI-MEDIA TABLE
    # ========================================================

    op.drop_table(
        "restaurant_experience_media"
    )