"""add restaurant push campaigns

Revision ID: a8e068dcc0d1
Revises: 052c0aca0bfd
Create Date: 2026-09-19 14:40:07.476401

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8e068dcc0d1'
down_revision = '052c0aca0bfd'
branch_labels = None
depends_on = None

def upgrade():

    with op.batch_alter_table(
        "push_campaigns",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "campaign_type",
                sa.String(length=30),
                nullable=False,
                server_default="event",
            )
        )

        batch_op.add_column(
            sa.Column(
                "restaurant_advert_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_push_campaigns_campaign_type",
            [
                "campaign_type",
            ],
            unique=False,
        )

        batch_op.create_index(
            "ix_push_campaigns_restaurant_advert_id",
            [
                "restaurant_advert_id",
            ],
            unique=False,
        )

        batch_op.create_foreign_key(
            "fk_push_campaigns_restaurant_advert_id",
            "restaurant_adverts",
            [
                "restaurant_advert_id",
            ],
            [
                "id",
            ],
            ondelete="SET NULL",
        )


    with op.batch_alter_table(
        "push_campaigns",
        schema=None,
    ) as batch_op:

        batch_op.alter_column(
            "campaign_type",
            server_default=None,
        )

def downgrade():

    with op.batch_alter_table(
        "push_campaigns",
        schema=None,
    ) as batch_op:

        batch_op.drop_constraint(
            "fk_push_campaigns_restaurant_advert_id",
            type_="foreignkey",
        )

        batch_op.drop_index(
            "ix_push_campaigns_restaurant_advert_id"
        )

        batch_op.drop_index(
            "ix_push_campaigns_campaign_type"
        )

        batch_op.drop_column(
            "restaurant_advert_id"
        )

        batch_op.drop_column(
            "campaign_type"
        )
    # ### end Alembic commands ###
