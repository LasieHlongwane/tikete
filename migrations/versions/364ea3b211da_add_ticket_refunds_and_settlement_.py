"""Add ticket refunds and settlement reconciliation.

Revision ID: 364ea3b211da
Revises: 929ae19f5e51
Create Date: 2026-10-10 15:57:07.318990

Only ticket refund and settlement accounting objects are changed.
No existing financial history is rewritten.
"""

from alembic import op
import sqlalchemy as sa


revision = "364ea3b211da"
down_revision = "929ae19f5e51"
branch_labels = None
depends_on = None


def upgrade():
    # Order-level refund and settlement summaries.
    op.add_column(
        "ticket_orders",
        sa.Column("refund_status", sa.String(length=30), server_default="none", nullable=False),
    )
    op.add_column(
        "ticket_orders",
        sa.Column("settlement_status", sa.String(length=30), server_default="unreconciled", nullable=False),
    )
    op.add_column(
        "ticket_orders",
        sa.Column("settlement_reconciled_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ticket_orders_refund_status", "ticket_orders", ["refund_status"])
    op.create_index("ix_ticket_orders_settlement_status", "ticket_orders", ["settlement_status"])
    op.create_index(
        "ix_ticket_orders_settlement_reconciled_at",
        "ticket_orders",
        ["settlement_reconciled_at"],
    )

    # Cumulative *completed* refunds per order item.
    op.add_column(
        "ticket_order_items",
        sa.Column("refunded_quantity", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ticket_order_items",
        sa.Column("refunded_face_value", sa.Numeric(10, 2), server_default="0", nullable=False),
    )

    # Provider settlement records; these are not organiser payout receipts.
    op.create_table(
        "paystack_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paystack_settlement_id", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("processing_fees", sa.Numeric(12, 2), nullable=True),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(30), server_default="discovered", nullable=False),
        sa.Column("destination_type", sa.String(30), nullable=True),
        sa.Column("destination_reference", sa.String(150), nullable=True),
        sa.Column("settlement_date", sa.DateTime(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_paystack_settlements_paystack_settlement_id",
        "paystack_settlements", ["paystack_settlement_id"], unique=True,
    )
    op.create_index("ix_paystack_settlements_status", "paystack_settlements", ["status"])

    # Refund requests are distinct from confirmed refunds.
    op.create_table(
        "ticket_refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("ticket_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("refund_reference", sa.String(100), nullable=False),
        sa.Column("paystack_refund_id", sa.String(100), nullable=True, unique=True),
        sa.Column("paystack_transaction_id", sa.String(100), nullable=True),
        sa.Column("face_value_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("provider_refund_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("commission_reversal_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="requested", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(100), nullable=True),
        sa.Column("accounting_applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ticket_refunds_order_id", "ticket_refunds", ["order_id"])
    op.create_index("ix_ticket_refunds_refund_reference", "ticket_refunds", ["refund_reference"], unique=True)
    op.create_index("ix_ticket_refunds_status", "ticket_refunds", ["status"])

    # Allocation of settlement transaction amounts to ticket orders.
    op.create_table(
        "ticket_settlement_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_id", sa.Integer(), sa.ForeignKey("paystack_settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("ticket_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("transaction_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("processing_fee", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("net_settlement_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("settlement_id", "order_id", name="uq_ticket_settlement_order"),
    )
    op.create_index("ix_ticket_settlement_allocations_order_id", "ticket_settlement_allocations", ["order_id"])
    op.create_index("ix_ticket_settlement_allocations_settlement_id", "ticket_settlement_allocations", ["settlement_id"])

    # Individual tickets selected for each refund request.
    op.create_table(
        "ticket_refund_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refund_id", sa.Integer(), sa.ForeignKey("ticket_refunds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("ticket_order_items.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("entry_pass_id", sa.Integer(), sa.ForeignKey("entry_passes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("face_value_amount", sa.Numeric(10, 2), nullable=False),
    )
    op.create_index("ix_ticket_refund_items_refund_id", "ticket_refund_items", ["refund_id"])
    op.create_index("ix_ticket_refund_items_order_item_id", "ticket_refund_items", ["order_item_id"])
    op.create_index("ix_ticket_refund_items_entry_pass_id", "ticket_refund_items", ["entry_pass_id"])


def downgrade():
    # WARNING: downgrade deletes refund and settlement history.
    # Back up financial records and confirm no production data depends
    # on these tables before downgrading.
    op.drop_index("ix_ticket_refund_items_entry_pass_id", table_name="ticket_refund_items")
    op.drop_index("ix_ticket_refund_items_order_item_id", table_name="ticket_refund_items")
    op.drop_index("ix_ticket_refund_items_refund_id", table_name="ticket_refund_items")
    op.drop_table("ticket_refund_items")

    op.drop_index("ix_ticket_settlement_allocations_settlement_id", table_name="ticket_settlement_allocations")
    op.drop_index("ix_ticket_settlement_allocations_order_id", table_name="ticket_settlement_allocations")
    op.drop_table("ticket_settlement_allocations")

    op.drop_index("ix_ticket_refunds_status", table_name="ticket_refunds")
    op.drop_index("ix_ticket_refunds_refund_reference", table_name="ticket_refunds")
    op.drop_index("ix_ticket_refunds_order_id", table_name="ticket_refunds")
    op.drop_table("ticket_refunds")

    op.drop_index("ix_paystack_settlements_status", table_name="paystack_settlements")
    op.drop_index("ix_paystack_settlements_paystack_settlement_id", table_name="paystack_settlements")
    op.drop_table("paystack_settlements")

    op.drop_column("ticket_order_items", "refunded_face_value")
    op.drop_column("ticket_order_items", "refunded_quantity")

    op.drop_index("ix_ticket_orders_settlement_reconciled_at", table_name="ticket_orders")
    op.drop_index("ix_ticket_orders_settlement_status", table_name="ticket_orders")
    op.drop_index("ix_ticket_orders_refund_status", table_name="ticket_orders")
    op.drop_column("ticket_orders", "settlement_reconciled_at")
    op.drop_column("ticket_orders", "settlement_status")
    op.drop_column("ticket_orders", "refund_status")
