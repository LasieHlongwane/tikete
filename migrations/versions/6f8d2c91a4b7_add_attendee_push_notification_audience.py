"""add attendee push notification audience

Revision ID: 6f8d2c91a4b7
Revises: 1723795ce899
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6f8d2c91a4b7"
down_revision = "1723795ce899"
branch_labels = None
depends_on = None


def upgrade():

    # ========================================================
    # ATTENDEE CONTACTS
    # ========================================================

    op.create_table(
        "attendee_contacts",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(length=150),
            nullable=True,
        ),

        sa.Column(
            "phone",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "phone_normalized",
            sa.String(length=50),
            nullable=False,
        ),

        sa.Column(
            "email",
            sa.String(length=150),
            nullable=True,
        ),

        sa.Column(
            "notification_consent",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "consented_at",
            sa.DateTime(),
            nullable=True,
        ),

        sa.Column(
            "opted_out_at",
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

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    with op.batch_alter_table(
        "attendee_contacts",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_attendee_contacts_phone_normalized"
            ),
            [
                "phone_normalized"
            ],
            unique=True,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_attendee_contacts_email"
            ),
            [
                "email"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_attendee_contacts_notification_consent"
            ),
            [
                "notification_consent"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_attendee_contacts_consented_at"
            ),
            [
                "consented_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_attendee_contacts_opted_out_at"
            ),
            [
                "opted_out_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_attendee_contacts_created_at"
            ),
            [
                "created_at"
            ],
            unique=False,
        )


    # ========================================================
    # PUSH SUBSCRIPTIONS
    # ========================================================

    op.create_table(
        "push_subscriptions",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "contact_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "firebase_installation_id",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "registered_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "last_seen_at",
            sa.DateTime(),
            nullable=False,
        ),

        sa.Column(
            "disabled_at",
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

        sa.ForeignKeyConstraint(
            [
                "contact_id"
            ],
            [
                "attendee_contacts.id"
            ],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),
    )


    with op.batch_alter_table(
        "push_subscriptions",
        schema=None,
    ) as batch_op:

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_contact_id"
            ),
            [
                "contact_id"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_firebase_installation_id"
            ),
            [
                "firebase_installation_id"
            ],
            unique=True,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_active"
            ),
            [
                "active"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_registered_at"
            ),
            [
                "registered_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_last_seen_at"
            ),
            [
                "last_seen_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_disabled_at"
            ),
            [
                "disabled_at"
            ],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_push_subscriptions_created_at"
            ),
            [
                "created_at"
            ],
            unique=False,
        )


def downgrade():

    with op.batch_alter_table(
        "push_subscriptions",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_created_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_disabled_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_last_seen_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_registered_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_active"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_firebase_installation_id"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_push_subscriptions_contact_id"
            )
        )


    op.drop_table(
        "push_subscriptions"
    )


    with op.batch_alter_table(
        "attendee_contacts",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_attendee_contacts_created_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_attendee_contacts_opted_out_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_attendee_contacts_consented_at"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_attendee_contacts_notification_consent"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_attendee_contacts_email"
            )
        )

        batch_op.drop_index(
            batch_op.f(
                "ix_attendee_contacts_phone_normalized"
            )
        )


    op.drop_table(
        "attendee_contacts"
    )