"""add event reels

Revision ID: d8785d9abe9d
Revises: b31d8f4c6a20
Create Date: 2026-09-18 21:14:05.666911

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "d8785d9abe9d"
down_revision = "b31d8f4c6a20"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # EVENT REELS
    # ========================================================
    #
    # One event can have one reel.
    #
    # The actual video is stored in Cloudinary.
    # PostgreSQL stores only the Cloudinary/public metadata.
    # ========================================================

    op.create_table(
        "event_reels",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "event_id",
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
            sa.String(length=500),
            nullable=False,
        ),

        sa.Column(
            "video_url",
            sa.String(length=1200),
            nullable=False,
        ),

        sa.Column(
            "thumbnail_url",
            sa.String(length=1200),
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
            sa.BigInteger(),
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
            ["event_id"],
            ["ticket_events.id"],
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

        sa.UniqueConstraint(
            "cloudinary_public_id",
            name="uq_event_reels_cloudinary_public_id",
        ),
    )


    # ========================================================
    # INDEXES
    # ========================================================

    op.create_index(
        "ix_event_reels_active",
        "event_reels",
        ["active"],
        unique=False,
    )

    op.create_index(
        "ix_event_reels_created_at",
        "event_reels",
        ["created_at"],
        unique=False,
    )

    # Unique=True because each event has only one Event Reel.
    op.create_index(
        "ix_event_reels_event_id",
        "event_reels",
        ["event_id"],
        unique=True,
    )

    op.create_index(
        "ix_event_reels_organizer_id",
        "event_reels",
        ["organizer_id"],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # REMOVE EVENT REELS
    # ========================================================

    op.drop_index(
        "ix_event_reels_organizer_id",
        table_name="event_reels",
    )

    op.drop_index(
        "ix_event_reels_event_id",
        table_name="event_reels",
    )

    op.drop_index(
        "ix_event_reels_created_at",
        table_name="event_reels",
    )

    op.drop_index(
        "ix_event_reels_active",
        table_name="event_reels",
    )

    op.drop_table(
        "event_reels"
    )