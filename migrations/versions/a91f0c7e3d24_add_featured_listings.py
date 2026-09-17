"""add featured listings and featured poster images

Revision ID: a91f0c7e3d24
Revises: f72c1d4a8b90
Create Date: 2026-09-17
"""

from alembic import op
import sqlalchemy as sa


revision = "a91f0c7e3d24"
down_revision = "f72c1d4a8b90"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "featured_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
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
            "organizer_id",
            sa.Integer(),
            sa.ForeignKey(
                "organizers.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("plan_code", sa.String(length=30), nullable=False),
        sa.Column("plan_name", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("payment_reference", sa.String(length=100), nullable=False),
        sa.Column("payment_provider", sa.String(length=30), nullable=False, server_default="paystack"),
        sa.Column("paystack_access_code", sa.String(length=150), nullable=True),
        sa.Column("paystack_authorization_url", sa.String(length=500), nullable=True),
        sa.Column("paystack_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("payment_channel", sa.String(length=50), nullable=True),
        sa.Column("payment_verified_at", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "payment_reference",
            name="uq_featured_listings_payment_reference",
        ),
    )

    for name, columns, unique in [
        ("ix_featured_listings_event_id", ["event_id"], False),
        ("ix_featured_listings_organizer_id", ["organizer_id"], False),
        ("ix_featured_listings_plan_code", ["plan_code"], False),
        ("ix_featured_listings_status", ["status"], False),
        ("ix_featured_listings_payment_reference", ["payment_reference"], True),
        ("ix_featured_listings_paystack_transaction_id", ["paystack_transaction_id"], False),
        ("ix_featured_listings_payment_verified_at", ["payment_verified_at"], False),
        ("ix_featured_listings_paid_at", ["paid_at"], False),
        ("ix_featured_listings_starts_at", ["starts_at"], False),
        ("ix_featured_listings_ends_at", ["ends_at"], False),
        ("ix_featured_listings_created_at", ["created_at"], False),
    ]:
        op.create_index(
            name,
            "featured_listings",
            columns,
            unique=unique,
        )

    op.create_table(
        "featured_listing_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Integer(),
            sa.ForeignKey(
                "ticket_events.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column("image_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("image_mimetype", sa.String(length=100), nullable=False),
        sa.Column("image_filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "event_id",
            "image_order",
            name="uq_featured_listing_image_order",
        ),
    )

    op.create_index(
        "ix_featured_listing_images_event_id",
        "featured_listing_images",
        ["event_id"],
        unique=False,
    )


def downgrade():

    op.drop_index(
        "ix_featured_listing_images_event_id",
        table_name="featured_listing_images",
    )

    op.drop_table(
        "featured_listing_images"
    )

    for name in [
        "ix_featured_listings_created_at",
        "ix_featured_listings_ends_at",
        "ix_featured_listings_starts_at",
        "ix_featured_listings_paid_at",
        "ix_featured_listings_payment_verified_at",
        "ix_featured_listings_paystack_transaction_id",
        "ix_featured_listings_payment_reference",
        "ix_featured_listings_status",
        "ix_featured_listings_plan_code",
        "ix_featured_listings_organizer_id",
        "ix_featured_listings_event_id",
    ]:
        op.drop_index(
            name,
            table_name="featured_listings",
        )

    op.drop_table(
        "featured_listings"
    )