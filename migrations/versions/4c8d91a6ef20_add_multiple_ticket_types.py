"""add multiple ticket types and order items

Revision ID: 4c8d91a6ef20
Revises: f84b6d21c7aa
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "4c8d91a6ef20"
down_revision = "f84b6d21c7aa"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "ticket_types",

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
            "name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "price",
            sa.Numeric(10, 2),
            nullable=False,
        ),

        sa.Column(
            "capacity",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "sort_order",
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
    )

    op.create_index(
        "ix_ticket_types_event_id",
        "ticket_types",
        ["event_id"],
    )

    op.create_index(
        "ix_ticket_types_active",
        "ticket_types",
        ["active"],
    )


    op.create_table(
        "ticket_order_items",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),

        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey(
                "ticket_orders.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "ticket_type_id",
            sa.Integer(),
            sa.ForeignKey(
                "ticket_types.id",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),

        sa.Column(
            "ticket_name",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "unit_price",
            sa.Numeric(10, 2),
            nullable=False,
        ),

        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "line_total",
            sa.Numeric(10, 2),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_ticket_order_items_order_id",
        "ticket_order_items",
        ["order_id"],
    )

    op.create_index(
        "ix_ticket_order_items_ticket_type_id",
        "ticket_order_items",
        ["ticket_type_id"],
    )


    with op.batch_alter_table(
        "entry_passes",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "order_item_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_foreign_key(
            "fk_entry_passes_order_item_id",
            "ticket_order_items",
            ["order_item_id"],
            ["id"],
            ondelete="CASCADE",
        )

        batch_op.create_index(
            "ix_entry_passes_order_item_id",
            ["order_item_id"],
            unique=False,
        )


def downgrade():

    with op.batch_alter_table(
        "entry_passes",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            "ix_entry_passes_order_item_id"
        )

        batch_op.drop_constraint(
            "fk_entry_passes_order_item_id",
            type_="foreignkey",
        )

        batch_op.drop_column(
            "order_item_id"
        )


    op.drop_index(
        "ix_ticket_order_items_ticket_type_id",
        table_name="ticket_order_items",
    )

    op.drop_index(
        "ix_ticket_order_items_order_id",
        table_name="ticket_order_items",
    )

    op.drop_table(
        "ticket_order_items"
    )


    op.drop_index(
        "ix_ticket_types_active",
        table_name="ticket_types",
    )

    op.drop_index(
        "ix_ticket_types_event_id",
        table_name="ticket_types",
    )

    op.drop_table(
        "ticket_types"
    )
