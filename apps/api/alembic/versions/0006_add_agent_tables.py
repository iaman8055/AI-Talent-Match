"""add agent_configs and agent_decisions tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Uuid(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("auto_apply_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("target_roles", sa.JSON(), nullable=False),
        sa.Column("target_skills", sa.JSON(), nullable=False),
        sa.Column("target_locations", sa.JSON(), nullable=False),
        sa.Column("work_modes", sa.JSON(), nullable=False),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("min_match_score", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("daily_apply_cap", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_configs_candidate_id", "agent_configs", ["candidate_id"])

    op.create_table(
        "agent_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "candidate_id",
            sa.Uuid(),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "match_score_id",
            sa.Uuid(),
            sa.ForeignKey("match_scores.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("constraint_results", sa.JSON(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_agent_decisions_candidate_job"),
    )
    op.create_index("ix_agent_decisions_candidate_id", "agent_decisions", ["candidate_id"])
    op.create_index("ix_agent_decisions_job_id", "agent_decisions", ["job_id"])
    op.create_index(
        "ix_agent_decisions_candidate_action", "agent_decisions", ["candidate_id", "action"]
    )


def downgrade() -> None:
    op.drop_table("agent_decisions")
    op.drop_table("agent_configs")
