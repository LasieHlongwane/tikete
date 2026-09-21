"""add restaurant experience rating

Revision ID: dc1c5e87dd37
Revises: ff2b3fee9b72
Create Date: 2026-09-21 06:50:54.132230

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "dc1c5e87dd37"
down_revision = "ff2b3fee9b72"
branch_labels = None
depends_on = None


def upgrade():

    # ========================================================
    # RESTAURANT EXPERIENCE RATING
    # ========================================================
    #
    # IMPORTANT:
    #
    # Existing restaurant experience posts were created
    # before ratings existed.
    #
    # Therefore rating is intentionally nullable at the
    # database level so that old posts remain valid.
    #
    # New submissions should still require a rating in the
    # Flask route / HTML form.
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "rating",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_restaurant_experience_posts_rating"
            ),
            [
                "rating",
            ],
            unique=False,
        )


    # ========================================================
    # RATING RANGE CONSTRAINT
    # ========================================================
    #
    # Rating may be NULL for old posts.
    #
    # Otherwise it must be between 1 and 5.
    # ========================================================

    op.create_check_constraint(
        "ck_restaurant_experience_posts_rating_range",
        "restaurant_experience_posts",
        (
            "rating IS NULL "
            "OR "
            "(rating >= 1 AND rating <= 5)"
        ),
    )


def downgrade():

    # ========================================================
    # REMOVE RATING RANGE CONSTRAINT
    # ========================================================

    op.drop_constraint(
        "ck_restaurant_experience_posts_rating_range",
        "restaurant_experience_posts",
        type_="check",
    )


    # ========================================================
    # REMOVE RATING
    # ========================================================

    with op.batch_alter_table(
        "restaurant_experience_posts",
        schema=None,
    ) as batch_op:

        batch_op.drop_index(
            batch_op.f(
                "ix_restaurant_experience_posts_rating"
            )
        )

        batch_op.drop_column(
            "rating"
        )