"""Prevent duplicate ticket checkins

Revision ID: 929ae19f5e51
Revises: 2e11e68f1b30
Create Date: 2026-10-10 15:27:49.249442

Only changes the index on checkins.entry_pass_id.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '929ae19f5e51'
down_revision = '2e11e68f1b30'
branch_labels = None
depends_on = None


def upgrade():
    # Refuse to change the index if historical duplicate admissions exist.
    # Never silently delete or merge check-in records.
    connection = op.get_bind()
    duplicate = connection.execute(
        sa.text(
            """
            SELECT entry_pass_id, COUNT(*) AS checkin_count
            FROM checkins
            GROUP BY entry_pass_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()

    if duplicate is not None:
        raise RuntimeError(
            "Cannot enforce unique checkins.entry_pass_id: "
            f"entry_pass_id={duplicate[0]} has {duplicate[1]} check-in records. "
            "Review and resolve duplicates before upgrading."
        )

    with op.batch_alter_table('checkins', schema=None) as batch_op:
        batch_op.drop_index('ix_checkins_entry_pass_id')
        batch_op.create_index(
            'ix_checkins_entry_pass_id',
            ['entry_pass_id'],
            unique=True,
        )


def downgrade():
    with op.batch_alter_table('checkins', schema=None) as batch_op:
        batch_op.drop_index('ix_checkins_entry_pass_id')
        batch_op.create_index(
            'ix_checkins_entry_pass_id',
            ['entry_pass_id'],
            unique=False,
        )
