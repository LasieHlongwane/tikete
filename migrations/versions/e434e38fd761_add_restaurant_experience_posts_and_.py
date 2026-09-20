"""add restaurant experience posts and loves

Revision ID: e434e38fd761
Revises: a8e068dcc0d1
Create Date: 2026-09-20 17:31:39.566715

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "e434e38fd761"
down_revision = "a8e068dcc0d1"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # RESTAURANT EXPERIENCE POSTS
    # ========================================================

    op.create_table(
        "restaurant_experience_posts",

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
            "poster_name",
            sa.String(length=120),
            nullable=False,
        ),

        sa.Column(
            "experience_text",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "media_type",
            sa.String(length=20),
            nullable=False,
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
            "moderation_status",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "moderated_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "moderated_by",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "rejection_reason",
            sa.Text(),
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

        sa.ForeignKeyConstraint(
            ["restaurant_advert_id"],
            ["restaurant_adverts.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    # ========================================================
    # RESTAURANT EXPERIENCE POST INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_active"
            ),
            ["active"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_cloudinary_public_id"
            ),
            ["cloudinary_public_id"],
            unique=True,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_created_at"
            ),
            ["created_at"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_media_type"
            ),
            ["media_type"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_moderated_at"
            ),
            ["moderated_at"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_moderation_status"
            ),
            ["moderation_status"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_restaurant_advert_id"
            ),
            ["restaurant_advert_id"],
            unique=False,
        )


    # ========================================================
    # RESTAURANT EXPERIENCE LOVES
    # ========================================================

    op.create_table(
        "restaurant_experience_loves",

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
            "anonymous_session_id",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ["post_id"],
            ["restaurant_experience_posts.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),

        sa.UniqueConstraint(
            "post_id",
            "anonymous_session_id",
            name=(
                "uq_restaurant_experience_love_session"
            ),
        ),
    )


    # ========================================================
    # RESTAURANT EXPERIENCE LOVE INDEXES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_loves",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_loves_anonymous_session_id"
            ),
            ["anonymous_session_id"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_loves_created_at"
            ),
            ["created_at"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_loves_post_id"
            ),
            ["post_id"],
            unique=False,
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # REMOVE RESTAURANT EXPERIENCE LOVES
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_loves",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_loves_post_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_loves_created_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_loves_anonymous_session_id"
            )
        )


    op.drop_table(
        "restaurant_experience_loves"
    )


    # ========================================================
    # REMOVE RESTAURANT EXPERIENCE POSTS
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_restaurant_advert_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_moderation_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_moderated_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_media_type"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_created_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_cloudinary_public_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_active"
            )
        )


    op.drop_table(
        "restaurant_experience_posts"
    )