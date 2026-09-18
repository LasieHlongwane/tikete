"""add event reel analytics

Revision ID: e71ac408740d
Revises: d8785d9abe9d
Create Date: 2026-09-18 22:32:18.072352

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "e71ac408740d"
down_revision = "d8785d9abe9d"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # EVENT REEL ANALYTICS
    # ========================================================
    #
    # Anonymous engagement events for public Event Reels.
    #
    # Supported event types:
    #
    # impression
    # play
    # open
    # half_watched
    # completed
    # view_event
    #
    # One browser session can record each event type once
    # per reel because of the unique constraint below.
    # ========================================================

    op.create_table(
        "event_reel_analytics",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "reel_id",
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
            "event_type",
            sa.String(length=40),
            nullable=False,
        ),

        sa.Column(
            "anonymous_session_id",
            sa.String(length=80),
            nullable=False,
        ),

        sa.Column(
            "created_at",
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

        sa.ForeignKeyConstraint(
            ["reel_id"],
            ["event_reels.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),

        sa.UniqueConstraint(
            "reel_id",
            "anonymous_session_id",
            "event_type",
            name=(
                "uq_reel_analytics_"
                "session_event"
            ),
        ),
    )


    # ========================================================
    # INDEXES
    # ========================================================

    op.create_index(
        "ix_event_reel_analytics_anonymous_session_id",
        "event_reel_analytics",
        ["anonymous_session_id"],
        unique=False,
    )

    op.create_index(
        "ix_event_reel_analytics_created_at",
        "event_reel_analytics",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_event_reel_analytics_event_id",
        "event_reel_analytics",
        ["event_id"],
        unique=False,
    )

    op.create_index(
        "ix_event_reel_analytics_event_type",
        "event_reel_analytics",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_event_reel_analytics_organizer_id",
        "event_reel_analytics",
        ["organizer_id"],
        unique=False,
    )

    op.create_index(
        "ix_event_reel_analytics_reel_id",
        "event_reel_analytics",
        ["reel_id"],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    op.drop_index(
        "ix_event_reel_analytics_reel_id",
        table_name="event_reel_analytics",
    )

    op.drop_index(
        "ix_event_reel_analytics_organizer_id",
        table_name="event_reel_analytics",
    )

    op.drop_index(
        "ix_event_reel_analytics_event_type",
        table_name="event_reel_analytics",
    )

    op.drop_index(
        "ix_event_reel_analytics_event_id",
        table_name="event_reel_analytics",
    )

    op.drop_index(
        "ix_event_reel_analytics_created_at",
        table_name="event_reel_analytics",
    )

    op.drop_index(
        "ix_event_reel_analytics_anonymous_session_id",
        table_name="event_reel_analytics",
    )

    op.drop_table(
        "event_reel_analytics"
    )