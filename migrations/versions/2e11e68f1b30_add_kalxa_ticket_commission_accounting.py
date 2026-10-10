"""Add Kalxa ticket commission accounting

Revision ID: 2e11e68f1b30
Revises: 248ae90be8dd
Create Date: 2026-10-10 08:50:58.719549

Only ticket_orders is modified. Existing orders are not backfilled
with the new 4% commission rate.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e11e68f1b30'
down_revision = '248ae90be8dd'
branch_labels = None
depends_on = None


def upgrade():
    # Financial snapshots are nullable so historical orders remain intact.
    with op.batch_alter_table('ticket_orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('commission_rate', sa.Numeric(precision=6, scale=4), nullable=True))
        batch_op.add_column(sa.Column('commission_amount', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('organizer_gross_share', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('commission_recorded_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('refunded_face_value', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('commission_reversed_amount', sa.Numeric(precision=10, scale=2), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('refunded_at', sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_ticket_orders_commission_recorded_at'),
            ['commission_recorded_at'],
            unique=False,
        )


def downgrade():
    # Downgrading discards stored commission and refund accounting data.
    with op.batch_alter_table('ticket_orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ticket_orders_commission_recorded_at'))
        batch_op.drop_column('refunded_at')
        batch_op.drop_column('commission_reversed_amount')
        batch_op.drop_column('refunded_face_value')
        batch_op.drop_column('commission_recorded_at')
        batch_op.drop_column('organizer_gross_share')
        batch_op.drop_column('commission_amount')
        batch_op.drop_column('commission_rate')
