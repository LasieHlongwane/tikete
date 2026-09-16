"""add ticket sales phases

Revision ID: f72c1d4a8b90
Revises: e6a2c9f41b73
Create Date: 2026-09-16
"""
from alembic import op
import sqlalchemy as sa
revision="f72c1d4a8b90"
down_revision="e6a2c9f41b73"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("ticket_sale_phases",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("ticket_type_id",sa.Integer(),sa.ForeignKey("ticket_types.id",ondelete="CASCADE"),nullable=False),sa.Column("name",sa.String(length=100),nullable=False),sa.Column("price",sa.Numeric(10,2),nullable=False),sa.Column("start_at",sa.DateTime(),nullable=True),sa.Column("end_at",sa.DateTime(),nullable=True),sa.Column("quantity_limit",sa.Integer(),nullable=True),sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("sort_order",sa.Integer(),nullable=False,server_default="0"),sa.Column("created_at",sa.DateTime(),nullable=False),sa.Column("updated_at",sa.DateTime(),nullable=False))
    op.create_index("ix_ticket_sale_phases_ticket_type_id","ticket_sale_phases",["ticket_type_id"])
    op.create_index("ix_ticket_sale_phases_start_at","ticket_sale_phases",["start_at"])
    op.create_index("ix_ticket_sale_phases_end_at","ticket_sale_phases",["end_at"])
    op.create_index("ix_ticket_sale_phases_active","ticket_sale_phases",["active"])
    with op.batch_alter_table("ticket_order_items") as batch_op:
        batch_op.add_column(sa.Column("sale_phase_id",sa.Integer(),nullable=True))
        batch_op.add_column(sa.Column("sale_phase_name",sa.String(length=100),nullable=True))
        batch_op.create_foreign_key("fk_ticket_order_items_sale_phase_id","ticket_sale_phases",["sale_phase_id"],["id"],ondelete="SET NULL")
        batch_op.create_index("ix_ticket_order_items_sale_phase_id",["sale_phase_id"],unique=False)
def downgrade():
    with op.batch_alter_table("ticket_order_items") as batch_op:
        batch_op.drop_index("ix_ticket_order_items_sale_phase_id")
        batch_op.drop_constraint("fk_ticket_order_items_sale_phase_id",type_="foreignkey")
        batch_op.drop_column("sale_phase_name")
        batch_op.drop_column("sale_phase_id")
    op.drop_index("ix_ticket_sale_phases_active",table_name="ticket_sale_phases")
    op.drop_index("ix_ticket_sale_phases_end_at",table_name="ticket_sale_phases")
    op.drop_index("ix_ticket_sale_phases_start_at",table_name="ticket_sale_phases")
    op.drop_index("ix_ticket_sale_phases_ticket_type_id",table_name="ticket_sale_phases")
    op.drop_table("ticket_sale_phases")
