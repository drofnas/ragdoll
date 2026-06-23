"""phase_13a_self_hosted_policy_cleanup

Revision ID: 202606220003
Revises: 202606220002
Create Date: 2026-06-22 00:03:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606220003"
down_revision = "202606220002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "feature_flag_overrides")
    op.drop_column("users", "plan_tier")


def downgrade() -> None:
    op.add_column("users", sa.Column("plan_tier", sa.String(length=32), nullable=False, server_default="free"))
    op.add_column("users", sa.Column("feature_flag_overrides", sa.JSON(), nullable=True))
