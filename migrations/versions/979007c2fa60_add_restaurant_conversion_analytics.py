"""add restaurant conversion analytics

Revision ID: 979007c2fa60
Revises: 9569366337f5
Create Date: 2026-09-29 02:02:59.290078

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "979007c2fa60"
down_revision = "9569366337f5"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # ========================================================
    # RESTAURANT ANALYTICS EVENTS
    #
    # Stores anonymous restaurant conversion events generated
    # inside Kalxa Ticketing.
    #
    # Examples:
    #
    # restaurant_view
    # experience_view
    # whatsapp_click
    # phone_click
    # directions_click
    #
    # The source_* fields allow Kalxa Ticketing to preserve
    # attribution from external Kalxa services such as
    # Kalxa Stories without creating cross-database foreign
    # keys.
    # ========================================================

    op.create_table(
        "restaurant_analytics_events",

        # ----------------------------------------------------
        # PRIMARY KEY
        # ----------------------------------------------------

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        # ----------------------------------------------------
        # RESTAURANT
        # ----------------------------------------------------

        sa.Column(
            "restaurant_id",
            sa.Integer(),
            nullable=False,
        ),

        # ----------------------------------------------------
        # EVENT
        # ----------------------------------------------------

        sa.Column(
            "event_type",
            sa.String(
                length=50
            ),
            nullable=False,
        ),

        # ----------------------------------------------------
        # ANONYMOUS TICKETING SESSION
        # ----------------------------------------------------

        sa.Column(
            "session_id",
            sa.String(
                length=100
            ),
            nullable=True,
        ),

        # ----------------------------------------------------
        # ATTRIBUTION SOURCE
        #
        # Example:
        #
        # source = "stories"
        # ----------------------------------------------------

        sa.Column(
            "source",
            sa.String(
                length=50
            ),
            nullable=True,
        ),

        # ----------------------------------------------------
        # EXTERNAL KALXA STORIES ARTICLE ID
        #
        # NOT a foreign key because Kalxa Stories has its
        # own database.
        # ----------------------------------------------------

        sa.Column(
            "source_article_id",
            sa.Integer(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # RESTAURANT ID RECEIVED FROM THE SOURCE
        #
        # Stored for attribution/debugging.
        # ----------------------------------------------------

        sa.Column(
            "source_restaurant_id",
            sa.Integer(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # ANONYMOUS SOURCE SESSION
        #
        # Example:
        #
        # anonymous Kalxa Stories session ID
        # ----------------------------------------------------

        sa.Column(
            "source_session_id",
            sa.String(
                length=100
            ),
            nullable=True,
        ),

        # ----------------------------------------------------
        # OPTIONAL EVENT METADATA
        #
        # Examples:
        #
        # {
        #     "action": "whatsapp"
        # }
        #
        # {
        #     "experience_post_id": 24
        # }
        # ----------------------------------------------------

        sa.Column(
            "event_metadata",
            sa.JSON(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # HTTP REFERRER
        # ----------------------------------------------------

        sa.Column(
            "referrer",
            sa.Text(),
            nullable=True,
        ),

        # ----------------------------------------------------
        # TIMESTAMP
        # ----------------------------------------------------

        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
        ),

        # ----------------------------------------------------
        # FOREIGN KEY
        # ----------------------------------------------------

        sa.ForeignKeyConstraint(
            [
                "restaurant_id"
            ],
            [
                "restaurant_adverts.id"
            ],
            ondelete="CASCADE",
        ),

        # ----------------------------------------------------
        # PRIMARY KEY
        # ----------------------------------------------------

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    # ========================================================
    # INDEXES
    # ========================================================

    op.create_index(
        "ix_restaurant_analytics_events_created_at",
        "restaurant_analytics_events",
        [
            "created_at"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_event_type",
        "restaurant_analytics_events",
        [
            "event_type"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_restaurant_id",
        "restaurant_analytics_events",
        [
            "restaurant_id"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_session_id",
        "restaurant_analytics_events",
        [
            "session_id"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_source",
        "restaurant_analytics_events",
        [
            "source"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_source_article_id",
        "restaurant_analytics_events",
        [
            "source_article_id"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_source_restaurant_id",
        "restaurant_analytics_events",
        [
            "source_restaurant_id"
        ],
        unique=False,
    )


    op.create_index(
        "ix_restaurant_analytics_events_source_session_id",
        "restaurant_analytics_events",
        [
            "source_session_id"
        ],
        unique=False,
    )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    # ========================================================
    # DROP INDEXES
    # ========================================================

    op.drop_index(
        "ix_restaurant_analytics_events_source_session_id",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_source_restaurant_id",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_source_article_id",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_source",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_session_id",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_restaurant_id",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_event_type",
        table_name="restaurant_analytics_events",
    )


    op.drop_index(
        "ix_restaurant_analytics_events_created_at",
        table_name="restaurant_analytics_events",
    )


    # ========================================================
    # DROP TABLE
    # ========================================================

    op.drop_table(
        "restaurant_analytics_events"
    )