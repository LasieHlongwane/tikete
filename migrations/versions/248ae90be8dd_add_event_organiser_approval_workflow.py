"""Add event organiser approval workflow

Revision ID: 248ae90be8dd
Revises: f3a31952dbcd
Create Date: 2026-10-10 07:07:36.936557

Only adds event-organiser approval metadata. Existing event organisers
remain pending until explicitly reviewed by KALXA administration.
Restaurant accounts retain their current active/subscription state.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "248ae90be8dd"
down_revision = "f3a31952dbcd"
branch_labels = None
depends_on = None


def upgrade():
    # The server default populates existing rows with 'pending' and
    # ensures future inserts without an explicit value also start pending.
    # No existing active flags, subscription history, or payment records
    # are changed by this migration.
    with op.batch_alter_table("organizers", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "approval_status",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'pending'"),
            )
        )
        batch_op.add_column(
            sa.Column("approved_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("approved_by", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("rejected_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("rejection_reason", sa.Text(), nullable=True)
        )
        batch_op.create_index(
            "ix_organizers_approval_status",
            ["approval_status"],
            unique=False,
        )


def downgrade():
    # Reverts only the columns/index introduced above. Approval history
    # will be lost if downgraded; other account data is untouched.
    with op.batch_alter_table("organizers", schema=None) as batch_op:
        batch_op.drop_index("ix_organizers_approval_status")
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("rejected_at")
        batch_op.drop_column("approved_by")
        batch_op.drop_column("approved_at")
        batch_op.drop_column("approval_status")
