"""add staff check-in accounts and audit

Revision ID: e6a2c9f41b73
Revises: d48f7c2e9a11
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "e6a2c9f41b73"
down_revision = "d48f7c2e9a11"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "staff_accounts",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
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

        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),

        sa.Column(
            "username",
            sa.String(length=120),
            nullable=False,
        ),

        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "last_login_at",
            sa.DateTime(),
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
            "username",
            name="uq_staff_accounts_username",
        ),
    )

    op.create_index(
        "ix_staff_accounts_organizer_id",
        "staff_accounts",
        ["organizer_id"],
    )

    op.create_index(
        "ix_staff_accounts_username",
        "staff_accounts",
        ["username"],
        unique=True,
    )

    op.create_index(
        "ix_staff_accounts_active",
        "staff_accounts",
        ["active"],
    )

    op.create_index(
        "ix_staff_accounts_last_login_at",
        "staff_accounts",
        ["last_login_at"],
    )

    op.create_index(
        "ix_staff_accounts_created_at",
        "staff_accounts",
        ["created_at"],
    )


    op.create_table(
        "staff_event_access",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "staff_id",
            sa.Integer(),
            sa.ForeignKey(
                "staff_accounts.id",
                ondelete="CASCADE",
            ),
            nullable=False,
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
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.UniqueConstraint(
            "staff_id",
            "event_id",
            name="uq_staff_event_access",
        ),
    )

    op.create_index(
        "ix_staff_event_access_staff_id",
        "staff_event_access",
        ["staff_id"],
    )

    op.create_index(
        "ix_staff_event_access_event_id",
        "staff_event_access",
        ["event_id"],
    )


    with op.batch_alter_table(
        "checkins",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "staff_account_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_foreign_key(
            "fk_checkins_staff_account_id",
            "staff_accounts",
            ["staff_account_id"],
            ["id"],
            ondelete="SET NULL",
        )

        batch_op.create_index(
            "ix_checkins_staff_account_id",
            ["staff_account_id"],
            unique=False,
        )


def downgrade():

    with op.batch_alter_table(
        "checkins",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_checkins_staff_account_id"
        )

        batch_op.drop_constraint(
            "fk_checkins_staff_account_id",
            type_="foreignkey",
        )

        batch_op.drop_column(
            "staff_account_id"
        )


    op.drop_index(
        "ix_staff_event_access_event_id",
        table_name="staff_event_access",
    )

    op.drop_index(
        "ix_staff_event_access_staff_id",
        table_name="staff_event_access",
    )

    op.drop_table(
        "staff_event_access"
    )


    op.drop_index(
        "ix_staff_accounts_created_at",
        table_name="staff_accounts",
    )

    op.drop_index(
        "ix_staff_accounts_last_login_at",
        table_name="staff_accounts",
    )

    op.drop_index(
        "ix_staff_accounts_active",
        table_name="staff_accounts",
    )

    op.drop_index(
        "ix_staff_accounts_username",
        table_name="staff_accounts",
    )

    op.drop_index(
        "ix_staff_accounts_organizer_id",
        table_name="staff_accounts",
    )

    op.drop_table(
        "staff_accounts"
    )
