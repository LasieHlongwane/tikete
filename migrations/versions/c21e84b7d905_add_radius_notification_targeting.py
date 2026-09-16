"""add radius based notification targeting

Revision ID: c21e84b7d905
Revises: 7bd3f1a9c640
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "c21e84b7d905"
down_revision = "7bd3f1a9c640"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "geocoded_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("query_key", sa.String(length=255), nullable=False),
        sa.Column("query_text", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=500), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
            server_default="nominatim",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_geocoded_areas_query_key",
        "geocoded_areas",
        ["query_key"],
        unique=True,
    )


    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "notification_area",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "notification_location_display",
                sa.String(length=500),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "notification_latitude",
                sa.Float(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "notification_longitude",
                sa.Float(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_ticket_events_notification_area",
            ["notification_area"],
            unique=False,
        )
        batch_op.create_index(
            "ix_ticket_events_notification_latitude",
            ["notification_latitude"],
            unique=False,
        )
        batch_op.create_index(
            "ix_ticket_events_notification_longitude",
            ["notification_longitude"],
            unique=False,
        )


    with op.batch_alter_table(
        "push_subscriptions",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "home_area",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "home_location_display",
                sa.String(length=500),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "home_latitude",
                sa.Float(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "home_longitude",
                sa.Float(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_push_subscriptions_home_area",
            ["home_area"],
            unique=False,
        )
        batch_op.create_index(
            "ix_push_subscriptions_home_latitude",
            ["home_latitude"],
            unique=False,
        )
        batch_op.create_index(
            "ix_push_subscriptions_home_longitude",
            ["home_longitude"],
            unique=False,
        )


    with op.batch_alter_table(
        "push_campaigns",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "target_mode",
                sa.String(length=30),
                nullable=False,
                server_default="radius",
            )
        )
        batch_op.add_column(
            sa.Column(
                "target_area",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "target_latitude",
                sa.Float(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "target_longitude",
                sa.Float(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "radius_km",
                sa.Numeric(6, 2),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_push_campaigns_target_mode",
            ["target_mode"],
            unique=False,
        )


def downgrade():

    with op.batch_alter_table(
        "push_campaigns",
        schema=None,
    ) as batch_op:
        batch_op.drop_index("ix_push_campaigns_target_mode")
        batch_op.drop_column("radius_km")
        batch_op.drop_column("target_longitude")
        batch_op.drop_column("target_latitude")
        batch_op.drop_column("target_area")
        batch_op.drop_column("target_mode")

    with op.batch_alter_table(
        "push_subscriptions",
        schema=None,
    ) as batch_op:
        batch_op.drop_index("ix_push_subscriptions_home_longitude")
        batch_op.drop_index("ix_push_subscriptions_home_latitude")
        batch_op.drop_index("ix_push_subscriptions_home_area")
        batch_op.drop_column("home_longitude")
        batch_op.drop_column("home_latitude")
        batch_op.drop_column("home_location_display")
        batch_op.drop_column("home_area")

    with op.batch_alter_table(
        "ticket_events",
        schema=None,
    ) as batch_op:
        batch_op.drop_index("ix_ticket_events_notification_longitude")
        batch_op.drop_index("ix_ticket_events_notification_latitude")
        batch_op.drop_index("ix_ticket_events_notification_area")
        batch_op.drop_column("notification_longitude")
        batch_op.drop_column("notification_latitude")
        batch_op.drop_column("notification_location_display")
        batch_op.drop_column("notification_area")

    op.drop_index(
        "ix_geocoded_areas_query_key",
        table_name="geocoded_areas",
    )
    op.drop_table("geocoded_areas")
