"""add push notification campaigns

Revision ID: 1b7c9e4f2a61
Revises: 6f8d2c91a4b7
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1b7c9e4f2a61"
down_revision = "6f8d2c91a4b7"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "push_campaigns",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "event_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "title",
            sa.String(length=120),
            nullable=False,
        ),

        sa.Column(
            "body",
            sa.String(length=500),
            nullable=False,
        ),

        sa.Column(
            "target_url",
            sa.String(length=1000),
            nullable=True,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "recipient_count",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "success_count",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "failure_count",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "created_by",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "sent_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.ForeignKeyConstraint(
            ["event_id"],
            ["ticket_events.id"],
            ondelete="SET NULL",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    op.create_index(
        "ix_push_campaigns_event_id",
        "push_campaigns",
        ["event_id"],
        unique=False,
    )

    op.create_index(
        "ix_push_campaigns_status",
        "push_campaigns",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_push_campaigns_created_at",
        "push_campaigns",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_push_campaigns_sent_at",
        "push_campaigns",
        ["sent_at"],
        unique=False,
    )


    op.create_table(
        "push_deliveries",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "campaign_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "push_subscription_id",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "firebase_installation_id",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "firebase_message_id",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "sent_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["push_campaigns.id"],
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["push_subscription_id"],
            ["push_subscriptions.id"],
            ondelete="SET NULL",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    op.create_index(
        "ix_push_deliveries_campaign_id",
        "push_deliveries",
        ["campaign_id"],
        unique=False,
    )

    op.create_index(
        "ix_push_deliveries_push_subscription_id",
        "push_deliveries",
        ["push_subscription_id"],
        unique=False,
    )

    op.create_index(
        "ix_push_deliveries_firebase_installation_id",
        "push_deliveries",
        ["firebase_installation_id"],
        unique=False,
    )

    op.create_index(
        "ix_push_deliveries_status",
        "push_deliveries",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_push_deliveries_created_at",
        "push_deliveries",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_push_deliveries_sent_at",
        "push_deliveries",
        ["sent_at"],
        unique=False,
    )


def downgrade():

    op.drop_index(
        "ix_push_deliveries_sent_at",
        table_name="push_deliveries",
    )

    op.drop_index(
        "ix_push_deliveries_created_at",
        table_name="push_deliveries",
    )

    op.drop_index(
        "ix_push_deliveries_status",
        table_name="push_deliveries",
    )

    op.drop_index(
        "ix_push_deliveries_firebase_installation_id",
        table_name="push_deliveries",
    )

    op.drop_index(
        "ix_push_deliveries_push_subscription_id",
        table_name="push_deliveries",
    )

    op.drop_index(
        "ix_push_deliveries_campaign_id",
        table_name="push_deliveries",
    )

    op.drop_table(
        "push_deliveries"
    )


    op.drop_index(
        "ix_push_campaigns_sent_at",
        table_name="push_campaigns",
    )

    op.drop_index(
        "ix_push_campaigns_created_at",
        table_name="push_campaigns",
    )

    op.drop_index(
        "ix_push_campaigns_status",
        table_name="push_campaigns",
    )

    op.drop_index(
        "ix_push_campaigns_event_id",
        table_name="push_campaigns",
    )

    op.drop_table(
        "push_campaigns"
    )
