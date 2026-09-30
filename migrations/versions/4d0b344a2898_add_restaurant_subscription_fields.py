"""add restaurant subscription fields

Revision ID: 4d0b344a2898
Revises: 979007c2fa60
Create Date: 2026-10-01 01:18:15.252608

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# REVISION IDENTIFIERS
# ============================================================

revision = "4d0b344a2898"
down_revision = "979007c2fa60"
branch_labels = None
depends_on = None


# ============================================================
# UPGRADE
# ============================================================

def upgrade():

    # --------------------------------------------------------
    # RESTAURANT SUBSCRIPTION
    #
    # Existing restaurants automatically become:
    #
    # subscription_tier   = "free"
    # subscription_status = "active"
    #
    # This allows existing restaurant profiles to continue
    # working while restricting premium features later.
    # --------------------------------------------------------

    with op.batch_alter_table(
        "restaurant_adverts",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "subscription_tier",
                sa.String(length=30),
                server_default="free",
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "subscription_status",
                sa.String(length=30),
                server_default="active",
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "subscription_started_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "subscription_expires_at",
                sa.DateTime(),
                nullable=True,
            )
        )

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_adverts_subscription_tier"
            ),
            ["subscription_tier"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_adverts_subscription_status"
            ),
            ["subscription_status"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_adverts_subscription_expires_at"
            ),
            ["subscription_expires_at"],
            unique=False,
        )


# ============================================================
# DOWNGRADE
# ============================================================

def downgrade():

    with op.batch_alter_table(
        "restaurant_adverts",
        schema=None,
    ) as batch_op:

        # ----------------------------------------------------
        # REMOVE INDEXES FIRST
        # ----------------------------------------------------

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_adverts_subscription_expires_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_adverts_subscription_status"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_adverts_subscription_tier"
            )
        )

        # ----------------------------------------------------
        # REMOVE SUBSCRIPTION COLUMNS
        # ----------------------------------------------------

        batch_op.drop_column(
            "subscription_expires_at"
        )

        batch_op.drop_column(
            "subscription_started_at"
        )

        batch_op.drop_column(
            "subscription_status"
        )

        batch_op.drop_column(
            "subscription_tier"
        )