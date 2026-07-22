"""add outreach_drafts table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outreach_drafts",
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
        sa.Column("candidate_summary", sa.String(2000), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.String(4000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("sent_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_outreach_drafts_candidate_job"),
    )
    op.create_index("ix_outreach_drafts_candidate_id", "outreach_drafts", ["candidate_id"])
    op.create_index("ix_outreach_drafts_job_id", "outreach_drafts", ["job_id"])
    op.create_index("ix_outreach_drafts_job_status", "outreach_drafts", ["job_id", "status"])


def downgrade() -> None:
    op.drop_table("outreach_drafts")
