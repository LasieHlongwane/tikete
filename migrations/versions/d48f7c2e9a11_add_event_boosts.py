"""add paid event boost plans and reminders

Revision ID: d48f7c2e9a11
Revises: c21e84b7d905
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "d48f7c2e9a11"
down_revision = "c21e84b7d905"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "event_boosts",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey(
                "ticket_events.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "plan_code",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "plan_name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "price",
            sa.Numeric(10, 2),
            nullable=False,
        ),

        sa.Column(
            "radius_km",
            sa.Numeric(6, 2),
            nullable=False,
            server_default="80",
        ),

        sa.Column(
            "campaign_limit",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),

        sa.Column(
            "payment_reference",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "payment_provider",
            sa.String(length=30),
            nullable=False,
            server_default="paystack",
        ),

        sa.Column(
            "paystack_access_code",
            sa.String(length=150),
            nullable=True,
        ),

        sa.Column(
            "paystack_authorization_url",
            sa.String(length=500),
            nullable=True,
        ),

        sa.Column(
            "paystack_transaction_id",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "payment_channel",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "payment_verified_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "paid_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "activated_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "audience_count_at_purchase",
            sa.Integer(),
            nullable=False,
            server_default="0",
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

        sa.UniqueConstraint(
            "event_id",
            name=
                "uq_event_boosts_event_id",
        ),

        sa.UniqueConstraint(
            "payment_reference",
            name=
                "uq_event_boosts_payment_reference",
        ),
    )

    op.create_index(
        "ix_event_boosts_event_id",
        "event_boosts",
        ["event_id"],
        unique=True,
    )

    op.create_index(
        "ix_event_boosts_plan_code",
        "event_boosts",
        ["plan_code"],
    )

    op.create_index(
        "ix_event_boosts_status",
        "event_boosts",
        ["status"],
    )

    op.create_index(
        "ix_event_boosts_payment_reference",
        "event_boosts",
        ["payment_reference"],
        unique=True,
    )

    op.create_index(
        "ix_event_boosts_paystack_transaction_id",
        "event_boosts",
        ["paystack_transaction_id"],
    )

    op.create_index(
        "ix_event_boosts_payment_verified_at",
        "event_boosts",
        ["payment_verified_at"],
    )

    op.create_index(
        "ix_event_boosts_paid_at",
        "event_boosts",
        ["paid_at"],
    )

    op.create_index(
        "ix_event_boosts_activated_at",
        "event_boosts",
        ["activated_at"],
    )

    op.create_index(
        "ix_event_boosts_created_at",
        "event_boosts",
        ["created_at"],
    )


    op.create_table(
        "event_boost_reminders",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "boost_id",
            sa.Integer(),
            sa.ForeignKey(
                "event_boosts.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "reminder_type",
            sa.String(length=30),
            nullable=False,
        ),

        sa.Column(
            "scheduled_for",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="pending",
        ),

        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey(
                "push_campaigns.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),

        sa.Column(
            "sent_at",
            sa.DateTime(),
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
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.UniqueConstraint(
            "boost_id",
            "reminder_type",
            name=
                "uq_event_boost_reminder_type",
        ),
    )

    op.create_index(
        "ix_event_boost_reminders_boost_id",
        "event_boost_reminders",
        ["boost_id"],
    )

    op.create_index(
        "ix_event_boost_reminders_reminder_type",
        "event_boost_reminders",
        ["reminder_type"],
    )

    op.create_index(
        "ix_event_boost_reminders_scheduled_for",
        "event_boost_reminders",
        ["scheduled_for"],
    )

    op.create_index(
        "ix_event_boost_reminders_status",
        "event_boost_reminders",
        ["status"],
    )

    op.create_index(
        "ix_event_boost_reminders_campaign_id",
        "event_boost_reminders",
        ["campaign_id"],
    )

    op.create_index(
        "ix_event_boost_reminders_sent_at",
        "event_boost_reminders",
        ["sent_at"],
    )


def downgrade():

    op.drop_index(
        "ix_event_boost_reminders_sent_at",
        table_name=
            "event_boost_reminders",
    )

    op.drop_index(
        "ix_event_boost_reminders_campaign_id",
        table_name=
            "event_boost_reminders",
    )

    op.drop_index(
        "ix_event_boost_reminders_status",
        table_name=
            "event_boost_reminders",
    )

    op.drop_index(
        "ix_event_boost_reminders_scheduled_for",
        table_name=
            "event_boost_reminders",
    )

    op.drop_index(
        "ix_event_boost_reminders_reminder_type",
        table_name=
            "event_boost_reminders",
    )

    op.drop_index(
        "ix_event_boost_reminders_boost_id",
        table_name=
            "event_boost_reminders",
    )

    op.drop_table(
        "event_boost_reminders"
    )


    op.drop_index(
        "ix_event_boosts_created_at",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_activated_at",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_paid_at",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_payment_verified_at",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_paystack_transaction_id",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_payment_reference",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_status",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_plan_code",
        table_name=
            "event_boosts",
    )

    op.drop_index(
        "ix_event_boosts_event_id",
        table_name=
            "event_boosts",
    )

    op.drop_table(
        "event_boosts"
    )
